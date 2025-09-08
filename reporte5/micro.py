import xml.etree.ElementTree as ET
from flask import Flask, request, Response
import MySQLdb
from flask_cors import CORS

# --- Configuración de la Aplicación Flask ---
app = Flask(__name__)

# Permite solo tu frontend en desarrollo (ajusta el origen):
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://172.206.106.38:8080"  # por si sirves el HTML desde aquí
            ]
        },
        r"/libros.xsl": {  # si tu cliente carga el XSL remoto
            "origins": ["*"]  # o restringe igual que /api/*
        },
    },
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    expose_headers=["Content-Type"],
    supports_credentials=False,
    max_age=86400,
)

# --- Configuración de la Conexión a la Base de Datos ---
# Asegúrate de que el host sea el correcto (ej. 'localhost' o la IP del contenedor si usas Docker)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'libros_user',
    'passwd': '666',
    'db': 'Libros',
    'charset': 'utf8mb4' # Usar utf8mb4 para soportar caracteres especiales
}

def get_db_connection():
    """Establece y retorna una conexión a la base de datos."""
    try:
        conn = MySQLdb.connect(**DB_CONFIG)
        return conn
    except MySQLdb.Error as e:
        # En una aplicación real, aquí registraríamos el error en un log.
        print(f"Error al conectar a la base de datos: {e}")
        return None

# --- Funciones Auxiliares para generar XML ---

def create_xml_response(books_data):
    """
    Construye una respuesta XML a partir de una lista de diccionarios de libros.
    """
    # Raíz del documento
    catalog = ET.Element('catalog')

    for book_dict in books_data:
        book_element = ET.SubElement(catalog, 'book', isbn=str(book_dict.get('isbn', '')))
        
        # Crear y añadir cada sub-elemento
        ET.SubElement(book_element, 'title').text = book_dict.get('titulo', '')
        ET.SubElement(book_element, 'author').text = book_dict.get('autor', '')
        ET.SubElement(book_element, 'year').text = str(book_dict.get('anio_publicacion', ''))
        ET.SubElement(book_element, 'genre').text = book_dict.get('genero', '')
        ET.SubElement(book_element, 'price').text = str(book_dict.get('precio', ''))
        ET.SubElement(book_element, 'stock').text = str(book_dict.get('stock', ''))
        ET.SubElement(book_element, 'format').text = book_dict.get('formato', '')
    
    # Convierte el árbol XML a una cadena de texto SIN la declaración XML por ahora
    catalog_string = ET.tostring(catalog, encoding='UTF-8', method='xml').decode('utf-8')
    
    # Construimos la respuesta final manualmente para incluir ambas instrucciones de procesamiento
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    # La referencia href ahora apunta a una ruta válida que sirve el archivo XSL
    xsl_pi = '<?xml-stylesheet type="text/xsl" href="/libros.xsl"?>\n'
    
    full_xml_string = xml_declaration + xsl_pi + catalog_string
    
    return Response(full_xml_string, mimetype='application/xml')

def create_message_xml(message, status_code=200):
    """Crea una respuesta XML simple para mensajes de éxito o error."""
    root = ET.Element('response')
    ET.SubElement(root, 'message').text = message
    ET.SubElement(root, 'status').text = str(status_code)
    xml_string = ET.tostring(root, encoding='UTF-8', xml_declaration=True).decode('utf-8')
    return Response(xml_string, mimetype='application/xml', status=status_code)

# --- Endpoints de la API ---

@app.route('/libros.xsl', methods=['GET'])
def get_xsl_stylesheet():
    """Sirve el archivo de transformación XSLT para que el navegador pueda renderizar el XML."""
    xsl_content = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:template match="/">
  <html>
  <head>
    <title>Catálogo de Libros</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 2em; background-color: #f9f9f9; }
      h1 { color: #333; text-align: center; }
      table { width: 95%; margin: 2em auto; border-collapse: collapse; box-shadow: 0 4px 8px rgba(0,0,0,0.1); background-color: white; border-radius: 8px; overflow: hidden; }
      th, td { border-bottom: 1px solid #e0e0e0; padding: 16px; text-align: left; }
      th { background-color: #4A90E2; color: white; font-weight: 600; }
      tr:nth-child(even) { background-color: #f7faff; }
      tr:hover { background-color: #e6f0fa; }
      td:first-child { font-family: "Courier New", Courier, monospace; }
    </style>
  </head>
  <body>
    <h1>Catálogo de Libros</h1>
    <table>
      <thead>
        <tr>
            <th>ISBN</th>
            <th>Título</th>
            <th>Autor(es)</th>
            <th>Año</th>
            <th>Género</th>
            <th>Precio</th>
            <th>Stock</th>
            <th>Formato</th>
        </tr>
      </thead>
      <tbody>
        <xsl:for-each select="catalog/book">
        <tr>
            <td><xsl:value-of select="@isbn"/></td>
            <td><xsl:value-of select="title"/></td>
            <td><xsl:value-of select="author"/></td>
            <td><xsl:value-of select="year"/></td>
            <td><xsl:value-of select="genre"/></td>
            <td><xsl:value-of select="price"/></td>
            <td><xsl:value-of select="stock"/></td>
            <td><xsl:value-of select="format"/></td>
        </tr>
        </xsl:for-each>
      </tbody>
    </table>
  </body>
  </html>
</xsl:template>
</xsl:stylesheet>
"""
    return Response(xsl_content, mimetype='application/xml')

@app.route('/api/books', methods=['GET'])
def get_all_books():
    """Muestra todos los libros."""
    conn = get_db_connection()
    if not conn:
        return create_message_xml("Error de conexión con la base de datos", 500)
    
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    query = """
    SELECT 
        l.isbn, l.titulo, l.anio_publicacion, l.precio, l.stock,
        GROUP_CONCAT(a.nombre SEPARATOR ', ') AS autor,
        g.nombre AS genero,
        f.nombre AS formato
    FROM libros l
    LEFT JOIN libro_autor la ON l.id_libro = la.id_libro
    LEFT JOIN autores a ON la.id_autor = a.id_autor
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    LEFT JOIN formato f ON l.id_formato = f.id_formato
    GROUP BY l.id_libro
    ORDER BY l.titulo;
    """
    
    cursor.execute(query)
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return create_xml_response(books)

@app.route('/api/books/isbn/<string:isbn>', methods=['GET'])
def get_book_by_isbn(isbn):
    """Busca un libro por su ISBN."""
    conn = get_db_connection()
    if not conn:
        return create_message_xml("Error de conexión con la base de datos", 500)
    
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    query = """
    SELECT 
        l.isbn, l.titulo, l.anio_publicacion, l.precio, l.stock,
        GROUP_CONCAT(a.nombre SEPARATOR ', ') AS autor,
        g.nombre AS genero,
        f.nombre AS formato
    FROM libros l
    LEFT JOIN libro_autor la ON l.id_libro = la.id_libro
    LEFT JOIN autores a ON la.id_autor = a.id_autor
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    LEFT JOIN formato f ON l.id_formato = f.id_formato
    WHERE l.isbn = %s
    GROUP BY l.id_libro;
    """
    
    cursor.execute(query, (isbn,))
    book = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if book:
        return create_xml_response([book])
    else:
        return create_message_xml(f"Libro con ISBN {isbn} no encontrado.", 404)

@app.route('/api/books/format/<string:format_name>', methods=['GET'])
def get_books_by_format(format_name):
    """Busca libros por formato."""
    conn = get_db_connection()
    if not conn:
        return create_message_xml("Error de conexión con la base de datos", 500)
    
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    query = """
    SELECT 
        l.isbn, l.titulo, l.anio_publicacion, l.precio, l.stock,
        GROUP_CONCAT(a.nombre SEPARATOR ', ') AS autor,
        g.nombre AS genero,
        f.nombre AS formato
    FROM libros l
    LEFT JOIN libro_autor la ON l.id_libro = la.id_libro
    LEFT JOIN autores a ON la.id_autor = a.id_autor
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    JOIN formato f ON l.id_formato = f.id_formato
    WHERE f.nombre = %s
    GROUP BY l.id_libro
    ORDER BY l.titulo;
    """
    
    cursor.execute(query, (format_name,))
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if books:
        return create_xml_response(books)
    else:
        return create_message_xml(f"No se encontraron libros con el formato '{format_name}'.", 404)

@app.route('/api/books/author/<string:author_name>', methods=['GET'])
def get_books_by_author(author_name):
    """Busca libros por autor."""
    conn = get_db_connection()
    if not conn:
        return create_message_xml("Error de conexión con la base de datos", 500)
    
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # Buscamos el id del autor primero
    cursor.execute("SELECT id_autor FROM autores WHERE nombre = %s", (author_name,))
    author = cursor.fetchone()
    
    if not author:
        cursor.close()
        conn.close()
        return create_message_xml(f"No se encontró el autor '{author_name}'.", 404)
        
    query = """
    SELECT 
        l.isbn, l.titulo, l.anio_publicacion, l.precio, l.stock,
        (SELECT GROUP_CONCAT(a_inner.nombre SEPARATOR ', ') FROM autores a_inner JOIN libro_autor la_inner ON a_inner.id_autor = la_inner.id_autor WHERE la_inner.id_libro = l.id_libro) AS autor,
        g.nombre AS genero,
        f.nombre AS formato
    FROM libros l
    JOIN libro_autor la ON l.id_libro = la.id_libro
    LEFT JOIN genero g ON l.id_genero = g.id_genero
    LEFT JOIN formato f ON l.id_formato = f.id_formato
    WHERE la.id_autor = %s
    GROUP BY l.id_libro
    ORDER BY l.titulo;
    """
    
    cursor.execute(query, (author['id_autor'],))
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if books:
        return create_xml_response(books)
    else:
        # Esto es poco probable si el autor existe, pero es una buena práctica.
        return create_message_xml(f"No se encontraron libros para el autor '{author_name}'.", 404)


@app.route('/api/books/insert', methods=['POST'])
def insert_book():
    """Inserta un nuevo libro. Se esperan los datos en formato JSON."""
    data = request.get_json()
    if not data:
        return create_message_xml("No se recibieron datos JSON.", 400)

    # Campos requeridos
    required_fields = ['isbn', 'titulo', 'anio_publicacion', 'precio', 'stock', 'genero', 'formato', 'autor']
    if not all(field in data for field in required_fields):
        return create_message_xml(f"Faltan campos requeridos. Se necesitan: {', '.join(required_fields)}", 400)

    conn = get_db_connection()
    if not conn:
        return create_message_xml("Error de conexión con la base de datos", 500)

    cursor = conn.cursor()
    try:
        # Obtener IDs de género y formato (o crearlos si no existen)
        cursor.execute("SELECT id_genero FROM genero WHERE nombre = %s", (data['genero'],))
        result = cursor.fetchone()
        id_genero = result[0] if result else None
        
        cursor.execute("SELECT id_formato FROM formato WHERE nombre = %s", (data['formato'],))
        result = cursor.fetchone()
        id_formato = result[0] if result else None
        
        if not id_genero or not id_formato:
            raise ValueError("Género o formato no válido.")

        # Insertar libro
        sql_insert_libro = """
        INSERT INTO libros (isbn, titulo, anio_publicacion, precio, stock, id_genero, id_formato)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        libro_values = (data['isbn'], data['titulo'], data['anio_publicacion'], data['precio'], data['stock'], id_genero, id_formato)
        cursor.execute(sql_insert_libro, libro_values)
        id_libro_nuevo = cursor.lastrowid

        # Manejar autor(es)
        autores = [a.strip() for a in data['autor'].split(',')]
        for autor_nombre in autores:
            cursor.execute("SELECT id_autor FROM autores WHERE nombre = %s", (autor_nombre,))
            result = cursor.fetchone()
            id_autor = result[0] if result else None
            if not id_autor:
                raise ValueError(f"El autor '{autor_nombre}' no existe en la base de datos.")
            
            # Insertar en la tabla intermedia
            cursor.execute("INSERT INTO libro_autor (id_libro, id_autor) VALUES (%s, %s)", (id_libro_nuevo, id_autor))

        conn.commit()
        return create_message_xml(f"Libro con ISBN {data['isbn']} insertado correctamente.", 201)

    except MySQLdb.IntegrityError as e:
        conn.rollback()
        return create_message_xml(f"Error de integridad: El ISBN '{data['isbn']}' probablemente ya existe. ({e})", 409)
    except (MySQLdb.Error, ValueError) as e:
        conn.rollback()
        return create_message_xml(f"Error en la base de datos o en los datos proporcionados: {e}", 500)
    finally:
        cursor.close()
        conn.close()


@app.route('/api/books/update/<string:isbn>', methods=['PUT'])
def update_book(isbn):
    """Actualiza un libro por ISBN. Se esperan los datos a actualizar en JSON."""
    data = request.get_json()
    if not data:
        return create_message_xml("No se recibieron datos JSON para actualizar.", 400)

    conn = get_db_connection()
    if not conn:
        return create_message_xml("Error de conexión con la base de datos", 500)
    
    cursor = conn.cursor()

    try:
        # Verificar si el libro existe
        cursor.execute("SELECT id_libro FROM libros WHERE isbn = %s", (isbn,))
        libro_existente = cursor.fetchone()
        if not libro_existente:
            return create_message_xml(f"Libro con ISBN {isbn} no encontrado.", 404)

        # Construir la consulta de actualización dinámicamente
        fields_to_update = []
        values_to_update = []
        
        # Campos de la tabla 'libros'
        mapeo_campos = {
            'titulo': 'titulo', 'anio_publicacion': 'anio_publicacion', 
            'precio': 'precio', 'stock': 'stock'
        }
        for key, value in data.items():
            if key in mapeo_campos:
                fields_to_update.append(f"{mapeo_campos[key]} = %s")
                values_to_update.append(value)
        
        # Actualizar si hay campos
        if fields_to_update:
            sql_update = f"UPDATE libros SET {', '.join(fields_to_update)} WHERE isbn = %s"
            values_to_update.append(isbn)
            cursor.execute(sql_update, tuple(values_to_update))

        conn.commit()
        
        if cursor.rowcount > 0:
            return create_message_xml(f"Libro con ISBN {isbn} actualizado correctamente.", 200)
        else:
            return create_message_xml(f"No se realizaron cambios en el libro con ISBN {isbn} (puede que los datos fueran los mismos).", 200)

    except MySQLdb.Error as e:
        conn.rollback()
        return create_message_xml(f"Error al actualizar la base de datos: {e}", 500)
    finally:
        cursor.close()
        conn.close()

@app.route('/api/books/delete', methods=['DELETE'])
def delete_books():
    """Borra uno o varios libros por ISBN. Espera un JSON con una lista de ISBNs: {"isbns": ["...", "..."]}"""
    data = request.get_json()
    if not data or 'isbns' not in data or not isinstance(data['isbns'], list):
        return create_message_xml("Formato de solicitud incorrecto. Se espera un JSON con una clave 'isbns' que contenga una lista de ISBNs.", 400)

    isbns_to_delete = data['isbns']
    if not isbns_to_delete:
        return create_message_xml("La lista de ISBNs para borrar está vacía.", 400)

    conn = get_db_connection()
    if not conn:
        return create_message_xml("Error de conexión con la base de datos", 500)

    cursor = conn.cursor()
    try:
        # Obtener los id_libro correspondientes a los ISBNs
        format_strings = ','.join(['%s'] * len(isbns_to_delete))
        cursor.execute(f"SELECT id_libro FROM libros WHERE isbn IN ({format_strings})", tuple(isbns_to_delete))
        libros_a_borrar = cursor.fetchall()
        
        if not libros_a_borrar:
            return create_message_xml("Ninguno de los ISBNs proporcionados fue encontrado.", 404)

        ids_libros = [item[0] for item in libros_a_borrar]
        format_ids = ','.join(['%s'] * len(ids_libros))

        # Borrar de la tabla intermedia primero por la restricción de clave foránea
        cursor.execute(f"DELETE FROM libro_autor WHERE id_libro IN ({format_ids})", tuple(ids_libros))

        # Borrar de la tabla principal de libros
        cursor.execute(f"DELETE FROM libros WHERE id_libro IN ({format_ids})", tuple(ids_libros))
        
        conn.commit()
        
        return create_message_xml(f"Se borraron {cursor.rowcount} libro(s) correctamente.", 200)

    except MySQLdb.Error as e:
        conn.rollback()
        return create_message_xml(f"Error al borrar en la base de datos: {e}", 500)
    finally:
        cursor.close()
        conn.close()

# --- Punto de Entrada de la Aplicación ---
if __name__ == '__main__':
    # '0.0.0.0' hace que el servidor sea accesible desde cualquier IP de la red.
    app.run(host='0.0.0.0', port=5000, debug=True)


