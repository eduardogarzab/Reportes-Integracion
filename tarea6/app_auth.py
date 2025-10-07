import os, uuid, logging, datetime as dt, json
import MySQLdb, jwt, redis
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from urllib.parse import urlparse

# =========================
# App & Config
# =========================
app = Flask(__name__)
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

CORS(
    app,
    resources={r"/auth/*": {"origins": ["*"]},
               r"/api/*": {"origins": ["*"]}},
    methods=["GET","POST","PUT","DELETE","OPTIONS"],
    allow_headers=["Content-Type","Accept","Authorization"],
    expose_headers=["Content-Type"],
    supports_credentials=False,
    max_age=86400,
)

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
    # allowlist en Redis (TTL hasta exp)
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
    # allowlist refresh
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
# AUTH
# =========================
@app.post("/auth/register")
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
def login():
    data = request.get_json(force=True)
    who = (data.get('email') or data.get('username') or '').strip().lower()
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

@app.post("/auth/refresh")
def refresh():
    data = request.get_json(force=True)
    rt = (data.get('refresh_token') or '').strip()
    if not rt: return jsonify({"error":"refresh_token es requerido"}), 400
    try:
        payload = jwt.decode(rt, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALG']])
        if payload.get('type')!='refresh': return jsonify({"error":"Token no es de tipo refresh"}), 401
        jti = payload.get('jti'); sub = int(payload.get('sub'))
        if not jti or not _is_refresh_valid(jti):
            return jsonify({"error":"Refresh token inválido o revocado/expirado"}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({"error":"Refresh token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error":"Refresh token inválido"}), 401

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT username FROM users WHERE id=%s", (sub,))
    row = cur.fetchone(); cur.close()
    username = row['username'] if row else 'user'
    access, acc_jti, acc_exp = _issue_access(sub, username)
    return jsonify({"message":"Nuevo access token emitido",
                    "access_token": access, "access_jti": acc_jti,
                    "access_expires_at_utc": acc_exp.isoformat()+"Z"}), 200

@app.post("/auth/logout")
@jwt_required
def logout():
    data = request.get_json(silent=True) or {}
    refresh_token = (data.get('refresh_token') or '').strip()
    # Revoca access actual
    acc_ttl = r.ttl(f"access:session:{g.access_jti}")
    _blacklist_access(g.access_jti, ttl=max(acc_ttl, 60))
    r.delete(f"access:session:{g.access_jti}")
    # Revoca refresh si viene
    if refresh_token:
        try:
            p = jwt.decode(refresh_token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALG']])
            if p.get('type') == 'refresh' and p.get('jti'):
                ref_jti = p['jti']
                ref_ttl = r.ttl(f"refresh:session:{ref_jti}")
                _blacklist_refresh(ref_jti, ttl=max(ref_ttl, 300))
                r.delete(f"refresh:session:{ref_jti}")
        except Exception:
            pass
    return jsonify({"message":"Sesión cerrada y tokens revocados"}), 200

@app.post("/auth/introspect")
def introspect():
    """
    Devuelve comparación útil para el cliente:
    - payload decodificado (header/payload)
    - estado en Redis (allowlist/blacklist)
    """
    data = request.get_json(force=True)
    tok = (data.get('token') or '').strip()
    if not tok: return jsonify({"error":"token requerido"}), 400
    try:
        p = jwt.decode(tok, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALG']], options={"verify_exp": False})
        jti = p.get('jti'); t = p.get('type')
        exp = p.get('exp'); now = int(dt.datetime.utcnow().timestamp())
        on_allow = on_bl = None
        if t == 'access':
            on_allow = r.exists(f"access:session:{jti}") == 1
            on_bl    = r.exists(f"bl:access:{jti}") == 1
        elif t == 'refresh':
            on_allow = r.exists(f"refresh:session:{jti}") == 1
            on_bl    = r.exists(f"bl:refresh:{jti}") == 1
        return jsonify({
            "decoded": p,
            "exp_utc": dt.datetime.utcfromtimestamp(exp).isoformat()+"Z" if exp else None,
            "is_expired": (exp is not None and now >= int(exp)),
            "redis_state": {"allowlist": bool(on_allow), "blacklist": bool(on_bl)}
        }), 200
    except jwt.InvalidTokenError:
        return jsonify({"error":"Token inválido"}), 400

# API de prueba protegida (no libros; libros vive en micro1)
@app.get("/api/profile")
@jwt_required
def profile():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, email, username, created_at, updated_at FROM users WHERE id=%s", (g.user_id,))
    user = cur.fetchone(); cur.close()
    if not user: return jsonify({"error":"Usuario no encontrado"}), 404
    return jsonify({"user": user}), 200

@app.get("/health")
def health():
    ok = r.ping()
    return jsonify({"status":"ok","db":app.config['MYSQL_DB'],"redis": ok}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
