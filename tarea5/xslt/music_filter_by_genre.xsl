<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>
<xsl:param name="genre" select="'Rock'"/>

<xsl:template match="/catalog">
  <html><head><title>Álbumes por género</title></head><body>
    <h1>Álbumes de género: <xsl:value-of select="$genre"/></h1>
    <ul>
      <xsl:for-each select="artist/album[genre=$genre]">
        <li>
          <b><xsl:value-of select="@title"/></b> — <xsl:value-of select="@year"/>
          <span> (</span><xsl:value-of select="../@name"/><span>)</span>
        </li>
      </xsl:for-each>
    </ul>
  </body></html>
</xsl:template>
</xsl:stylesheet>
