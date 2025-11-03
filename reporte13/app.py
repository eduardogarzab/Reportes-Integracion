import os
import io
import pymysql
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, Response
from azure.storage.blob import (
    BlobServiceClient,
    ContainerClient,
    generate_blob_sas,
    BlobSasPermissions
)
from azure.identity import DefaultAzureCredential
from werkzeug.utils import secure_filename
from dicttoxml import dicttoxml
from flasgger import Swagger, swag_from

# --- Configuración Inicial ---

app = Flask(__name__)
swagger = Swagger(app)

from dotenv import load_dotenv
load_dotenv()

ACCOUNT_URL = os.environ.get("AZURE_STORAGE_ACCOUNT_URL", "https://imagenesintegracion.blob.core.windows.net")
CONTAINER_NAME = os.environ.get("CONTAINER_NAME", "microservicio-libros")

# Autenticación segura con Service Principal (lee variables de entorno)
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(account_url=ACCOUNT_URL, credential=credential)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# Configuración de MariaDB (leída desde variables de entorno)
# DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'cursorclass': pymysql.cursors.DictCursor
}

# Configuración de la App
API_TOKEN = os.environ.get("API_TOKEN") # Token de API para autenticación
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# --- Helpers y Decoradores ---

def get_db_connection():
    """Conecta a la base de datos MariaDB."""
    try:
        conn = pymysql.connect(**db_config)
        return conn
    except pymysql.MySQLError as e:
        app.logger.error(f"Error al conectar a MariaDB: {e}")
        return None

def allowed_file(filename):
    """Verifica si la extensión del archivo es válida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_sas_url(blob_name):
    """Genera una URL SAS válida por 1 hora."""
    # Nota: DefaultAzureCredential no puede generar SAS de *usuario*.
    # Pero el Service Principal (si tiene el rol correcto) puede generar SAS de *servicio*.
    # Necesitamos obtener la clave de delegación de usuario primero.
    
    try:
        # 1. Obtener clave de delegación de usuario (válida por 1 hora)
        user_delegation_key = blob_service_client.get_user_delegation_key(
            key_start_time=datetime.utcnow() - timedelta(minutes=5),
            key_expiry_time=datetime.utcnow() + timedelta(hours=1)
        )

        # 2. Generar el SAS token para el blob específico
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=CONTAINER_NAME,
            blob_name=blob_name,
            user_delegation_key=user_delegation_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )

        # 3. Construir la URL completa
        sas_url = f"{ACCOUNT_URL}/{CONTAINER_NAME}/{blob_name}?{sas_token}"
        return sas_url

    except Exception as e:
        app.logger.error(f"Error generando SAS URL: {e}")
        # Fallback por si el SP no tiene permisos para delegación
        # (Aunque 'Storage Blob Data Contributor' debería tenerlo)
        return f"{ACCOUNT_URL}/{CONTAINER_NAME}/{blob_name} (Error: No se pudo firmar)"


def output_formatter(data, code=200):
    """Formatea la salida a XML (default) o JSON."""
    format_req = request.args.get('format', 'xml').lower()
    
    if format_req == 'json':
        return jsonify(data), code
    
    # Por defecto, XML
    xml_data = dicttoxml(data, custom_root='response', attr_type=False)
    return Response(xml_data, mimetype='application/xml', status=code)

def require_api_token(f):
    """Decorador para proteger rutas con API_TOKEN."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not API_TOKEN:
            return output_formatter({"error": "Autenticación no configurada en el servidor"}, 500)
        
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return output_formatter({"error": "Falta el header 'Authorization'"}, 401)
        
        try:
            auth_type, token = auth_header.split()
            if auth_type.lower() != 'bearer' or token != API_TOKEN:
                raise ValueError
        except ValueError:
            return output_formatter({"error": "Token inválido o mal formateado"}, 401)
        
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas de la API ---

@app.route('/')
def home():
    """Ruta de bienvenida y documentación Swagger."""
    return "Microservicio de Libros. Visita /apidocs para ver la documentación de Swagger."

@app.route('/upload', methods=['POST'])
@require_api_token
@swag_from({
    'tags': ['Imágenes'],
    'summary': 'Sube una nueva imagen al Blob Storage.',
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'image',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'Archivo de imagen (png, jpg, jpeg, gif). Máx 16MB.'
        },
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'Token Bearer (ej: "Bearer tu_token_secreto").'
        }
    ],
    'responses': {
        201: {'description': 'Imagen subida exitosamente.'},
        400: {'description': 'Error en la solicitud (archivo faltante, formato inválido, tamaño excedido).'},
        401: {'description': 'No autorizado (token inválido o faltante).'},
        500: {'description': 'Error interno del servidor (BD o Azure).'}
    }
})
def upload_image():
    """Ruta para subir una imagen."""
    if 'image' not in request.files:
        return output_formatter({"error": "No se encontró el archivo en la solicitud"}, 400)
    
    file = request.files['image']
    
    if file.filename == '':
        return output_formatter({"error": "No se seleccionó ningún archivo"}, 400)
    
    if file and allowed_file(file.filename):
        # Usar un nombre de archivo único para evitar colisiones
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{extension}"
        
        try:
            # Leer el archivo en memoria para obtener tamaño y contenido
            file_stream = file.read()
            file_size = len(file_stream)
            file.seek(0) # Regresar el puntero al inicio
            
            # 1. Subir a Azure Blob Storage
            blob_client = container_client.get_blob_client(unique_filename)
            blob_client.upload_blob(file_stream, blob_type="BlockBlob", overwrite=True)
            
            # 2. Generar URL SAS
            sas_url = generate_sas_url(unique_filename)
            
            # 3. Registrar en MariaDB
            conn = get_db_connection()
            if not conn:
                return output_formatter({"error": "No se pudo conectar a la base de datos"}, 500)
                
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO images 
                    (nombre_archivo, fecha_subida, tamaño_archivo, tipo_mime, url_firmada)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    unique_filename,
                    datetime.utcnow(),
                    file_size,
                    file.mimetype,
                    sas_url
                ))
            conn.commit()
            conn.close()

            return output_formatter({
                "mensaje": "Archivo subido exitosamente",
                "nombre_archivo": unique_filename,
                "url": sas_url
            }, 201)

        except pymysql.MySQLError as db_error:
            # Error de BD: Intentar borrar el blob subido para mantener consistencia
            try:
                blob_client.delete_blob()
            except Exception as azure_error:
                app.logger.error(f"Error al revertir subida en Azure: {azure_error}")
            return output_formatter({"error": f"Error de base de datos: {db_error}"}, 500)
        
        except Exception as e:
            # Error de Azure u otro
            return output_formatter({"error": f"Error al subir el archivo: {str(e)}"}, 500)
            
    else:
        return output_formatter({"error": "Formato de archivo no permitido"}, 400)

@app.route('/images', methods=['GET'])
@require_api_token
@swag_from({
    'tags': ['Imágenes'],
    'summary': 'Lista todas las imágenes registradas en la base de datos.',
    'parameters': [
        {
            'name': 'format',
            'in': 'query',
            'type': 'string',
            'required': False,
            'enum': ['json', 'xml'],
            'description': 'Formato de respuesta deseado. Default: xml.'
        },
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'Token Bearer (ej: "Bearer tu_token_secreto").'
        }
    ],
    'responses': {
        200: {'description': 'Lista de imágenes.'},
        401: {'description': 'No autorizado.'},
        500: {'description': 'Error interno del servidor (BD).'}
    }
})
def list_images():
    """Ruta para listar imágenes desde la BD."""
    try:
        conn = get_db_connection()
        if not conn:
            return output_formatter({"error": "No se pudo conectar a la base de datos"}, 500)
            
        with conn.cursor() as cursor:
            # Re-generamos las URLs SAS al momento de la consulta
            # para asegurar que siempre sean válidas por 1 hora.
            cursor.execute("SELECT id, nombre_archivo, fecha_subida, tamaño_archivo, tipo_mime FROM images ORDER BY fecha_subida DESC")
            images = cursor.fetchall()
        
        conn.close()
        
        # Procesar resultados y generar SAS URLs frescas
        images_list = []
        for img in images:
            img['url_acceso'] = generate_sas_url(img['nombre_archivo'])
            # Formatear fecha para que sea legible
            img['fecha_subida'] = img['fecha_subida'].isoformat()
            images_list.append(img)
            
        return output_formatter({"imagenes": images_list})

    except Exception as e:
        return output_formatter({"error": f"Error al consultar la base de datos: {str(e)}"}, 500)

# Manejadores de errores HTTP
@app.errorhandler(404)
def not_found(error):
    return output_formatter({"error": "Ruta no encontrada"}, 404)

@app.errorhandler(401)
def unauthorized(error):
    return output_formatter({"error": "No autorizado"}, 401)

@app.errorhandler(413)
def request_entity_too_large(error):
    return output_formatter({"error": f"El archivo excede el límite de {MAX_CONTENT_LENGTH / 1024 / 1024} MB"}, 413)

@app.errorhandler(500)
def internal_server_error(error):
    return output_formatter({"error": f"Error interno del servidor: {error}"}, 500)

if __name__ == '__main__':
    # El token debe estar en las variables de entorno, no aquí.
    if not API_TOKEN:
        print("Error: La variable de entorno 'API_TOKEN' no está configurada.")
    if not os.environ.get('AZURE_CLIENT_ID'):
         print("Error: Variables de entorno de Azure (CLIENT_ID, CLIENT_SECRET, TENANT_ID) no configuradas.")
    if not os.environ.get('DB_USER'):
        print("Error: Variables de entorno de MariaDB (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME) no configuradas.")
        
    app.run(debug=True, host='0.0.0.0', port=5000)