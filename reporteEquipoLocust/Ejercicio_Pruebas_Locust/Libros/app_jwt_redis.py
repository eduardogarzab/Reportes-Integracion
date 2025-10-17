from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from datetime import datetime, timedelta
import redis
import mysql.connector
from mysql.connector import pooling
import bcrypt
import traceback

# --- Configuración Flask ---
app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = "super-secret-key"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

jwt = JWTManager(app)

# --- Conexión a Redis ---
try:
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    r.ping()
    print("✅ (Auth) Redis conectado correctamente")
except redis.ConnectionError:
    print("⚠️ (Auth) Redis no disponible")
    r = None

# --- Configuración de BD ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'libros_user',
    'password': '666',
    'database': 'Libros',
}

# --- Pool de Conexiones para el servicio de Auth ---
try:
    # Creamos un pool con el tamaño máximo permitido y recomendado
    cnxpool_auth = pooling.MySQLConnectionPool(pool_name="auth_pool",
                                               pool_size=10,
                                               pool_reset_session=True,
                                               **DB_CONFIG)
    print("✅ (Auth) Pool de conexiones a la BD (tamaño 32) creado exitosamente.")
except mysql.connector.Error as e:
    print(f"⚠️ (Auth) Error al crear el pool de conexiones: {e}")
    cnxpool_auth = None

# --- Gestión de Conexión usando el Pool ---
@app.before_request
def before_request():
    """Toma una conexión del pool antes de cada petición."""
    if cnxpool_auth:
        try:
            g.db = cnxpool_auth.get_connection()
        except mysql.connector.Error as e:
            print(f"Error al obtener conexión del pool de Auth: {e}")
            g.db = None
    else:
        g.db = None

@app.teardown_request
def teardown_request(exception):
    """Devuelve la conexión al pool después de cada petición."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Manejadores de Errores JWT ---
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "token_expired", "msg": "El token ha expirado."}), 401
@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"error": "invalid_token", "msg": "Token inválido."}), 422
@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({"error": "authorization_required", "msg": "Falta la cabecera de autorización."}), 401
@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "token_revoked", "msg": "Este token ha sido revocado."}), 401

# --- Endpoints Refactorizados para usar el Pool de Conexiones ---

@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok"), 200

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all([username, email, password]):
        return jsonify({"msg": "Se requiere nombre de usuario, email y contraseña"}), 400

    if not hasattr(g, 'db') or g.db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        cur = g.db.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
        if cur.fetchone():
            cur.close()
            return jsonify({"msg": "El usuario o email ya existe"}), 409

        cur.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, hashed))
        g.db.commit()
        cur.close()
        return jsonify({"msg": "Usuario registrado exitosamente"}), 201
    except Exception as e:
        g.db.rollback()
        traceback.print_exc()
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    identifier = data.get("username") or data.get("email")
    password = data.get("password")

    if not identifier or not password:
        return jsonify({"msg": "Se requiere identificador y contraseña"}), 400

    if not hasattr(g, 'db') or g.db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        cur = g.db.cursor(dictionary=True)
        cur.execute("SELECT id, username, password_hash FROM users WHERE username=%s OR email=%s", (identifier, identifier))
        user = cur.fetchone()

        if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            cur.close()
            return jsonify({"msg": "Credenciales inválidas"}), 401

        user_identity = user["username"]
        access_token = create_access_token(identity=user_identity)
        refresh_token = create_refresh_token(identity=user_identity)

        if r:
            from flask_jwt_extended import decode_token
            jti = decode_token(access_token)["jti"]
            r.setex(f"token:{jti}", app.config["JWT_ACCESS_TOKEN_EXPIRES"], "active")

        expires_at = datetime.utcnow() + app.config["JWT_REFRESH_TOKEN_EXPIRES"]
        cur.execute("INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
                    (user['id'], refresh_token, expires_at))
        g.db.commit()
        cur.close()

        return jsonify(access_token=access_token, refresh_token=refresh_token), 200
    except Exception as e:
        g.db.rollback()
        traceback.print_exc()
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    try:
        user_identity = get_jwt_identity()
        new_access_token = create_access_token(identity=user_identity)

        if r:
            from flask_jwt_extended import decode_token
            new_jti = decode_token(new_access_token)["jti"]
            r.setex(f"token:{new_jti}", app.config["JWT_ACCESS_TOKEN_EXPIRES"], "active")

        return jsonify(access_token=new_access_token), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    if not hasattr(g, 'db') or g.db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    jti = get_jwt()["jti"]
    username = get_jwt_identity()

    try:
        cur = g.db.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cur.fetchone()

        if r:
            r.setex(f"token:{jti}", app.config["JWT_ACCESS_TOKEN_EXPIRES"], "revoked")

        if user:
            user_id = user['id']
            cur.execute("DELETE FROM refresh_tokens WHERE user_id=%s", (user_id,))

        g.db.commit()
        cur.close()
        return jsonify(msg="Sesión cerrada exitosamente"), 200
    except Exception as e:
        g.db.rollback()
        traceback.print_exc()
        return jsonify({"error": "Error interno del servidor al cerrar sesión"}), 500

@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    jti = get_jwt().get("jti")
    if r and r.get(f"token:{jti}") != "active":
        return jsonify({"msg": "El token ha sido revocado o ya no es válido"}), 401

    return jsonify(logged_in_as=get_jwt_identity()), 200

@app.route("/token/status", methods=["GET"])
@jwt_required()
def token_status():
    decoded_token = get_jwt()
    jti = decoded_token.get("jti")
    username = get_jwt_identity()

    response_data = {
        "decoded": {
            "exp": decoded_token.get("exp"),
            "iat": decoded_token.get("iat"),
            "jti": jti,
            "sub": decoded_token.get("sub"),
            "type": decoded_token.get("type"),
            "username": username
        },
        "exp_utc": datetime.utcfromtimestamp(decoded_token.get('exp')).isoformat() + 'Z',
        "is_revoked": True,
        "redis_state": "not_found_or_expired",
    }

    if r:
        token_in_redis = r.get(f"token:{jti}")
        if token_in_redis:
            response_data["redis_state"] = token_in_redis
            if token_in_redis == "active":
                response_data["is_revoked"] = False

    return jsonify(response_data), 200


# --- Bloque de Ejecución (SOLO para desarrollo, no para Gunicorn) ---
if __name__ == "__main__":
    if cnxpool_auth:
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        print(">>>>> (Auth) LA APLICACIÓN NO PUEDE INICIAR: NO SE PUDO CREAR EL POOL DE CONEXIONES. <<<<<")
