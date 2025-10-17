import xml.etree.ElementTree as ET
from flask import Flask, request, Response, g, render_template, send_from_directory
import mysql.connector
from mysql.connector import pooling
from flask_cors import CORS
import requests
from functools import wraps

# --- Configuración Flask ---
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app, resources={r"/api/*": {"origins": ["*"]}}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Accept", "Authorization"])

# --- URLs y Configuración de BD ---
AUTH_SERVICE_URL = "http://35.225.153.19:5000"

DB_CONFIG = {
    'host': 'localhost',
    'user': 'libros_user',
    'password': '666',
    'database': 'Libros',
}

# --- Pool de Conexiones (ajustado a 32, el máximo compatible) ---
try:
    cnxpool = pooling.MySQLConnectionPool(pool_name="libros_pool",
                                          pool_size=32,
                                          pool_reset_session=True,
                                          **DB_CONFIG)
    print("✅ Pool de conexiones a la BD (tamaño 32) creado exitosamente.")
except mysql.connector.Error as e:
    print(f"⚠️ Error al crear el pool de conexiones: {e}")
    cnxpool = None

# --- Gestión de Conexión (compatible y con espera implícita) ---
@app.before_request
def before_request():
    if cnxpool:
        try:
            g.db = cnxpool.get_connection()
        except mysql.connector.Error as e:
            print(f"Error al obtener conexión del pool: {e}")
            g.db = None
    else:
        g.db = None

@app.teardown_request
def teardown_request(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Decorador de Autenticación ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header: return create_message_xml("Token es requerido", 401)
        try:
            response = requests.get(f"{AUTH_SERVICE_URL}/protected", headers={'Authorization': auth_header})
            if response.status_code != 200:
                error_message = response.json().get("msg", "Token inválido o revocado")
                return create_message_xml(error_message, response.status_code)
        except requests.exceptions.RequestException as e:
            print(f"Error al contactar servicio de autenticación: {e}")
            return create_message_xml("Error interno del servidor al validar token", 500)
        return f(*args, **kwargs)
    return decorated

# --- Helpers y Clases de Error ---
def create_xml_response(books_data):
    catalog = ET.Element('catalog')
    for book_dict in books_data:
        book = ET.SubElement(catalog, 'book', isbn=str(book_dict.get('isbn', '')))
        ET.SubElement(book, 'title').text = book_dict.get('title', '')
        ET.SubElement(book, 'author').text = book_dict.get('authors', '')
        ET.SubElement(book, 'year').text = str(book_dict.get('year', ''))
        ET.SubElement(book, 'genre').text = book_dict.get('genre', '')
        ET.SubElement(book, 'price').text = str(book_dict.get('price', ''))
        ET.SubElement(book, 'stock').text = str(book_dict.get('stock', ''))
        ET.SubElement(book, 'format').text = book_dict.get('format', '')
    return Response('<?xml version="1.0" encoding="UTF-8"?>\n<?xml-stylesheet type="text/xsl" href="/libros.xsl"?>\n' + ET.tostring(catalog, encoding='UTF-8').decode('utf-8'), mimetype='application/xml')

def create_message_xml(message, status_code=200):
    root = ET.Element('response')
    ET.SubElement(root, 'message').text = message
    ET.SubElement(root, 'status').text = str(status_code)
    return Response(ET.tostring(root, encoding='UTF-8', xml_declaration=True).decode('utf-8'), mimetype='application/xml', status=status_code)

class CommandError(Exception):
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

# --- Lógica de Negocio (Completa y Refactorizada) ---
def handle_get_all_books_query():
    if not hasattr(g, 'db') or g.db is None: return None
    cur = g.db.cursor(dictionary=True)
    query = "SELECT b.isbn, b.title, b.year, b.price, b.stock, g.name AS genre, f.name AS format, GROUP_CONCAT(a.name SEPARATOR ', ') AS authors FROM books b LEFT JOIN genres g ON b.genre_id = g.genre_id LEFT JOIN formats f ON b.format_id = f.format_id LEFT JOIN book_authors ba ON b.isbn = ba.isbn LEFT JOIN authors a ON ba.author_id = a.author_id GROUP BY b.isbn ORDER BY b.title;"
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    return rows

def handle_get_book_by_isbn_query(isbn):
    if not hasattr(g, 'db') or g.db is None: return None
    cur = g.db.cursor(dictionary=True)
    query = "SELECT b.isbn, b.title, b.year, b.price, b.stock, g.name AS genre, f.name AS format, GROUP_CONCAT(a.name SEPARATOR ', ') AS authors FROM books b LEFT JOIN genres g ON b.genre_id = g.genre_id LEFT JOIN formats f ON b.format_id = f.format_id LEFT JOIN book_authors ba ON b.isbn = ba.isbn LEFT JOIN authors a ON ba.author_id = a.author_id WHERE b.isbn=%s GROUP BY b.isbn;"
    cur.execute(query, (isbn,))
    row = cur.fetchone()
    cur.close()
    return [row] if row else []

def handle_get_books_by_author_query(author):
    if not hasattr(g, 'db') or g.db is None: return None
    cur = g.db.cursor(dictionary=True)
    query = "SELECT b.isbn, b.title, b.year, b.price, b.stock, g.name AS genre, f.name AS format, GROUP_CONCAT(a.name SEPARATOR ', ') AS authors FROM books b JOIN book_authors ba ON b.isbn = ba.isbn JOIN authors a ON ba.author_id = a.author_id LEFT JOIN genres g ON b.genre_id = g.genre_id LEFT JOIN formats f ON b.format_id = f.format_id WHERE a.name=%s GROUP BY b.isbn;"
    cur.execute(query, (author,))
    rows = cur.fetchall()
    cur.close()
    return rows

def handle_get_books_by_format_query(format_name):
    if not hasattr(g, 'db') or g.db is None: return None
    cur = g.db.cursor(dictionary=True)
    query = "SELECT b.isbn, b.title, b.year, b.price, b.stock, g.name AS genre, f.name AS format, GROUP_CONCAT(a.name SEPARATOR ', ') AS authors FROM books b LEFT JOIN genres g ON b.genre_id = g.genre_id LEFT JOIN formats f ON b.format_id = f.format_id LEFT JOIN book_authors ba ON b.isbn = ba.isbn LEFT JOIN authors a ON ba.author_id = a.author_id WHERE f.name=%s GROUP BY b.isbn;"
    cur.execute(query, (format_name,))
    rows = cur.fetchall()
    cur.close()
    return rows

def handle_insert_book_command(data):
    if not hasattr(g, 'db') or g.db is None: raise CommandError("Error de conexión con la BD", 500)
    cur = g.db.cursor(dictionary=True)
    try:
        cur.execute("SELECT genre_id FROM genres WHERE name=%s", (data['genre'],))
        g_row = cur.fetchone()
        if not g_row: raise CommandError("Género inválido")
        genre_id = g_row['genre_id']

        cur.execute("SELECT format_id FROM formats WHERE name=%s", (data['format'],))
        f_row = cur.fetchone()
        if not f_row: raise CommandError("Formato inválido")
        format_id = f_row['format_id']

        cur.execute("INSERT INTO books (isbn,title,year,price,stock,genre_id,format_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (data['isbn'], data['title'], data['year'], data['price'], data['stock'], genre_id, format_id))

        for author_name in [a.strip() for a in data['authors'].split(',')]:
            cur.execute("SELECT author_id FROM authors WHERE name=%s", (author_name,))
            a_row = cur.fetchone()
            if not a_row: raise CommandError(f"Autor '{author_name}' inválido")
            author_id = a_row['author_id']
            cur.execute("INSERT INTO book_authors (isbn,author_id) VALUES (%s,%s)", (data['isbn'], author_id))

        g.db.commit()
    except (mysql.connector.Error, KeyError) as e:
        g.db.rollback()
        if isinstance(e, mysql.connector.Error) and e.errno == 1062:
            raise CommandError(f"Error: Ya existe un libro con el ISBN {data['isbn']}", 409)
        print(f"Error en la transacción de inserción: {e}")
        raise CommandError("Error en la base de datos al insertar", 500)
    finally:
        cur.close()

def handle_update_book_command(isbn, data):
    if not hasattr(g, 'db') or g.db is None: raise CommandError("Error de conexión con la BD", 500)
    cur = g.db.cursor(dictionary=True)
    try:
        fields, vals = [], []
        for k in ['title','year','price','stock']:
            if k in data:
                fields.append(f"{k}=%s")
                vals.append(data[k])
        if not fields: raise CommandError("No hay campos para actualizar", 400)

        sql = f"UPDATE books SET {', '.join(fields)} WHERE isbn=%s"
        vals.append(isbn)
        cur.execute(sql, vals)

        if cur.rowcount == 0:
            raise CommandError(f"No se encontró ningún libro con el ISBN {isbn} para actualizar", 404)
        g.db.commit()
    except mysql.connector.Error as e:
        g.db.rollback()
        print(f"Error en la transacción de actualización: {e}")
        raise CommandError("Error en la base de datos al actualizar", 500)
    finally:
        cur.close()

def handle_delete_books_command(isbns):
    if not hasattr(g, 'db') or g.db is None: raise CommandError("Error de conexión con la BD", 500)
    cur = g.db.cursor(dictionary=True)
    try:
        format_str = ','.join(['%s'] * len(isbns))
        cur.execute(f"DELETE FROM book_authors WHERE isbn IN ({format_str})", tuple(isbns))
        cur.execute(f"DELETE FROM books WHERE isbn IN ({format_str})", tuple(isbns))

        if cur.rowcount == 0:
            raise CommandError("No se encontraron libros con esos ISBNs para borrar", 404)
        g.db.commit()
    except mysql.connector.Error as e:
        g.db.rollback()
        print(f"Error en la transacción de borrado: {e}")
        raise CommandError("Error en la base de datos al borrar", 500)
    finally:
        cur.close()

# --- Endpoints ---
@app.route('/api/books', methods=['GET'])
@token_required
def get_books():
    rows = handle_get_all_books_query()
    if rows is None: return create_message_xml("Error en la base de datos", 500)
    return create_xml_response(rows)

@app.route('/api/books/isbn/<isbn>', methods=['GET'])
@token_required
def get_book(isbn):
    rows = handle_get_book_by_isbn_query(isbn)
    if rows is None: return create_message_xml("Error en la base de datos", 500)
    if not rows: return create_message_xml("Libro no encontrado", 404)
    return create_xml_response(rows)

@app.route('/api/books/author/<author>', methods=['GET'])
@token_required
def get_books_by_author(author):
    rows = handle_get_books_by_author_query(author)
    if rows is None: return create_message_xml("Error en la base de datos", 500)
    if not rows: return create_message_xml("No se encontraron libros para este autor", 404)
    return create_xml_response(rows)

@app.route('/api/books/format/<format_name>', methods=['GET'])
@token_required
def get_books_by_format(format_name):
    rows = handle_get_books_by_format_query(format_name)
    if rows is None: return create_message_xml("Error en la base de datos", 500)
    if not rows: return create_message_xml("No se encontraron libros para este formato", 404)
    return create_xml_response(rows)

@app.route('/api/books/insert', methods=['POST'])
@token_required
def insert_book():
    data = request.get_json()
    required = ['isbn','title','year','price','stock','genre','format','authors']
    if not data or not all(k in data for k in required):
        return create_message_xml("Faltan campos requeridos", 400)
    try:
        handle_insert_book_command(data)
        return create_message_xml("Libro insertado exitosamente", 201)
    except CommandError as e:
        return create_message_xml(e.message, e.status_code)

@app.route('/api/books/update/<isbn>', methods=['PUT'])
@token_required
def update_book(isbn):
    data = request.get_json()
    if not data: return create_message_xml("Cuerpo de la petición vacío o sin JSON", 400)
    try:
        handle_update_book_command(isbn, data)
        return create_message_xml("Libro actualizado", 200)
    except CommandError as e:
        return create_message_xml(e.message, e.status_code)

@app.route('/api/books/delete', methods=['DELETE'])
@token_required
def delete_books():
    data = request.get_json()
    if not data or 'isbns' not in data or not isinstance(data['isbns'], list) or not data['isbns']:
        return create_message_xml("Formato incorrecto: se requiere un JSON con una lista de ISBNs", 400)
    try:
        handle_delete_books_command(data['isbns'])
        return create_message_xml("Libros borrados", 200)
    except CommandError as e:
        return create_message_xml(e.message, e.status_code)

# --- Endpoints de interfaz ---
@app.route('/libros.xsl')
def get_xsl():
    return send_from_directory('.', 'libros.xsl', mimetype='application/xml')

@app.route('/')
def home():
    return render_template('index.html')

# --- Bloque de Ejecución (SOLO para desarrollo local, no para Gunicorn) ---
if __name__ == '__main__':
    if cnxpool:
        app.run(host='0.0.0.0', port=5001, debug=True)
    else:
        print(">>>>> LA APLICACIÓN NO PUEDE INICIAR: NO SE PUDO CREAR EL POOL DE CONEXIONES A LA BD. <<<<<")
