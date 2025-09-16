<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>
<xsl:key name="dept" match="employee" use="concat(department/@name,'|',department/@location)"/>

<xsl:template match="/company">
  <html><head><title>Empleados por departamento</title></head><body>
    <h1>Empleados por departamento</h1>
    <xsl:for-each select="employee[generate-id() = generate-id(key('dept', concat(department/@name,'|',department/@location))[1])]">
      <xsl:sort select="department/@name"/>
      <h2><xsl:value-of select="department/@name"/> — <xsl:value-of select="department/@location"/></h2>
      <table border="1" cellspacing="0" cellpadding="4">
        <tr><th>Nombre</th><th>Posición</th><th>Salario (MXN)</th></tr>
        <xsl:for-each select="key('dept', concat(department/@name,'|',department/@location))">
          <tr>
            <td><xsl:value-of select="concat(first_name,' ',last_name)"/></td>
            <td><xsl:value-of select="position"/></td>
            <td><xsl:value-of select="salary"/></td>
          </tr>
        </xsl:for-each>
      </table>
    </xsl:for-each>
  </body></html>
</xsl:template>
</xsl:stylesheet>
