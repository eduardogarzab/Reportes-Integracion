# Sistema de Autenticación y Protección de Recursos en Microservicios

## 1. Descripción general

Este proyecto implementa un sistema de autenticación y protección de recursos en microservicios utilizando **Flask**, **MariaDB**, **Redis** y **JWT**.

Consta de dos microservicios:

- **microauth** (puerto `5001`): gestiona usuarios, autenticación, generación y revocación de tokens JWT.
- **microbooks** (puerto `5000`): expone endpoints de libros protegidos por autenticación JWT.

Incluye un cliente web (**HTML**, **CSS**, **JS**) que realiza login, guarda tokens, consume los endpoints protegidos y compara el JWT local con el estado real en Redis.

---

## 2. Requisitos previos

- Python `3.10+`
- MariaDB `10.6+`
- Redis Server `6+`
- Navegador moderno con soporte para Fetch API

---

## 3. Instalación y despliegue

### 3.1. Instalar dependencias

```bash
pip install flask flask-cors flask-mysqldb PyJWT mysqlclient redis werkzeug
```

### 3.2. Configurar base de datos

Importa el script SQL:

```sql
mysql -u root -p
CREATE DATABASE Libros CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'libros_user'@'%' IDENTIFIED BY '666';
GRANT ALL PRIVILEGES ON Libros.* TO 'libros_user'@'%';
FLUSH PRIVILEGES;
exit;

mysql -u root -p Libros < libros_dump.sql
```

---

## 4. Variables de entorno

```bash
export JWT_SECRET='dev_jwt_secret_change_me'
export MYSQL_HOST='localhost'
export MYSQL_USER='libros_user'
export MYSQL_PASSWORD='666'
export MYSQL_DB='Libros'
export ACCESS_TOKEN_MINUTES=15
export REFRESH_TOKEN_DAYS=7
export REDIS_URL='redis://127.0.0.1:6379/0'
```

---

## 5. Ejecución de los microservicios

### 5.1. Servicio Auth

```bash
cd Microservicios/microauth
python3 app_auth.py
```
Escucha en: [http://0.0.0.0:5001](http://0.0.0.0:5001)

### 5.2. Servicio Books

```bash
cd Microservicios/microbooks
python3 app_books.py
```
Escucha en: [http://0.0.0.0:5000](http://0.0.0.0:5000)

### 5.3. Cliente Web

```bash
cd cliente_web
python3 -m http.server 8080 --bind 0.0.0.0
```
Accede a [http://<IP_VM>:8080](http://<IP_VM>:8080)

---

## 6. Estructura de archivos

```
├── Microservicios/
│   ├── microauth/
│   │   └── app_auth.py
│   ├── microbooks/
│   │   └── app_books.py
├── cliente_web/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── libros_dump.sql
└── readme.txt
```

---

## 7. Pruebas y evidencias

### 7.1. Pruebas con curl

```bash
AUTH=http://127.0.0.1:5001
BOOKS=http://127.0.0.1:5000

# Registro
curl -s $AUTH/auth/register -H 'Content-Type: application/json' \
    -d '{"email":"admin@demo.com","username":"admin@demo.com","password":"Admin#2025"}' | jq .

# Login
LOGIN=$(curl -s $AUTH/auth/login -H 'Content-Type: application/json' \
    -d '{"email":"admin@demo.com","password":"Admin#2025"}')

ACCESS=$(echo "$LOGIN" | jq -r '.tokens.access_token')
REFRESH=$(echo "$LOGIN" | jq -r '.tokens.refresh_token')

# Listar libros (recurso protegido)
curl -s $BOOKS/api/books -H "Authorization: Bearer $ACCESS"

# Verificar estado del token en Redis
curl -s $AUTH/auth/introspect -H 'Content-Type: application/json' \
    -d "{\"token\":\"$ACCESS\"}" | jq .

# Revocar tokens (logout)
curl -s $AUTH/auth/logout -H "Authorization: Bearer $ACCESS" \
    -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$REFRESH\"}" | jq .
```

### 7.2. Pruebas con cliente web

- Accede a `http://IP:8080`
- Regístrate o inicia sesión.
- Observa en el log:
    - Generación y expiración del JWT.
    - Comparación entre JWT local y estado en Redis.
    - Llama a `/api/books` para listar libros.
    - Prueba revocación → `/auth/logout`.
    - Reintenta `/api/books`: debe devolver `401`.

### 7.3. Logs esperados

**Servidor Auth (ejemplo):**
```
[2025-10-07 23:15:10] INFO {"event":"request_in","m":"POST","p":"/auth/login","auth":"no"}
[2025-10-07 23:15:10] INFO {"event":"response_out","m":"POST","p":"/auth/login","status":200,"ms":23}
```

**Cliente Web (ejemplo):**
```
[2025-10-07T23:16:12.492Z] login ok
{
    "user": {"id":1,"email":"admin@demo.com"},
    "access_exp":"2025-10-07T23:31:12Z"
}
```

---

## 8. Flujo de autenticación JWT + Redis

- **Registro/Login** → `access_token` (15 min) y `refresh_token` (7 días). Ambos se guardan en Redis (`access:session:<jti>` y `refresh:session:<jti>`).
- **Protección de endpoints** → `/api/books/*` valida firma y estado en Redis.
- **Refresh** → genera nuevo access y mantiene refresh vigente.
- **Logout** → mueve JTIs a blacklist (`bl:access:*`, `bl:refresh:*`).
- **Introspect** → compara JWT local con su estado real en Redis.
