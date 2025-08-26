<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

  <xsl:output method="html" indent="yes"/>

  <xsl:template match="/">
    <html>
      <head>
        <meta charset="UTF-8"/>
        <title>Catálogo de Libros</title>
        <link rel="stylesheet" type="text/css" href="styles.css"/>
        <script>
          //<![CDATA[
          function filterBooks() {
            let author = document.getElementById("author").value.toLowerCase();
            let year = document.getElementById("year").value.toLowerCase();
            let genre = document.getElementById("genre").value.toLowerCase();
            let format = document.getElementById("format").value.toLowerCase();
            let books = document.getElementsByClassName("book");

            for (let i = 0; i < books.length; i++) {
              let a = books[i].getAttribute("data-author").toLowerCase();
              let y = books[i].getAttribute("data-year").toLowerCase();
              let g = books[i].getAttribute("data-genre").toLowerCase();
              let f = books[i].getAttribute("data-format").toLowerCase();

              if ((author === "" || a.includes(author)) &&
                  (year === "" || y.includes(year)) &&
                  (genre === "" || g.includes(genre)) &&
                  (format === "" || f.includes(format))) {
                
                // --- CORRECCIÓN CLAVE AQUÍ ---
                // En lugar de "block", usamos "" para que el CSS (display: grid) vuelva a tomar el control.
                books[i].style.display = ""; 

              } else {
                books[i].style.display = "none";
              }
            }
          }
          //]]>
        </script>
      </head>
      <body>
        <h1>Catálogo de Libros</h1>

        <div class="search-box">
          <input type="text" id="author" placeholder="Buscar por autor" onkeyup="filterBooks()"/>
          <input type="text" id="year" placeholder="Buscar por año" onkeyup="filterBooks()"/>
          <input type="text" id="genre" placeholder="Buscar por género" onkeyup="filterBooks()"/>
          <input type="text" id="format" placeholder="Buscar por formato" onkeyup="filterBooks()"/>
        </div>

        <div class="catalog">
          <xsl:for-each select="catalog/book">
            <div class="book">
              <xsl:attribute name="data-author"><xsl:value-of select="author"/></xsl:attribute>
              <xsl:attribute name="data-year"><xsl:value-of select="year"/></xsl:attribute>
              <xsl:attribute name="data-genre"><xsl:value-of select="genre"/></xsl:attribute>
              <xsl:attribute name="data-format"><xsl:value-of select="format"/></xsl:attribute>

              <h2><xsl:value-of select="title"/></h2>
              <div class="author"><xsl:value-of select="author"/></div>
              <div class="meta">Año: <xsl:value-of select="year"/> | Género: <xsl:value-of select="genre"/></div>
              <div class="price">Precio: $<xsl:value-of select="price"/></div>
              <div class="stock">Stock: <xsl:value-of select="stock"/></div>
              <div class="format">Formato: <xsl:value-of select="format"/></div>
            </div>
          </xsl:for-each>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>