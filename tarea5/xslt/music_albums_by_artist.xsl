<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>

<xsl:template match="/catalog">
  <html><head><title>Álbumes por artista</title></head><body>
    <h1>Álbumes por artista</h1>
    <xsl:for-each select="artist">
      <h2>
        <xsl:value-of select="@name"/>
        <span> (</span><xsl:value-of select="@country"/><span>)</span>
      </h2>
      <ul>
        <xsl:for-each select="album">
          <li>
            <b><xsl:value-of select="@title"/></b>
            — <xsl:value-of select="@year"/> — <i><xsl:value-of select="genre"/></i>
          </li>
        </xsl:for-each>
      </ul>
    </xsl:for-each>
  </body></html>
</xsl:template>
</xsl:stylesheet>
