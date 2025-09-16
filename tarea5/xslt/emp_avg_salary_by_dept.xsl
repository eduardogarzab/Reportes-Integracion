<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>
<xsl:key name="dept" match="employee" use="concat(department/@name,'|',department/@location)"/>

<xsl:template match="/company">
  <html><head><title>Salario promedio por departamento</title></head><body>
    <h1>Salario promedio por departamento</h1>
    <ul>
      <xsl:for-each select="employee[generate-id() = generate-id(key('dept', concat(department/@name,'|',department/@location))[1])]">
        <xsl:sort select="department/@name"/>
        <xsl:variable name="groupKey" select="concat(department/@name,'|',department/@location)"/>
        <xsl:variable name="emps" select="key('dept', $groupKey)"/>
        <xsl:variable name="sum" select="sum($emps/salary)"/>
        <xsl:variable name="cnt" select="count($emps)"/>
        <li>
          <b><xsl:value-of select="department/@name"/></b> — <xsl:value-of select="department/@location"/>:
          Promedio = <xsl:value-of select="format-number($sum div $cnt,'#,##0.00')"/>
        </li>
      </xsl:for-each>
    </ul>
  </body></html>
</xsl:template>
</xsl:stylesheet>
