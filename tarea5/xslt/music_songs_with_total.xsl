<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>

<!-- Suma segundos de una lista de canciones -->
<xsl:template name="sum-seconds">
  <xsl:param name="nodes"/>
  <xsl:param name="acc" select="0"/>
  <xsl:choose>
    <xsl:when test="count($nodes)=0">
      <xsl:value-of select="$acc"/>
    </xsl:when>
    <xsl:otherwise>
      <xsl:variable name="d" select="$nodes[1]/@duration"/>
      <xsl:variable name="sec" select="number(substring-before($d,':'))*60 + number(substring-after($d,':'))"/>
      <xsl:call-template name="sum-seconds">
        <xsl:param name="nodes" select="$nodes[position()>1]"/>
        <xsl:param name="acc" select="$acc + $sec"/>
      </xsl:call-template>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match="/catalog">
  <html><head><title>Canciones y total</title></head><body>
    <h1>Canciones por álbum y duración total</h1>
    <xsl:for-each select="artist">
      <h2><xsl:value-of select="@name"/> (<xsl:value-of select="@country"/>)</h2>
      <xsl:for-each select="album">
        <h3><xsl:value-of select="@title"/> — <xsl:value-of select="@year"/> (<xsl:value-of select="genre"/>)</h3>
        <table border="1" cellspacing="0" cellpadding="4">
          <tr><th>#</th><th>Canción</th><th>Duración</th><th>Single</th></tr>
          <xsl:for-each select="song">
            <tr>
              <td><xsl:value-of select="position()"/></td>
              <td><xsl:value-of select="@title"/></td>
              <td><xsl:value-of select="@duration"/></td>
              <td><xsl:value-of select="@single"/></td>
            </tr>
          </xsl:for-each>
          <tr>
            <td colspan="4" align="right">
              <b>Total álbum:
                <xsl:variable name="totalSec">
                  <xsl:call-template name="sum-seconds">
                    <xsl:with-param name="nodes" select="song"/>
                  </xsl:call-template>
                </xsl:variable>
                <xsl:variable name="min" select="floor(number($totalSec) div 60)"/>
                <xsl:variable name="sec" select="number($totalSec) mod 60"/>
                <xsl:value-of select="$min"/>:<xsl:value-of select="format-number($sec,'00')"/>
              </b>
            </td>
          </tr>
        </table>
      </xsl:for-each>
    </xsl:for-each>
  </body></html>
</xsl:template>
</xsl:stylesheet>
