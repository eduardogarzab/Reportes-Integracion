import os
import time
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from flasgger import Swagger
from datetime import timedelta

# ==============================================
# CONFIGURACIÓN INICIAL
# ==============================================
app = Flask(__name__)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:mendoza2004@localhost:3306/Libros'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de JWT
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'clave_super_secreta')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)

# Inicializar extensiones
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# ==============================================
# SWAGGER CONFIG
# ==============================================
swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Auth Service API",
        "description": "API de autenticación (register, login, refresh, profile) para el microservicio 'auth'.",
        "version": "1.0.0"
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
        }
    },
    "schemes": ["http"]
}
swagger = Swagger(app, template=swagger_template)

# ==============================================
# MODELOS
# ==============================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# ==============================================
# RUTAS
# ==============================================

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check
    ---
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            status:
              type: string
            service:
              type: string
            timestamp:
              type: number
    """
    return jsonify({"status": "healthy", "service": "auth", "timestamp": time.time()}), 200


@app.route('/auth/test-db', methods=['GET'])
def test_db():
    """
    Test database connection
    ---
    responses:
      200:
        description: Database connection successful
      500:
        description: Database connection failed
    """
    try:
        db.session.execute('SELECT 1')
        return jsonify({"status": "ok", "message": "Database connection successful"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/auth/register', methods=['POST'])
def register():
    """
    Register a new user
    ---
    tags:
      - auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
            email:
              type: string
            password:
              type: string
          required:
            - username
            - email
            - password
    responses:
      201:
        description: User registered successfully (returns tokens)
      400:
        description: Missing data
      409:
        description: User already exists
    """
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"message": "Missing data"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"message": "User already exists"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, email=email, password=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    access_token = create_access_token(identity=new_user.id)
    refresh_token = create_refresh_token(identity=new_user.id)

    return jsonify({
        "message": "User registered successfully",
        "tokens": {
            "access": access_token,
            "refresh": refresh_token
        }
    }), 201


@app.route('/auth/login', methods=['POST'])
def login():
    """
    Login an existing user
    ---
    tags:
      - auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: credentials
        required: true
        schema:
          type: object
          properties:
            identifier:
              type: string
              description: "username or email"
            password:
              type: string
          required:
            - identifier
            - password
    responses:
      200:
        description: Login successful (returns tokens)
      400:
        description: Missing data
      401:
        description: Invalid credentials
    """
    data = request.get_json()
    identifier = data.get('identifier')
    password = data.get('password')

    if not identifier or not password:
        return jsonify({"message": "Missing data"}), 400

    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()

    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        "message": "Login successful",
        "tokens": {
            "access": access_token,
            "refresh": refresh_token
        }
    }), 200


@app.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token
    ---
    tags:
      - auth
    security:
      - Bearer: []
    responses:
      200:
        description: New access token
      401:
        description: Unauthorized (invalid refresh token)
    """
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify({"access": new_access_token}), 200


@app.route('/api/user-profile', methods=['GET'])
@jwt_required()
def user_profile():
    """
    Get current user profile
    ---
    tags:
      - users
    security:
      - Bearer: []
    responses:
      200:
        description: User profile
        schema:
          type: object
          properties:
            id: { type: integer }
            username: { type: string }
            email: { type: string }
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email
    }), 200


# ==============================================
# INICIALIZAR BASE DE DATOS
# ==============================================
@app.before_first_request
def create_tables():
    db.create_all()

# ==============================================
# EJECUTAR SERVICIO
# ==============================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
