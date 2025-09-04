<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" omit-xml-declaration="yes" />

  <xsl:template match="/">
    <div>
      <div class="toolbar">
        <span class="pill">
          <xsl:text>Total de libros: </xsl:text>
          <xsl:value-of select="count(/catalog/book)"/>
        </span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Título</th>
            <th>Autor</th>
            <th>Año</th>
            <th>Género</th>
            <th>Precio</th>
            <th>Stock</th>
            <th>Formato</th>
            <th>ISBN</th>
          </tr>
        </thead>
        <tbody>
          <xsl:for-each select="/catalog/book">
            <tr>
              <td><xsl:value-of select="title"/></td>
              <td><xsl:value-of select="author"/></td>
              <td><xsl:value-of select="year"/></td>
              <td><xsl:value-of select="genre"/></td>
              <td>
                <xsl:text>$</xsl:text>
                <xsl:value-of select="format-number(number(price), '0.00')"/>
              </td>
              <td><xsl:value-of select="stock"/></td>
              <td><xsl:value-of select="format"/></td>
              <td class="isbn"><xsl:value-of select="@isbn"/></td>
            </tr>
          </xsl:for-each>
        </tbody>
      </table>
    </div>
  </xsl:template>
</xsl:stylesheet>

