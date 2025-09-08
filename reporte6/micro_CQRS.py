# cqrs_libros.py
# Flask + MySQLdb con CQRS básico: /query/* (solo lectura) y /command/* (solo escritura)
# Mantiene respuestas XML con XSL en las consultas.

import json
import uuid
from datetime import datetime
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, TYPE_CHECKING

from flask import Flask, request, Response, Blueprint
import MySQLdb
from flask_cors import CORS

if TYPE_CHECKING:
    from MySQLdb.connections import Connection

# -----------------------------------------------------------------------------
# Configuración Flask + CORS
# -----------------------------------------------------------------------------
app = Flask(__name__)

CORS(
    app,
    resources={
        r"/query/*": {
            "origins": [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://[::1]:8080",
                "http://172.206.106.38:8080",
            ]
        },
        r"/command/*": {
            "origins": [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://[::1]:8080",
                "http://172.206.106.38:8080",
            ]
        },
        r"/libros.xsl": {"origins": ["*"]},
        r"/libros_fragment.xsl": {"origins": ["*"]},
    },
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Idempotency-Key"],
    expose_headers=["Content-Type"],
    supports_credentials=False,
    max_age=86400,
)

# -----------------------------------------------------------------------------
# Config DB: separa lectura y escritura (pueden ser iguales si no tienes réplicas)
# -----------------------------------------------------------------------------
DB_READ = {
    "host": "localhost",
    "user": "libros_user",
    "passwd": "666",
    "db": "Libros",
    "charset": "utf8mb4",
}

DB_WRITE = {
    "host": "localhost",
    "user": "libros_user",
    "passwd": "666",
    "db": "Libros",
    "charset": "utf8mb4",
}

def get_conn(cfg):  # anotación relajada para evitar AttributeError en algunos entornos
    try:
        return MySQLdb.connect(**cfg)
    except MySQLdb.Error as e:
        print(f"[DB] Error de conexión: {e}")
        return None

# -----------------------------------------------------------------------------
# Helpers XML
# -----------------------------------------------------------------------------
def xml_catalog_from_books(books_data: List[Dict]) -> Response:
    catalog = ET.Element("catalog")
    for b in books_data:
        book = ET.SubElement(catalog, "book", isbn=str(b.get("isbn", "")))
        ET.SubElement(book, "title").text = b.get("titulo", "")
        ET.SubElement(book, "author").text = b.get("autor", "")
        ET.SubElement(book, "year").text = str(b.get("anio_publicacion", ""))
        ET.SubElement(book, "genre").text = b.get("genero", "")
        ET.SubElement(book, "price").text = str(b.get("precio", ""))
        ET.SubElement(book, "stock").text = str(b.get("stock", ""))
        ET.SubElement(book, "format").text = b.get("formato", "")

    xml_body = ET.tostring(catalog, encoding="UTF-8", method="xml").decode("utf-8")
    head = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xsl = '<?xml-stylesheet type="text/xsl" href="/libros.xsl"?>\n'
    return Response(head + xsl + xml_body, mimetype="application/xml")

def xml_message(msg: str, code: int = 200) -> Response:
    root = ET.Element("response")
    ET.SubElement(root, "message").text = msg
    ET.SubElement(root, "status").text = str(code)
    xml = ET.tostring(root, encoding="UTF-8", xml_declaration=True).decode("utf-8")
    return Response(xml, mimetype="application/xml", status=code)

# -----------------------------------------------------------------------------
# Repos CQRS
# -----------------------------------------------------------------------------
class QueryRepository:
    def __init__(self, cfg):
        self.cfg = cfg

    def _fetchall(self, sql: str, params: tuple = ()) -> List[Dict]:
        conn = get_conn(self.cfg)
        if not conn:
            raise RuntimeError("Error de conexión a la DB de lectura")
        try:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            cur.execute(sql, params)
            rows = cur.fetchall()
            return rows
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass

    def all_books(self) -> List[Dict]:
        sql = """
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
        return self._fetchall(sql)

    def by_isbn(self, isbn: str) -> Optional[Dict]:
        sql = """
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
        rows = self._fetchall(sql, (isbn,))
        return rows[0] if rows else None

    def by_format(self, fmt: str) -> List[Dict]:
        sql = """
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
        return self._fetchall(sql, (fmt,))

    def by_author(self, author_name: str) -> List[Dict]:
        sql = """
        SELECT 
            l.isbn, l.titulo, l.anio_publicacion, l.precio, l.stock,
            (SELECT GROUP_CONCAT(a_inner.nombre SEPARATOR ', ')
             FROM autores a_inner 
             JOIN libro_autor la_inner ON a_inner.id_autor = la_inner.id_autor
             WHERE la_inner.id_libro = l.id_libro) AS autor,
            g.nombre AS genero,
            f.nombre AS formato
        FROM libros l
        JOIN libro_autor la ON l.id_libro = la.id_libro
        LEFT JOIN genero g ON l.id_genero = g.id_genero
        LEFT JOIN formato f ON l.id_formato = f.id_formato
        WHERE la.id_autor = (SELECT id_autor FROM autores WHERE nombre = %s)
        GROUP BY l.id_libro
        ORDER BY l.titulo;
        """
        return self._fetchall(sql, (author_name,))

class CommandRepository:
    """
    Repositorio de escritura. Implementa outbox e idempotencia.
    Requiere existencia de tablas:
      CREATE TABLE IF NOT EXISTS idempotency_keys (
        id VARCHAR(64) PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        response_xml MEDIUMTEXT NULL
      );

      CREATE TABLE IF NOT EXISTS outbox_messages (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        event_type VARCHAR(128) NOT NULL,
        aggregate_id VARCHAR(128) NOT NULL,
        payload JSON NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        dispatched TINYINT(1) NOT NULL DEFAULT 0
      );
    """
    def __init__(self, cfg):
        self.cfg = cfg

    def _begin(self):
        conn = get_conn(self.cfg)
        if not conn:
            raise RuntimeError("Error de conexión a la DB de escritura")
        conn.autocommit(False)
        return conn

    # ----- Idempotencia -----
    def _get_or_store_idempotency(self, conn, key: Optional[str], response_xml: Optional[str] = None):
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        try:
            if response_xml is None:
                cur.execute("SELECT response_xml FROM idempotency_keys WHERE id=%s", (key,))
                row = cur.fetchone()
                return row["response_xml"] if row else None
            else:
                cur.execute(
                    "INSERT INTO idempotency_keys (id, response_xml) VALUES (%s, %s)",
                    (key, response_xml),
                )
        finally:
            cur.close()

    def _emit_outbox(self, conn, event_type: str, aggregate_id: str, payload: dict):
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO outbox_messages (event_type, aggregate_id, payload) VALUES (%s, %s, %s)",
                (event_type, aggregate_id, json.dumps(payload, ensure_ascii=False)),
            )
        finally:
            cur.close()

    # ----- Comandos -----
    def insert_book(self, data: dict, idem_key: Optional[str]) -> Response:
        required = ["isbn", "titulo", "anio_publicacion", "precio", "stock", "genero", "formato", "autor"]
        if not all(k in data for k in required):
            return xml_message(f"Faltan campos requeridos. Se necesitan: {', '.join(required)}", 400)

        conn = self._begin()
        try:
            if idem_key:
                prev = self._get_or_store_idempotency(conn, idem_key)
                if prev:
                    conn.rollback()
                    return Response(prev, mimetype="application/xml", status=201)

            cur = conn.cursor()
            cur.execute("SELECT id_genero FROM genero WHERE nombre=%s", (data["genero"],))
            g = cur.fetchone()
            cur.execute("SELECT id_formato FROM formato WHERE nombre=%s", (data["formato"],))
            f = cur.fetchone()
            if not g or not f:
                conn.rollback()
                return xml_message("Género o formato no válido.", 400)

            sql = """
            INSERT INTO libros (isbn, titulo, anio_publicacion, precio, stock, id_genero, id_formato)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """
            cur.execute(sql, (data["isbn"], data["titulo"], data["anio_publicacion"], data["precio"], data["stock"], g[0], f[0]))
            id_libro = cur.lastrowid

            autores = [a.strip() for a in str(data["autor"]).split(",") if a.strip()]
            for a in autores:
                cur.execute("SELECT id_autor FROM autores WHERE nombre=%s", (a,))
                row = cur.fetchone()
                if not row:
                    conn.rollback()
                    return xml_message(f"El autor '{a}' no existe en la base de datos.", 400)
                cur.execute("INSERT INTO libro_autor (id_libro, id_autor) VALUES (%s,%s)", (id_libro, row[0]))

            self._emit_outbox(
                conn,
                event_type="BookCreated",
                aggregate_id=str(data["isbn"]),
                payload={"isbn": data["isbn"], "titulo": data["titulo"], "ts": datetime.utcnow().isoformat() + "Z"},
            )

            conn.commit()
            resp = xml_message(f"Libro con ISBN {data['isbn']} insertado correctamente.", 201)

            if idem_key:
                conn2 = self._begin()
                try:
                    self._get_or_store_idempotency(conn2, idem_key, resp.get_data(as_text=True))
                    conn2.commit()
                finally:
                    conn2.close()

            return resp
        except MySQLdb.IntegrityError as e:
            conn.rollback()
            return xml_message(f"Error de integridad: probablemente ISBN duplicado. ({e})", 409)
        except MySQLdb.Error as e:
            conn.rollback()
            return xml_message(f"Error en base de datos: {e}", 500)
        finally:
            conn.close()

    def update_book(self, isbn: str, data: dict, idem_key: Optional[str]) -> Response:
        if not data:
            return xml_message("No se recibieron datos JSON para actualizar.", 400)

        conn = self._begin()
        try:
            if idem_key:
                prev = self._get_or_store_idempotency(conn, idem_key)
                if prev:
                    conn.rollback()
                    return Response(prev, mimetype="application/xml", status=200)

            cur = conn.cursor()
            cur.execute("SELECT id_libro FROM libros WHERE isbn=%s", (isbn,))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return xml_message(f"Libro con ISBN {isbn} no encontrado.", 404)
            id_libro = row[0]

            fields, vals = [], []
            mapping = {"titulo": "titulo", "anio_publicacion": "anio_publicacion", "precio": "precio", "stock": "stock"}
            for k, v in data.items():
                if k in mapping:
                    fields.append(f"{mapping[k]}=%s")
                    vals.append(v)

            if fields:
                sql = f"UPDATE libros SET {', '.join(fields)} WHERE id_libro=%s"
                vals.append(id_libro)
                cur.execute(sql, tuple(vals))

            self._emit_outbox(
                conn,
                event_type="BookUpdated",
                aggregate_id=str(isbn),
                payload={"isbn": isbn, "changed_fields": list(data.keys()), "ts": datetime.utcnow().isoformat() + "Z"},
            )

            conn.commit()
            resp = xml_message(f"Libro con ISBN {isbn} actualizado correctamente.", 200)

            if idem_key:
                conn2 = self._begin()
                try:
                    self._get_or_store_idempotency(conn2, idem_key, resp.get_data(as_text=True))
                    conn2.commit()
                finally:
                    conn2.close()

            return resp
        except MySQLdb.Error as e:
            conn.rollback()
            return xml_message(f"Error al actualizar: {e}", 500)
        finally:
            conn.close()

    def delete_books(self, isbns: List[str], idem_key: Optional[str]) -> Response:
        if not isbns:
            return xml_message("La lista de ISBNs está vacía.", 400)

        conn = self._begin()
        try:
            if idem_key:
                prev = self._get_or_store_idempotency(conn, idem_key)
                if prev:
                    conn.rollback()
                    return Response(prev, mimetype="application/xml", status=200)

            cur = conn.cursor()
            fmt = ",".join(["%s"] * len(isbns))
            cur.execute(f"SELECT id_libro, isbn FROM libros WHERE isbn IN ({fmt})", tuple(isbns))
            rows = cur.fetchall()
            if not rows:
                conn.rollback()
                return xml_message("Ninguno de los ISBNs proporcionados fue encontrado.", 404)

            ids = [r[0] for r in rows]
            cur.execute(f"DELETE FROM libro_autor WHERE id_libro IN ({','.join(['%s']*len(ids))})", tuple(ids))
            cur.execute(f"DELETE FROM libros WHERE id_libro IN ({','.join(['%s']*len(ids))})", tuple(ids))

            self._emit_outbox(
                conn,
                event_type="BooksDeleted",
                aggregate_id=";".join(isbns),
                payload={"isbns": isbns, "ts": datetime.utcnow().isoformat() + "Z"},
            )

            deleted = cur.rowcount
            conn.commit()
            resp = xml_message(f"Se borraron {deleted} libro(s) correctamente.", 200)

            if idem_key:
                conn2 = self._begin()
                try:
                    self._get_or_store_idempotency(conn2, idem_key, resp.get_data(as_text=True))
                    conn2.commit()
                finally:
                    conn2.close()

            return resp
        except MySQLdb.Error as e:
            conn.rollback()
            return xml_message(f"Error al borrar: {e}", 500)
        finally:
            conn.close()

# -----------------------------------------------------------------------------
# Blueprints CQRS
# -----------------------------------------------------------------------------
query_bp = Blueprint("query", __name__, url_prefix="/query")
command_bp = Blueprint("command", __name__, url_prefix="/command")

Q = QueryRepository(DB_READ)
C = CommandRepository(DB_WRITE)

# --------- Query endpoints ----------
@query_bp.route("/books", methods=["GET"])
def q_all_books():
    try:
        books = Q.all_books()
        return xml_catalog_from_books(books)
    except Exception as e:
        return xml_message(f"Error en query: {e}", 500)

@query_bp.route("/books/isbn/<string:isbn>", methods=["GET"])
def q_by_isbn(isbn):
    try:
        book = Q.by_isbn(isbn)
        if book:
            return xml_catalog_from_books([book])
        return xml_message(f"Libro con ISBN {isbn} no encontrado.", 404)
    except Exception as e:
        return xml_message(f"Error en query: {e}", 500)

@query_bp.route("/books/format/<string:format_name>", methods=["GET"])
def q_by_format(format_name):
    try:
        books = Q.by_format(format_name)
        if books:
            return xml_catalog_from_books(books)
        return xml_message(f"No se encontraron libros con el formato '{format_name}'.", 404)
    except Exception as e:
        return xml_message(f"Error en query: {e}", 500)

@query_bp.route("/books/author/<string:author_name>", methods=["GET"])
def q_by_author(author_name):
    try:
        books = Q.by_author(author_name)
        if books:
            return xml_catalog_from_books(books)
        return xml_message(f"No se encontraron libros para el autor '{author_name}'.", 404)
    except Exception as e:
        return xml_message(f"Error en query: {e}", 500)

# --------- Command endpoints ----------
@command_bp.route("/books", methods=["POST"])
def c_insert_book():
    data = request.get_json(silent=True) or {}
    idem_key = request.headers.get("Idempotency-Key") or request.args.get("idem_key") or str(uuid.uuid4())
    return C.insert_book(data, idem_key)

@command_bp.route("/books/<string:isbn>", methods=["PUT"])
def c_update_book(isbn):
    data = request.get_json(silent=True) or {}
    idem_key = request.headers.get("Idempotency-Key") or request.args.get("idem_key") or str(uuid.uuid4())
    return C.update_book(isbn, data, idem_key)

@command_bp.route("/books/delete", methods=["DELETE"])
def c_delete_books():
    data = request.get_json(silent=True) or {}
    isbns = data.get("isbns", [])
    idem_key = request.headers.get("Idempotency-Key") or request.args.get("idem_key") or str(uuid.uuid4())
    return C.delete_books(isbns, idem_key)

# -----------------------------------------------------------------------------
# XSLs
# -----------------------------------------------------------------------------
@app.route("/libros.xsl", methods=["GET"])
def get_xsl_stylesheet():
    # Versión "página completa" (mantener por compatibilidad)
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
    return Response(xsl_content, mimetype="application/xml")

@app.route("/libros_fragment.xsl", methods=["GET"])
def get_xsl_fragment():
    # Versión "fragmento" (no contamina estilos globales)
    xsl_content = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" omit-xml-declaration="yes"/>
<xsl:template match="/">
  <div class="catalogo-embed">
    <style>
      .catalogo-embed { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
      .catalogo-embed .tbl { width: 100%; border-collapse: collapse; box-shadow: 0 4px 8px rgba(0,0,0,.08); background: white; border-radius: 8px; overflow: hidden; }
      .catalogo-embed .tbl th, .catalogo-embed .tbl td { border-bottom: 1px solid #e0e0e0; padding: 12px 14px; text-align: left; }
      .catalogo-embed .tbl th { background: #4A90E2; color: white; font-weight: 600; }
      .catalogo-embed .tbl tr:nth-child(even) { background: #f7faff; }
      .catalogo-embed .tbl tr:hover { background: #eef5ff; }
      .catalogo-embed .tbl td:first-child { font-family: "Courier New", Courier, monospace; }
      @media (prefers-color-scheme: dark) {
        .catalogo-embed .tbl { background: #111; color: #e7e7e7; }
        .catalogo-embed .tbl th { background: #245e9d; }
        .catalogo-embed .tbl tr:nth-child(even) { background: #1a1a1a; }
        .catalogo-embed .tbl tr:hover { background: #222; }
        .catalogo-embed .tbl td { border-color: #333; }
      }
    </style>
    <table class="tbl">
      <thead>
        <tr>
          <th>ISBN</th><th>Título</th><th>Autor(es)</th><th>Año</th>
          <th>Género</th><th>Precio</th><th>Stock</th><th>Formato</th>
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
  </div>
</xsl:template>
</xsl:stylesheet>
"""
    return Response(xsl_content, mimetype="application/xml")

# -----------------------------------------------------------------------------
# Registro de blueprints y arranque
# -----------------------------------------------------------------------------
app.register_blueprint(query_bp)
app.register_blueprint(command_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

