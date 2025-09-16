<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>

<xsl:template match="/catalog">
  <html><head><title>Sencillos</title></head><body>
    <h1>Sencillos por álbum</h1>
    <xsl:for-each select="artist">
      <xsl:variable name="artistName" select="@name"/>
      <xsl:if test="album/song[@single='true']">
        <h2><xsl:value-of select="$artistName"/> (<xsl:value-of select="@country"/>)</h2>
        <xsl:for-each select="album[song/@single='true']">
          <h3><xsl:value-of select="@title"/> — <xsl:value-of select="@year"/></h3>
          <ul>
            <xsl:for-each select="song[@single='true']">
              <li><xsl:value-of select="@title"/> (<xsl:value-of select="@duration"/>)</li>
            </xsl:for-each>
          </ul>
        </xsl:for-each>
      </xsl:if>
    </xsl:for-each>
  </body></html>
</xsl:template>
</xsl:stylesheet>
