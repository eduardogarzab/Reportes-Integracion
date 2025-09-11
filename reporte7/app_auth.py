import os
import uuid
import logging
import datetime as dt

import MySQLdb
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_mysqldb import MySQL
import jwt  # PyJWT
from werkzeug.security import generate_password_hash, check_password_hash

# =========================
# Configuración de la app
# =========================
app = Flask(__name__)

# JWT: usa variables de entorno en prod
app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'cambia-esto-en-produccion')
app.config['JWT_ALG'] = 'HS256'
app.config['ACCESS_TOKEN_MINUTES'] = int(os.getenv('ACCESS_TOKEN_MINUTES', '15'))
app.config['REFRESH_TOKEN_DAYS'] = int(os.getenv('REFRESH_TOKEN_DAYS', '7'))

# CORS: igual que tu micro de Libros
CORS(
    app,
    resources={
        r"/auth/*": {
            "origins": [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://172.206.106.38:8080"
            ]
        },
        r"/api/*": {
            "origins": [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://172.206.106.38:8080"
            ]
        },
    },
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
    expose_headers=["Content-Type"],
    supports_credentials=False,
    max_age=86400,
)

# =========================
# Conexión a MariaDB (Libros)
# =========================
# Respeta tus credenciales por defecto (como en tu micro base)
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'libros_user')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '666')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'Libros')
app.config['MYSQL_CHARSET'] = 'utf8mb4'

mysql = MySQL(app)

# =========================
# Logging del flujo
# =========================
logger = logging.getLogger('auth_service')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s'))
logger.addHandler(handler)

def _redact(d):
    if not isinstance(d, dict):
        return d
    s = dict(d)
    for k in list(s.keys()):
        if k.lower() in ('password','token','access_token','refresh_token'):
            s[k] = '***REDACTED***'
    return s

@app.before_request
def log_in():
    g.t0 = dt.datetime.utcnow()
    payload = None
    try:
        payload = request.get_json(silent=True)
    except Exception:
        pass
    logger.info({
        "event":"request_in",
        "method": request.method,
        "path": request.path,
        "ip": request.remote_addr,
        "ua": request.user_agent.string,
        "headers": {k: ('Bearer ***REDACTED***' if k.lower()=='authorization' else v) for k,v in request.headers.items()},
        "payload": _redact(payload) if payload else None
    })

@app.after_request
def log_out(resp):
    ms = int((dt.datetime.utcnow() - g.get('t0', dt.datetime.utcnow())).total_seconds()*1000)
    logger.info({"event":"response_out","method":request.method,"path":request.path,"status":resp.status_code,"duration_ms":ms})
    return resp

# =========================
# Utilidades JWT / DB
# =========================
def make_access_token(user_id:int, username:str):
    exp = dt.datetime.utcnow() + dt.timedelta(minutes=app.config['ACCESS_TOKEN_MINUTES'])
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": dt.datetime.utcnow(),
        "exp": exp
    }
    tok = jwt.encode(payload, app.config['JWT_SECRET'], algorithm=app.config['JWT_ALG'])
    return tok, exp

def make_refresh_token(user_id:int):
    exp = dt.datetime.utcnow() + dt.timedelta(days=app.config['REFRESH_TOKEN_DAYS'])
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": dt.datetime.utcnow(),
        "exp": exp
    }
    tok = jwt.encode(payload, app.config['JWT_SECRET'], algorithm=app.config['JWT_ALG'])
    # Persistimos para poder validar/revocar
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO refresh_tokens (user_id, jti, token, expires_at) VALUES (%s,%s,%s,%s)",
        (user_id, jti, tok, exp.strftime("%Y-%m-%d %H:%M:%S"))
    )
    mysql.connection.commit()
    cur.close()
    return tok, jti, exp

def is_refresh_valid(jti:str):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT revoked, expires_at FROM refresh_tokens WHERE jti=%s", (jti,))
    row = cur.fetchone()
    cur.close()
    if not row: return False
    if row['revoked']: return False
    return dt.datetime.utcnow() < row['expires_at']

def token_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization','')
        if not auth.startswith('Bearer '):
            return jsonify({"error":"Missing or invalid Authorization header"}), 401
        token = auth.split(' ',1)[1].strip()
        try:
            payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALG']])
            if payload.get('type')!='access':
                return jsonify({"error":"Invalid token type"}), 401
            g.user_id = int(payload['sub'])
            g.username = payload.get('username')
        except jwt.ExpiredSignatureError:
            return jsonify({"error":"Access token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error":"Invalid token"}), 401
        return fn(*args, **kwargs)
    return wrapper

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

    pwd_hash = generate_password_hash(password)  # PBKDF2-SHA256

    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "INSERT INTO users (email, username, password_hash) VALUES (%s,%s,%s)",
            (email, username, pwd_hash)
        )
        mysql.connection.commit()
        user_id = cur.lastrowid
    except MySQLdb.IntegrityError as e:
        mysql.connection.rollback()
        return jsonify({"error":"email o username ya existen","details":str(e)}), 409
    finally:
        cur.close()

    access, acc_exp = make_access_token(user_id, username)
    refresh, jti, ref_exp = make_refresh_token(user_id)

    return jsonify({
        "message":"Usuario registrado",
        "user":{"id":user_id,"email":email,"username":username},
        "tokens":{
            "access_token": access,
            "access_expires_at_utc": acc_exp.isoformat()+"Z",
            "refresh_token": refresh,
            "refresh_expires_at_utc": ref_exp.isoformat()+"Z"
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
    cur.execute(
        "SELECT id, email, username, password_hash FROM users WHERE email=%s OR username=%s",
        (who, who)
    )
    user = cur.fetchone()
    cur.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"error":"Credenciales inválidas"}), 401

    access, acc_exp = make_access_token(user['id'], user['username'])
    refresh, jti, ref_exp = make_refresh_token(user['id'])

    return jsonify({
        "message":"Login exitoso",
        "user":{"id":user['id'],"email":user['email'],"username":user['username']},
        "tokens":{
            "access_token": access,
            "access_expires_at_utc": acc_exp.isoformat()+"Z",
            "refresh_token": refresh,
            "refresh_expires_at_utc": ref_exp.isoformat()+"Z"
        }
    }), 200

@app.post("/auth/refresh")
def refresh():
    data = request.get_json(force=True)
    rt = (data.get('refresh_token') or '').strip()
    if not rt:
        return jsonify({"error":"refresh_token es requerido"}), 400
    try:
        payload = jwt.decode(rt, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALG']])
        if payload.get('type')!='refresh':
            return jsonify({"error":"Token no es de tipo refresh"}), 401
        jti = payload.get('jti'); sub = int(payload.get('sub'))
        if not jti or not is_refresh_valid(jti):
            return jsonify({"error":"Refresh token inválido o revocado/expirado"}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({"error":"Refresh token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error":"Refresh token inválido"}), 401

    # (Opcional) Rotar refresh: revocar jti y emitir uno nuevo.
    # Aquí solo emitimos nuevo access para simplicidad.
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT username FROM users WHERE id=%s", (sub,))
    row = cur.fetchone()
    cur.close()
    username = row['username'] if row else 'user'

    access, acc_exp = make_access_token(sub, username)
    return jsonify({
        "message":"Nuevo access token emitido",
        "access_token": access,
        "access_expires_at_utc": acc_exp.isoformat()+"Z"
    }), 200

# =========================
# API protegida
# =========================
@app.get("/api/profile")
@token_required
def profile():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, email, username, created_at, updated_at FROM users WHERE id=%s", (g.user_id,))
    user = cur.fetchone()
    cur.close()
    if not user:
        return jsonify({"error":"Usuario no encontrado"}), 404
    return jsonify({"user": user}), 200

@app.route("/api/items", methods=["GET","POST"])
@token_required
def items():
    if request.method == "GET":
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT id, title, notes, created_at FROM items WHERE user_id=%s ORDER BY id DESC", (g.user_id,))
        rows = cur.fetchall()
        cur.close()
        return jsonify({"items": rows}), 200

    data = request.get_json(force=True)
    title = (data.get('title') or '').strip()
    notes = data.get('notes')
    if not title:
        return jsonify({"error":"title es requerido"}), 400
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO items (user_id, title, notes) VALUES (%s,%s,%s)", (g.user_id, title, notes))
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return jsonify({"message":"Item creado","id":new_id}), 201

# =========================
# Healthcheck opcional
# =========================
@app.get("/health")
def health():
    return jsonify({"status":"ok","db":app.config['MYSQL_DB']}), 200

if __name__ == "__main__":
    # Igual que tu micro: accesible en red local
    app.run(host="0.0.0.0", port=5001, debug=True)

