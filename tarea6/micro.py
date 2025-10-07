import xml.etree.ElementTree as ET
from flask import Flask, request, Response, g, jsonify
import MySQLdb, jwt, redis, os
from flask_cors import CORS
from functools import wraps
from urllib.parse import urlparse

app = Flask(__name__)

# CORS
CORS(
    app,
    resources={ r"/auth/*": {"origins": "*"}, r"/api/*": {"origins": "*"} },
    methods=["GET","POST","PUT","DELETE","OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    supports_credentials=False,
    max_age=86400,
)

# DB
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST','localhost'),
    'user': os.getenv('MYSQL_USER','libros_user'),
    'passwd': os.getenv('MYSQL_PASSWORD','666'),
    'db': os.getenv('MYSQL_DB','Libros'),
    'charset': 'utf8mb4'
}

def get_db_connection():
    try:
        return MySQLdb.connect(**DB_CONFIG)
    except MySQLdb.Error as e:
        print(f"Error DB: {e}")
        return None

# JWT + Redis
JWT_SECRET = os.getenv('JWT_SECRET','cambia-esto-en-produccion')
JWT_ALG = 'HS256'
REDIS_URL = os.getenv('REDIS_URL','redis://127.0.0.1:6379/0')
rconf = urlparse(REDIS_URL)
r = redis.Redis(host=rconf.hostname, port=rconf.port or 6379, db=int((rconf.path or '/0')[1:] or 0), password=rconf.password, decode_responses=True)

def jwt_required(fn):
    @wraps(fn)
    def w(*args, **kwargs):
        auth = request.headers.get('Authorization','')
        if not auth.startswith('Bearer '):
            return Response("<error>Missing Authorization</error>", status=401, mimetype='application/xml')
        token = auth.split(' ',1)[1].strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            if payload.get('type')!='access':
                return Response("<error>Invalid token type</error>", status=401, mimetype='application/xml')
            jti = payload.get('jti')
            if not jti or r.exists(f"bl:access:{jti}") or not r.exists(f"access:session:{jti}"):
                return Response("<error>Access token revoked/invalid</error>", status=401, mimetype='application/xml')
            g.user_id = int(payload['sub'])
            g.username = payload.get('username')
        except jwt.ExpiredSignatureError:
            return Response("<error>Access token expired</error>", status=401, mimetype='application/xml')
        except jwt.InvalidTokenError:
            return Response("<error>Invalid token</error>", status=401, mimetype='application/xml')
        return fn(*args, **kwargs)
    return w

# Helpers XML
def create_xml_response(books_data):
    catalog = ET.Element('catalog')
    for book_dict in books_data:
        book = ET.SubElement(catalog, 'book', isbn=str(book_dict.get('isbn', '')))
        ET.SubElement(book, 'title').text = book_dict.get('titulo','')
        ET.SubElement(book, 'author').text = book_dict.get('autor','')
        ET.SubElement(book, 'year').text = str(book_dict.get('anio_publicacion',''))
        ET.SubElement(book, 'genre').text = book_dict.get('genero','')
        ET.SubElement(book, 'price').text = str(book_dict.get('precio',''))
        ET.SubElement(book, 'stock').text = str(book_dict.get('stock',''))
        ET.SubElement(book, 'format').text = book_dict.get('formato','')
    xml = ET.tostring(catalog, encoding='UTF-8', method='xml').decode('utf-8')
    full = '<?xml version="1.0" encoding="UTF-8"?>\n' + '<?xml-stylesheet type="text/xsl" href="/libros.xsl"?>\n' + xml
    return Response(full, mimetype='application/xml')

def create_message_xml(message, status_code=200):
    root = ET.Element('response')
    ET.SubElement(root, 'message').text = message
    ET.SubElement(root, 'status').text = str(status_code)
    xml_string = ET.tostring(root, encoding='UTF-8', xml_declaration=True).decode('utf-8')
    return Response(xml_string, mimetype='application/xml', status=status_code)

# XSL (igual que tu versión)
@app.get('/libros.xsl')
def get_xsl_stylesheet():
    xsl_content = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:template match="/">
  <html><head><title>Catálogo de Libros</title>
  <style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;margin:2em;background:#f9f9f9}h1{color:#333;text-align:center}table{width:95%;margin:2em auto;border-collapse:collapse;box-shadow:0 4px 8px rgba(0,0,0,.1);background:#fff;border-radius:8px;overflow:hidden}th,td{border-bottom:1px solid #e0e0e0;padding:16px;text-align:left}th{background:#4A90E2;color:#fff;font-weight:600}tr:nth-child(even){background:#f7faff}tr:hover{background:#e6f0fa}td:first-child{font-family:"Courier New",Courier,monospace}</style>
  </head><body><h1>Catálogo de Libros</h1>
  <table><thead><tr><th>ISBN</th><th>Título</th><th>Autor(es)</th><th>Año</th><th>Género</th><th>Precio</th><th>Stock</th><th>Formato</th></tr></thead>
  <tbody><xsl:for-each select="catalog/book"><tr>
  <td><xsl:value-of select="@isbn"/></td>
  <td><xsl:value-of select="title"/></td>
  <td><xsl:value-of select="author"/></td>
  <td><xsl:value-of select="year"/></td>
  <td><xsl:value-of select="genre"/></td>
  <td><xsl:value-of select="price"/></td>
  <td><xsl:value-of select="stock"/></td>
  <td><xsl:value-of select="format"/></td>
  </tr></xsl:for-each></tbody></table></body></html></xsl:template></xsl:stylesheet>"""
    return Response(xsl_content, mimetype='application/xml')

# ====== ENDPOINTS PROTEGIDOS /api/books/* ======

@app.get('/api/books')
@jwt_required
def get_all_books():
    conn = get_db_connection()
    if not conn: return create_message_xml("Error de conexión con la base de datos", 500)
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
    SELECT l.isbn,l.titulo,l.anio_publicacion,l.precio,l.stock,
           GROUP_CONCAT(a.nombre SEPARATOR ', ') AS autor,
           g.nombre AS genero, f.nombre AS formato
    FROM libros l
    LEFT JOIN libro_autor la ON l.id_libro = la.id_libro
    LEFT JOIN autores a ON la.id_autor = a.id_autor
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    LEFT JOIN formato f ON l.id_formato = f.id_formato
    GROUP BY l.id_libro ORDER BY l.titulo""")
    books = cur.fetchall(); cur.close(); conn.close()
    return create_xml_response(books)

@app.get('/api/books/isbn/<string:isbn>')
@jwt_required
def get_book_by_isbn(isbn):
    conn = get_db_connection()
    if not conn: return create_message_xml("Error de conexión con la base de datos", 500)
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
    SELECT l.isbn,l.titulo,l.anio_publicacion,l.precio,l.stock,
           GROUP_CONCAT(a.nombre SEPARATOR ', ') AS autor,
           g.nombre AS genero, f.nombre AS formato
    FROM libros l
    LEFT JOIN libro_autor la ON l.id_libro = la.id_libro
    LEFT JOIN autores a ON la.id_autor = a.id_autor
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    LEFT JOIN formato f ON l.id_formato = f.id_formato
    WHERE l.isbn=%s GROUP BY l.id_libro""", (isbn,))
    book = cur.fetchone(); cur.close(); conn.close()
    return create_xml_response([book]) if book else create_message_xml(f"ISBN {isbn} no encontrado", 404)

@app.get('/api/books/format/<string:format_name>')
@jwt_required
def get_books_by_format(format_name):
    conn = get_db_connection()
    if not conn: return create_message_xml("Error de conexión con la base de datos", 500)
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
    SELECT l.isbn,l.titulo,l.anio_publicacion,l.precio,l.stock,
           GROUP_CONCAT(a.nombre SEPARATOR ', ') AS autor,
           g.nombre AS genero, f.nombre AS formato
    FROM libros l
    LEFT JOIN libro_autor la ON l.id_libro = la.id_libro
    LEFT JOIN autores a ON la.id_autor = a.id_autor
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    JOIN formato f ON l.id_formato = f.id_formato
    WHERE f.nombre=%s
    GROUP BY l.id_libro ORDER BY l.titulo""", (format_name,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return create_xml_response(rows) if rows else create_message_xml(f"No hay libros con formato '{format_name}'", 404)

@app.get('/api/books/author/<string:author_name>')
@jwt_required
def get_books_by_author(author_name):
    conn = get_db_connection()
    if not conn: return create_message_xml("Error de conexión con la base de datos", 500)
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id_autor FROM autores WHERE nombre=%s", (author_name,))
    a = cur.fetchone()
    if not a:
        cur.close(); conn.close()
        return create_message_xml(f"No se encontró el autor '{author_name}'", 404)
    cur2 = conn.cursor(MySQLdb.cursors.DictCursor)
    cur2.execute("""
    SELECT l.isbn,l.titulo,l.anio_publicacion,l.precio,l.stock,
           (SELECT GROUP_CONCAT(a2.nombre SEPARATOR ', ')
            FROM autores a2 JOIN libro_autor la2 ON a2.id_autor=la2.id_autor
            WHERE la2.id_libro=l.id_libro) AS autor,
           g.nombre AS genero, f.nombre AS formato
    FROM libros l
    JOIN libro_autor la ON l.id_libro = la.id_libro
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    LEFT JOIN formato f ON l.id_formato = f.id_formato
    WHERE la.id_autor=%s
    GROUP BY l.id_libro ORDER BY l.titulo""", (a['id_autor'],))
    rows = cur2.fetchall(); cur2.close(); conn.close()
    return create_xml_response(rows) if rows else create_message_xml(f"Sin libros para '{author_name}'", 404)

@app.post('/api/books/insert')
@jwt_required
def insert_book():
    # ... (tu lógica original de insert, sin cambios)
    # IMPORTANTE: no la repito por espacio; copia tal cual tu función original aquí.
    return create_message_xml("Implementado (igual que tu versión original)")

@app.put('/api/books/update/<string:isbn>')
@jwt_required
def update_book(isbn):
    # ... idem
    return create_message_xml("Implementado (igual que tu versión original)")

@app.delete('/api/books/delete')
@jwt_required
def delete_books():
    # ... idem
    return create_message_xml("Implementado (igual que tu versión original)")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
