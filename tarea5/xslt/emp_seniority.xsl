<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>

<xsl:template match="/company">
  <html><head><title>Antigüedad de empleados</title></head><body>
    <h1>Empleados por antigüedad</h1>
    <ol>
      <xsl:for-each select="employee">
        <xsl:sort select="@hire_date"/>
        <li>
          <b><xsl:value-of select="concat(first_name,' ',last_name)"/></b> —
          <xsl:value-of select="position"/> —
          <i><xsl:value-of select="@hire_date"/></i>
        </li>
      </xsl:for-each>
    </ol>
  </body></html>
</xsl:template>
</xsl:stylesheet>