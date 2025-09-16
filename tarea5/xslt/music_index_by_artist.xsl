<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>

<xsl:template match="/catalog">
  <html><head><title>Índice de artistas</title></head><body>
    <h1>Índice de artistas</h1>
    <xsl:for-each select="artist">
      <xsl:sort select="@name"/>
      <h2><xsl:value-of select="@name"/> (<xsl:value-of select="@country"/>)</h2>
      <ol>
        <xsl:for-each select="album">
          <xsl:sort select="@year" data-type="number"/>
          <li><xsl:value-of select="@year"/> — <b><xsl:value-of select="@title"/></b> (<xsl:value-of select="genre"/>)</li>
        </xsl:for-each>
      </ol>
    </xsl:for-each>
  </body></html>
</xsl:template>
</xsl:stylesheet>
