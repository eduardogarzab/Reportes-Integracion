import os, uuid, logging, datetime as dt, json
import pymysql
# Use PyMySQL as a drop-in replacement for MySQLdb to avoid system
# dependencies required by mysqlclient when running in lightweight venvs.
pymysql.install_as_MySQLdb()
import MySQLdb, jwt, redis
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from urllib.parse import urlparse
from flasgger import Swagger, swag_from
from dotenv import load_dotenv

# --- Cargar .env ---
load_dotenv()

# =========================
# App & Config
# =========================
app = Flask(__name__)

CORS(app)

@app.before_request
def handle_preflight():
    """Maneja las solicitudes OPTIONS (pre-flight) de CORS."""
    if request.method == "OPTIONS":
        res = make_response()
        res.headers.add("Access-Control-Allow-Origin", "*")
        res.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        res.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        return res, 200

# --- Configuración de Swagger ---
app.config['SWAGGER'] = {
    'title': 'Servicio de Autenticación de Libros',
    'uiversion': 3,
    "specs_route": "/apidocs/",
    'securityDefinitions': {
        'bearerAuth': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': "Introduce el token de acceso con el prefijo 'Bearer ' (ej. 'Bearer eyJhbGci...')"
        }
    },
    'security': [{'bearerAuth': []}]
}
swagger = Swagger(app)
# -----------------------------

app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'cambia-esto-en-produccion')
app.config['JWT_ALG'] = 'HS256'
app.config['ACCESS_TOKEN_MINUTES'] = int(os.getenv('ACCESS_TOKEN_MINUTES', '15'))
app.config['REFRESH_TOKEN_DAYS'] = int(os.getenv('REFRESH_TOKEN_DAYS', '7'))
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'libros_user')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '666')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'Libros')
app.config['MYSQL_CHARSET'] = 'utf8mb4'

# Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
rconf = urlparse(REDIS_URL)
r = redis.Redis(host=rconf.hostname, port=rconf.port or 6379, db=int((rconf.path or '/0')[1:] or 0), password=rconf.password, decode_responses=True)

mysql = MySQL(app)

# =========================
# Logging
# =========================
logger = logging.getLogger('auth_service')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s'))
logger.addHandler(handler)

def _redact(d):
    if not isinstance(d, dict): return d
    s = dict(d)
    for k in list(s.keys()):
        if k.lower() in ('password','token','access_token','refresh_token'):
            s[k] = '***REDACTED***'
    return s

@app.before_request
def _in():
    g.t0 = dt.datetime.utcnow()
    payload = None
    try: payload = request.get_json(silent=True)
    except Exception: pass
    logger.info(json.dumps({
        "event":"request_in","m":request.method,"p":request.path,
        "auth": "yes" if request.headers.get("Authorization") else "no",
        "payload": _redact(payload) if payload else None
    }))

@app.after_request
def _out(resp):
    ms = int((dt.datetime.utcnow() - g.get('t0', dt.datetime.utcnow())).total_seconds()*1000)
    logger.info(json.dumps({"event":"response_out","m":request.method,"p":request.path,"status":resp.status_code,"ms":ms}))
    return resp

# =========================
# JWT helpers + Redis model
# =========================
def _issue_access(user_id:int, username:str):
    jti = str(uuid.uuid4())
    exp = dt.datetime.utcnow() + dt.timedelta(minutes=app.config['ACCESS_TOKEN_MINUTES'])
    payload = {"sub": str(user_id), "username": username, "type":"access", "jti": jti, "iat": dt.datetime.utcnow(), "exp": exp}
    tok = jwt.encode(payload, app.config['JWT_SECRET'], algorithm=app.config['JWT_ALG'])
    ttl = int((exp - dt.datetime.utcnow()).total_seconds())
    r.hset(f"access:session:{jti}", mapping={"user_id":str(user_id), "username":username})
    r.expire(f"access:session:{jti}", ttl)
    return tok, jti, exp

def _issue_refresh(user_id:int):
    jti = str(uuid.uuid4())
    exp = dt.datetime.utcnow() + dt.timedelta(days=app.config['REFRESH_TOKEN_DAYS'])
    payload = {"sub": str(user_id), "type":"refresh", "jti": jti, "iat": dt.datetime.utcnow(), "exp": exp}
    tok = jwt.encode(payload, app.config['JWT_SECRET'], algorithm=app.config['JWT_ALG'])
    ttl = int((exp - dt.datetime.utcnow()).total_seconds())
    r.set(f"refresh:session:{jti}", "1", ex=ttl)
    return tok, jti, exp

def _blacklist_access(jti:str, ttl:int=3600):
    r.set(f"bl:access:{jti}", "1", ex=ttl)

def _blacklist_refresh(jti:str, ttl:int=86400):
    r.set(f"bl:refresh:{jti}", "1", ex=ttl)

def _is_access_valid(jti:str)->bool:
    if r.exists(f"bl:access:{jti}"): return False
    return r.exists(f"access:session:{jti}") == 1

def _is_refresh_valid(jti:str)->bool:
    if r.exists(f"bl:refresh:{jti}"): return False
    return r.exists(f"refresh:session:{jti}") == 1

def jwt_required(fn):
    @wraps(fn)
    def w(*args, **kwargs):
        auth = request.headers.get('Authorization','')
        if not auth.startswith('Bearer '):
            return jsonify({"error":"Missing or invalid Authorization header"}), 401
        token = auth.split(' ',1)[1].strip()
        try:
            payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALG']])
            if payload.get('type')!='access':
                return jsonify({"error":"Invalid token type"}), 401
            jti = payload.get('jti')
            if not jti or not _is_access_valid(jti):
                return jsonify({"error":"Access token revoked/invalid"}), 401
            g.user_id = int(payload['sub'])
            g.username = payload.get('username')
            g.access_jti = jti
        except jwt.ExpiredSignatureError:
            return jsonify({"error":"Access token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error":"Invalid token"}), 401
        return fn(*args, **kwargs)
    return w

# =========================
# AUTH ENDPOINTS
# =========================
@app.post("/auth/register")
@swag_from({
    'tags': ['Auth'],
    'summary': 'Registra un nuevo usuario',
    'parameters': [
        {
            'in': 'body', 'name': 'body', 'required': True,
            'schema': {
                'type': 'object', 'required': ['email', 'username', 'password'],
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'username': {'type': 'string'},
                    'password': {'type': 'string', 'format': 'password'}
                }
            }
        }
    ],
    'responses': {
        201: {'description': 'Usuario registrado'},
        400: {'description': 'Datos faltantes'},
        409: {'description': 'Email o username ya existen'}
    }
})
def register():
    data = request.get_json(force=True)
    email = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not email or not username or not password:
        return jsonify({"error":"email, username y password son requeridos"}), 400
    pwd_hash = generate_password_hash(password)
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO users (email, username, password_hash) VALUES (%s,%s,%s)", (email, username, pwd_hash))
        mysql.connection.commit()
        user_id = cur.lastrowid
    except MySQLdb.IntegrityError as e:
        mysql.connection.rollback()
        return jsonify({"error":"email o username ya existen","details":str(e)}), 409
    finally:
        cur.close()
    access, acc_jti, acc_exp = _issue_access(user_id, username)
    refresh, ref_jti, ref_exp = _issue_refresh(user_id)
    return jsonify({
        "message":"Usuario registrado",
        "user":{"id":user_id,"email":email,"username":username},
        "tokens":{
            "access_token": access, "access_jti": acc_jti, "access_expires_at_utc": acc_exp.isoformat()+"Z",
            "refresh_token": refresh, "refresh_jti": ref_jti, "refresh_expires_at_utc": ref_exp.isoformat()+"Z"
        }
    }), 201

@app.post("/auth/login")
@swag_from({
    'tags': ['Auth'],
    'summary': 'Inicia sesión de un usuario',
     'parameters': [
        {
            'in': 'body', 'name': 'body', 'required': True,
            'schema': {
                'type': 'object', 'required': ['who', 'password'],
                'properties': {
                    'who': {'type': 'string', 'description': 'Email o username'},
                    'password': {'type': 'string', 'format': 'password'}
                }
            }
        }
    ],
    'responses': {
        200: {'description': 'Login exitoso'},
        401: {'description': 'Credenciales inválidas'}
    }
})
def login():
    data = request.get_json(force=True)
    who = (data.get('who') or '').strip().lower()
    password = data.get('password') or ''
    if not who or not password:
        return jsonify({"error":"email/username y password son requeridos"}), 400
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, email, username, password_hash FROM users WHERE email=%s OR username=%s", (who, who))
    user = cur.fetchone(); cur.close()
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"error":"Credenciales inválidas"}), 401
    access, acc_jti, acc_exp = _issue_access(user['id'], user['username'])
    refresh, ref_jti, ref_exp = _issue_refresh(user['id'])
    return jsonify({
        "message":"Login exitoso",
        "user":{"id":user['id'],"email":user['email'],"username":user['username']},
        "tokens":{
            "access_token": access, "access_jti": acc_jti, "access_expires_at_utc": acc_exp.isoformat()+"Z",
            "refresh_token": refresh, "refresh_jti": ref_jti, "refresh_expires_at_utc": ref_exp.isoformat()+"Z"
        }
    }), 200

# ... (El resto de los endpoints de app2.py: refresh, logout, introspect, profile, health)
# ... (Por brevedad, no los pego todos, pero estaban en el archivo original que te di)

# Endpoint de health check
@app.get("/health")
def health():
    return jsonify({"status":"ok","db":app.config['MYSQL_DB']}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)