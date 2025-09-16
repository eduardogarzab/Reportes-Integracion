<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>

<xsl:template match="/company">
  <html><head><title>Empleados tiempo completo</title></head><body>
    <h1>Empleados a tiempo completo</h1>
    <table border="1" cellspacing="0" cellpadding="4">
      <tr><th>Nombre</th><th>Posición</th><th>Departamento</th><th>Salario</th></tr>
      <xsl:for-each select="employee[@full_time='true']">
        <tr>
          <td><xsl:value-of select="concat(first_name,' ',last_name)"/></td>
          <td><xsl:value-of select="position"/></td>
          <td><xsl:value-of select="concat(department/@name,' (',department/@location,')')"/></td>
          <td><xsl:value-of select="salary"/></td>
        </tr>
      </xsl:for-each>
    </table>
  </body></html>
</xsl:template>
</xsl:stylesheet>
