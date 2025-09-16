<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>
<xsl:key name="dept" match="employee" use="concat(department/@name,'|',department/@location)"/>

<xsl:template match="/company">
  <html><head><title>Estructura de la empresa</title></head><body>
    <h1>Departamentos y empleados</h1>
    <xsl:for-each select="employee[generate-id() = generate-id(key('dept', concat(department/@name,'|',department/@location))[1])]">
      <xsl:sort select="department/@name"/>
      <h2><xsl:value-of select="department/@name"/> — <xsl:value-of select="department/@location"/></h2>
      <ul>
        <xsl:for-each select="key('dept', concat(department/@name,'|',department/@location))">
          <li>
            <b><xsl:value-of select="concat(first_name,' ',last_name)"/></b>
            — <xsl:value-of select="position"/>
            — <xsl:choose>
                <xsl:when test="@full_time='true'">Tiempo completo</xsl:when>
                <xsl:otherwise>Medio tiempo</xsl:otherwise>
              </xsl:choose>
          </li>
        </xsl:for-each>
      </ul>
    </xsl:for-each>
  </body></html>
</xsl:template>
</xsl:stylesheet>
