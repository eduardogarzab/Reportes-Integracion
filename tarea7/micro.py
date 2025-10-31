import os, uuid, io
from flask import Flask, request, Response, g, jsonify, make_response
import MySQLdb, jwt, redis
from flask_cors import CORS
from functools import wraps
from urllib.parse import urlparse
from flasgger import Swagger, swag_from
from werkzeug.utils import secure_filename

# --- Carga de variables de entorno (.env) ---
from dotenv import load_dotenv
load_dotenv() 

# =========================
# App & Config
# =========================
app = Flask(__name__)

# --- INICIO DE LA CORRECCIÓN DE SWAGGER ---

# 1. Elimina el bloque app.config['SWAGGER'] que tenías aquí.

# 2. Define UN ÚNICO TEMPLATE que tiene TODO: info, definiciones Y seguridad.
SWAGGER_TEMPLATE = {
    'swagger': '2.0',
    'info': {
        'title': 'Servicio de Libros',
        'version': '1.0'
    },
    'securityDefinitions': {
        'bearerAuth': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': "Introduce el token de acceso (sin 'Bearer '). P.ej: eyJhbGci..."
        }
    },
    'security': [{'bearerAuth': []}], # Aplica seguridad global
    'definitions': {
        'BookWithImages': {
            'type': 'object',
            'properties': {
                'id_libro': {'type': 'integer'},
                'isbn': {'type': 'string'},
                'titulo': {'type': 'string'},
                'anio_publicacion': {'type': 'integer'},
                'precio': {'type': 'number', 'format': 'float'},
                'stock': {'type': 'integer'},
                'genero': {'type': 'string'},
                'formato': {'type': 'string'},
                'autor': {'type': 'string', 'description': 'Nombres de autores separados por coma'},
                'imagenes': {
                    'type': 'array',
                    'items': {'type': 'string', 'format': 'uri'},
                    'description': 'URLs de las imágenes del libro'
                }
            }
        },
        'BookList': {
            'type': 'array',
            'items': {'$ref': '#/definitions/BookWithImages'}
        }
    }
}
# 3. Inicia Swagger con el template corregido
swagger = Swagger(app, template=SWAGGER_TEMPLATE)

# 4. Elimina la función 'swagger_definitions()' duplicada. Ya no es necesaria.

# --- FIN DE LA CORRECCIÓN DE SWAGGER ---


# --- CORS y Manejador de Pre-flight (OPTIONS) ---
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

# --- DB Config ---
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST','localhost'),
    'user': os.getenv('MYSQL_USER','libros_user'),
    'passwd': os.getenv('MYSQL_PASSWORD','666'),
    'db': os.getenv('MYSQL_DB','Libros'),
    'charset': 'utf8mb4',
    'autocommit': False # IMPORTANTE para transacciones
}

# --- JWT + Redis Config ---
JWT_SECRET = os.getenv('JWT_SECRET','cambia-esto-en-produccion')
JWT_ALG = 'HS256'
REDIS_URL = os.getenv('REDIS_URL','redis://127.0.0.1:6379/0')
rconf = urlparse(REDIS_URL)
r = redis.Redis(host=rconf.hostname, port=rconf.port or 6379, db=int((rconf.path or '/0')[1:] or 0), password=rconf.password, decode_responses=True)

# --- Azure Blob Storage Config ---
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

ACCOUNT_URL = os.getenv("AZURE_STORAGE_ACCOUNT_URL", "https://imagenesintegracion.blob.core.windows.net")
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "microservicio-libros")

try:
    credential = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(account_url=ACCOUNT_URL, credential=credential)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
    print("Azure Blob Storage conectado exitosamente.")
except Exception as e:
    print(f"Error al conectar con Azure Blob Storage: {e}")
    blob_service_client = None

# --- Validación de Archivos ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024 # 5 MB
MAX_IMAGE_COUNT = 5

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def json_error(message, status_code):
    """Helper para devolver errores en JSON."""
    return make_response(jsonify({"error": message, "status": status_code}), status_code)

# =========================
# DB & Auth
# =========================
def get_db_connection():
    """Obtiene una conexión de BD por petición."""
    if 'db' not in g:
        try:
            g.db = MySQLdb.connect(**DB_CONFIG)
        except MySQLdb.Error as e:
            print(f"Error DB: {e}")
            g.db = None
    return g.db

@app.teardown_appcontext
def teardown_db(exception):
    """Cierra la conexión de BD al final de la petición."""
    db = g.pop('db', None)
    if db is not None:
        if exception:
            db.rollback() 
        else:
            db.commit() 
        db.close()

def jwt_required(fn):
    """Decorador JWT modificado para devolver JSON."""
    @wraps(fn)
    def w(*args, **kwargs):
        auth = request.headers.get('Authorization','')
        if not auth.startswith('Bearer '):
            return json_error("Missing Authorization", 401)
        token = auth.split(' ',1)[1].strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            if payload.get('type')!='access':
                return json_error("Invalid token type", 401)
            jti = payload.get('jti')
            if not jti or not r.exists(f"access:session:{jti}"): 
                return json_error("Access token revoked/invalid", 401)
            g.user_id = int(payload['sub'])
            g.username = payload.get('username')
        except jwt.ExpiredSignatureError:
            return json_error("Access token expired", 401)
        except jwt.InvalidTokenError:
            return json_error("Invalid token", 401)
        return fn(*args, **kwargs)
    return w

# =========================
# Azure Blob Helpers
# =========================
def upload_image_to_azure(file_storage):
    """Sube un FileStorage de Flask a Azure y devuelve URL pública y blob_name."""
    if not blob_service_client:
        raise Exception("Azure Blob Service Client no está inicializado.")
        
    filename = secure_filename(file_storage.filename)
    extension = filename.rsplit('.', 1)[1].lower()
    unique_blob_name = f"libros/{uuid.uuid4()}.{extension}"
    
    try:
        blob_client = container_client.get_blob_client(unique_blob_name)
        blob_client.upload_blob(file_storage.stream, overwrite=True)
        public_url = f"{ACCOUNT_URL}/{CONTAINER_NAME}/{unique_blob_name}"
        return public_url, unique_blob_name
        
    except Exception as e:
        print(f"Error al subir a Azure: {e}")
        raise

def delete_blob_from_azure(blob_name):
    """Elimina un blob de Azure por su nombre."""
    if not blob_service_client or not blob_name:
        return
    try:
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob(delete_snapshots="include")
        print(f"Blob {blob_name} eliminado de Azure.")
    except Exception as e:
        print(f"Error al eliminar blob {blob_name} de Azure: {e}")

# =========================
# Endpoints de Libros
# =========================

@app.get('/api/books')
@jwt_required
@swag_from({
    'tags': ['Books'],
    'summary': 'Obtiene todos los libros (con filtros y búsqueda)',
    'description': 'Devuelve una lista de libros. Acepta parámetros de consulta para búsqueda y filtrado.',
    
    'security': [{'bearerAuth': []}], # <--- Esto es explícito y bueno

    'parameters': [
        {'in': 'query', 'name': 'q', 'type': 'string', 'description': 'Término de búsqueda (título o ISBN)'},
        {'in': 'query', 'name': 'genero', 'type': 'string', 'description': 'Filtrar por nombre de género'},
        {'in': 'query', 'name': 'formato', 'type': 'string', 'description': 'Filtrar por nombre de formato'},
        {'in': 'query', 'name': 'autor', 'type': 'string', 'description': 'Filtrar por nombre de autor'}
    ],
    'responses': { 200: {'$ref': '#/definitions/BookList'} }
})
def get_all_books():
    conn = get_db_connection()
    if not conn: return json_error("Error de conexión con la base de datos", 500)
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    
    query = """
    SELECT 
        l.id_libro, l.isbn, l.titulo, l.anio_publicacion, l.precio, l.stock,
        g.nombre AS genero, f.nombre AS formato,
        (SELECT GROUP_CONCAT(a.nombre SEPARATOR ', ')
         FROM autores a JOIN libro_autor la ON a.id_autor = la.id_autor
         WHERE la.id_libro = l.id_libro) AS autor,
        (SELECT GROUP_CONCAT(li.url SEPARATOR '||')
         FROM libro_imagenes li
         WHERE li.id_libro = l.id_libro ORDER BY li.orden) AS imagenes
    FROM libros l
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    LEFT JOIN formato f ON l.id_formato = f.id_formato
    """
    
    where_clauses = []
    params = []
    
    q = request.args.get('q')
    if q:
        where_clauses.append("(l.titulo LIKE %s OR l.isbn LIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])
        
    genero = request.args.get('genero')
    if genero:
        where_clauses.append("g.nombre = %s")
        params.append(genero)
        
    formato = request.args.get('formato')
    if formato:
        where_clauses.append("f.nombre = %s")
        params.append(formato)
        
    autor = request.args.get('autor')
    if autor:
        query += """
        JOIN libro_autor la_filt ON l.id_libro = la_filt.id_libro
        JOIN autores a_filt ON la_filt.id_autor = a_filt.id_autor
        """
        where_clauses.append("a_filt.nombre = %s")
        params.append(autor)

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " GROUP BY l.id_libro ORDER BY l.titulo"
    
    cur.execute(query, tuple(params))
    books = cur.fetchall()
    cur.close()
    
    for book in books:
        if book.get('imagenes'):
            book['imagenes'] = book['imagenes'].split('||')
        else:
            book['imagenes'] = []
            
    return jsonify(books)

# --- Endpoint para obtener un solo libro ---
@app.get('/api/books/<int:id_libro>')
@jwt_required
@swag_from({
    'tags': ['Books'],
    'summary': 'Obtiene un solo libro por ID',
    
    'security': [{'bearerAuth': []}], # <--- Esto es explícito y bueno

    'parameters': [
        {'in': 'path', 'name': 'id_libro', 'type': 'integer', 'required': True}
    ],
    'responses': { 200: {'$ref': '#/definitions/BookWithImages'} }
})
def get_book_by_id(id_libro):
    conn = get_db_connection()
    if not conn: return json_error("Error de conexión con la base de datos", 500)
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    
    query = """
    SELECT 
        l.id_libro, l.isbn, l.titulo, l.anio_publicacion, l.precio, l.stock,
        g.nombre AS genero, f.nombre AS formato,
        (SELECT GROUP_CONCAT(a.nombre SEPARATOR ', ')
         FROM autores a JOIN libro_autor la ON a.id_autor = la.id_autor
         WHERE la.id_libro = l.id_libro) AS autor,
        (SELECT GROUP_CONCAT(li.url SEPARATOR '||')
         FROM libro_imagenes li
         WHERE li.id_libro = l.id_libro ORDER BY li.orden) AS imagenes
    FROM libros l
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    LEFT JOIN formato f ON l.id_formato = f.id_formato
    WHERE l.id_libro = %s
    GROUP BY l.id_libro
    """
    cur.execute(query, (id_libro,))
    book = cur.fetchone()
    cur.close()
    
    if not book:
        return json_error("Libro no encontrado", 404)
        
    if book.get('imagenes'):
        book['imagenes'] = book['imagenes'].split('||')
    else:
        book['imagenes'] = []
            
    return jsonify(book)


@app.post('/api/books')
@jwt_required
@swag_from({
    'tags': ['Books'],
    'summary': 'Crea un nuevo libro con imágenes',
    'description': 'Crea un libro. Acepta multipart/form-data. Los datos del libro van en campos de formulario y las imágenes en el campo "images".',
    'consumes': ['multipart/form-data'],
    
    'security': [{'bearerAuth': []}], # <--- Esto es explícito y bueno
    
    'parameters': [
        {'in': 'formData', 'name': 'isbn', 'type': 'string', 'required': True},
        {'in': 'formData', 'name': 'titulo', 'type': 'string', 'required': True},
        {'in': 'formData', 'name': 'anio_publicacion', 'type': 'integer', 'required': True},
        {'in': 'formData', 'name': 'precio', 'type': 'number', 'required': True},
        {'in': 'formData', 'name': 'stock', 'type': 'integer', 'required': True},
        {'in': 'formData', 'name': 'autor', 'type': 'string', 'description': 'Nombre del autor (solo el primero se guardará)', 'required': True},
        {'in': 'formData', 'name': 'genero', 'type': 'string', 'required': True},
        {'in': 'formData', 'name': 'formato', 'type': 'string', 'required': True},
        {
            'in': 'formData',
            'name': 'images',
            'type': 'file',
            'description': f'Imágenes (Max {MAX_IMAGE_COUNT}, {MAX_FILE_SIZE//1024//1024}MB, {ALLOWED_EXTENSIONS})'
        }
    ],
    'responses': { 201: {'description': 'Libro creado'}, 400: {'description': 'Error de validación'} }
})
def insert_book():
    conn = get_db_connection()
    if not conn: return json_error("Error de conexión con la base de datos", 500)
    
    try:
        data = request.form
        images = request.files.getlist('images')

        if len(images) > MAX_IMAGE_COUNT:
            return json_error(f"No se pueden subir más de {MAX_IMAGE_COUNT} imágenes", 400)
        
        valid_images = []
        for file in images:
            if file and allowed_file(file.filename):
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0) 
                if file_size > MAX_FILE_SIZE:
                    return json_error(f"El archivo {file.filename} excede los {MAX_FILE_SIZE//1024//1024}MB", 400)
                valid_images.append(file)
            elif file.filename != '':
                return json_error(f"Formato de archivo no permitido: {file.filename}", 400)

        cur = conn.cursor()
        cur.execute("SELECT id_genero FROM genero WHERE nombre=%s", (data.get('genero'),))
        row = cur.fetchone()
        id_genero = row['id_genero'] if row else 1

        cur.execute("SELECT id_formato FROM formato WHERE nombre=%s", (data.get('formato'),))
        row = cur.fetchone()
        id_formato = row['id_formato'] if row else 1
        
        autor_nombre = data.get('autor', '').split(',')[0].strip()
        cur.execute("SELECT id_autor FROM autores WHERE nombre=%s", (autor_nombre,))
        row = cur.fetchone()
        id_autor = row['id_autor'] if row else 1
        
        sql_libro = """
        INSERT INTO libros (isbn, titulo, anio_publicacion, precio, stock, id_genero, id_formato)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(sql_libro, (
            data.get('isbn'), data.get('titulo'), data.get('anio_publicacion'),
            data.get('precio'), data.get('stock'), id_genero, id_formato
        ))
        id_libro = cur.lastrowid
        
        cur.execute("INSERT INTO libro_autor (id_libro, id_autor) VALUES (%s, %s)", (id_libro, id_autor))

        uploaded_urls = []
        for i, file in enumerate(valid_images):
            try:
                public_url, blob_name = upload_image_to_azure(file)
                sql_img = "INSERT INTO libro_imagenes (id_libro, url, blob_name, orden) VALUES (%s, %s, %s, %s)"
                cur.execute(sql_img, (id_libro, public_url, blob_name, i))
                uploaded_urls.append(public_url)
            except Exception as e:
                conn.rollback()
                return json_error(f"Error al subir imagen: {e}", 500)

        cur.close()
        
        return jsonify({
            "message": "Libro creado exitosamente",
            "id_libro": id_libro,
            "image_urls": uploaded_urls
        }), 201

    except MySQLdb.Error as e:
        conn.rollback() 
        return json_error(f"Error de base de datos: {e}", 500)
    except Exception as e:
        conn.rollback()
        return json_error(f"Error inesperado: {e}", 500)

# --- Endpoint para actualizar un libro ---
@app.put('/api/books/<int:id_libro>')
@jwt_required
@swag_from({
    'tags': ['Books'],
    'summary': 'Actualiza un libro existente',
    'description': 'Actualiza datos. Si se envían imágenes, REEMPLAZA las antiguas.',
    'consumes': ['multipart/form-data'],
    
    'security': [{'bearerAuth': []}], # <--- Esto es explícito y bueno
    
    'parameters': [
        {'in': 'path', 'name': 'id_libro', 'type': 'integer', 'required': True},
        {'in': 'formData', 'name': 'isbn', 'type': 'string', 'required': True},
        {'in': 'formData', 'name': 'titulo', 'type': 'string', 'required': True},
        {'in': 'formData', 'name': 'anio_publicacion', 'type': 'integer', 'required': True},
        {'in': 'formData', 'name': 'precio', 'type': 'number', 'required': True},
        {'in': 'formData', 'name': 'stock', 'type': 'integer', 'required': True},
        {'in': 'formData', 'name': 'autor', 'type': 'string', 'description': 'Nombre del autor (solo el primero se guardará)', 'required': True},
        {'in': 'formData', 'name': 'genero', 'type': 'string', 'required': True},
        {'in': 'formData', 'name': 'formato', 'type': 'string', 'required': True},
        {
            'in': 'formData',
            'name': 'images',
            'type': 'file',
            'description': 'Nuevas imágenes (reemplazarán las existentes)'
        }
    ],
    'responses': { 200: {'description': 'Libro actualizado'}, 404: {'description': 'Libro no encontrado'} }
})
def update_book(id_libro):
    conn = get_db_connection()
    if not conn: return json_error("Error de conexión con la base de datos", 500)
    
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    
    cur.execute("SELECT id_libro FROM libros WHERE id_libro = %s", (id_libro,))
    if not cur.fetchone():
        cur.close()
        return json_error("Libro no encontrado", 404)

    try:
        data = request.form
        images = request.files.getlist('images')
        
        blobs_to_delete = []
        
        if images and images[0].filename != '':
            if len(images) > MAX_IMAGE_COUNT:
                return json_error(f"No se pueden subir más de {MAX_IMAGE_COUNT} imágenes", 400)
            
            valid_images = []
            for file in images:
                if file and allowed_file(file.filename):
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    if file_size > MAX_FILE_SIZE:
                        return json_error(f"Archivo {file.filename} excede {MAX_FILE_SIZE//1024//1024}MB", 400)
                    valid_images.append(file)
                elif file.filename != '':
                    return json_error(f"Formato de archivo no permitido: {file.filename}", 400)

            cur.execute("SELECT blob_name FROM libro_imagenes WHERE id_libro = %s", (id_libro,))
            blobs_to_delete = [row['blob_name'] for row in cur.fetchall()]
            
            cur.execute("DELETE FROM libro_imagenes WHERE id_libro = %s", (id_libro,))
            
            for i, file in enumerate(valid_images):
                public_url, blob_name = upload_image_to_azure(file)
                sql_img = "INSERT INTO libro_imagenes (id_libro, url, blob_name, orden) VALUES (%s, %s, %s, %s)"
                cur.execute(sql_img, (id_libro, public_url, blob_name, i))

        cur.execute("SELECT id_genero FROM genero WHERE nombre=%s", (data.get('genero'),))
        row = cur.fetchone()
        id_genero = row['id_genero'] if row else 1

        cur.execute("SELECT id_formato FROM formato WHERE nombre=%s", (data.get('formato'),))
        row = cur.fetchone()
        id_formato = row['id_formato'] if row else 1
        
        autor_nombre = data.get('autor', '').split(',')[0].strip()
        cur.execute("SELECT id_autor FROM autores WHERE nombre=%s", (autor_nombre,))
        row = cur.fetchone()
        id_autor = row['id_autor'] if row else 1
        
        sql_update_libro = """
        UPDATE libros SET 
            isbn = %s, titulo = %s, anio_publicacion = %s, precio = %s, 
            stock = %s, id_genero = %s, id_formato = %s
        WHERE id_libro = %s
        """
        cur.execute(sql_update_libro, (
            data.get('isbn'), data.get('titulo'), data.get('anio_publicacion'),
            data.get('precio'), data.get('stock'), id_genero, id_formato, id_libro
        ))
        
        cur.execute("DELETE FROM libro_autor WHERE id_libro = %s", (id_libro,))
        cur.execute("INSERT INTO libro_autor (id_libro, id_autor) VALUES (%s, %s)", (id_libro, id_autor))
        
        cur.close()

        for blob_name in blobs_to_delete:
            delete_blob_from_azure(blob_name)
            
        return jsonify({"message": f"Libro {id_libro} actualizado exitosamente"}), 200

    except Exception as e:
        conn.rollback()
        print(f"Error en update_book: {e}") 
        return json_error(f"Error al actualizar: {e}", 500)

# --- Endpoint para eliminar un libro ---
@app.delete('/api/books/<int:id_libro>')
@jwt_required
@swag_from({
    'tags': ['Books'],
    'summary': 'Elimina un libro y sus imágenes',
    
    'security': [{'bearerAuth': []}], # <--- Esto es explícito y bueno
    
    'parameters': [
        {'in': 'path', 'name': 'id_libro', 'type': 'integer', 'required': True}
    ],
    'responses': { 200: {'description': 'Libro eliminado'}, 404: {'description': 'Libro no encontrado'} }
})
def delete_book(id_libro):
    conn = get_db_connection()
    if not conn: return json_error("Error de conexión con la base de datos", 500)
    
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cur.execute("SELECT blob_name FROM libro_imagenes WHERE id_libro = %s", (id_libro,))
        blobs_to_delete = [row['blob_name'] for row in cur.fetchall()]
        
        cur.execute("SELECT id_libro FROM libros WHERE id_libro = %s", (id_libro,))
        if not cur.fetchone():
            cur.close()
            return json_error("Libro no encontrado", 404)
        
        cur.execute("DELETE FROM libros WHERE id_libro = %s", (id_libro,))
        
        cur.close()

        for blob_name in blobs_to_delete:
            delete_blob_from_azure(blob_name)
            
        return jsonify({"message": f"Libro {id_libro} eliminado exitosamente"}), 200

    except Exception as e:
        conn.rollback()
        return json_error(f"Error al eliminar: {e}", 500)


if __name__ == '__main__':
    if not blob_service_client:
        print("\n!!! ADVERTENCIA: No se pudo conectar a Azure. La subida de archivos fallará. !!!")
        print("Asegúrate de tener las variables de entorno AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET y AZURE_STORAGE_ACCOUNT_URL configuradas.\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)