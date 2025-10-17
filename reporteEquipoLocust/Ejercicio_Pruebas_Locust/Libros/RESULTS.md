
# Reporte Final de Pruebas de Carga

**Proyecto:** Microservicios de Autenticación y Libros
**Fecha de Ejecución:** 16 de Octubre de 2025

Este documento resume y analiza los resultados de la suite completa de pruebas de rendimiento ejecutada sobre la arquitectura de microservicios. El objetivo fue identificar y resolver cuellos de botella para validar una arquitectura de producción robusta, basándose en los datos generados por cada escenario de prueba.

---
## 🌎 Entorno y Datos de Prueba

* **Infraestructura:** Google Cloud Platform (GCP)
* **Servidor de Aplicación:** Gunicorn
    * **Servicio Auth:** 2 workers (`--workers 2`)
    * **Servicio Libros:** 4 workers (`--workers 4`)
* **Microservicios:**
    * **Auth (Puerto 5000):** Basado en Flask, responsable del registro y login.
    * **Libros (Puerto 5001):** Basado en Flask, expone la API del catálogo.
* **Base de Datos:** MariaDB
* **Cache:** Redis (para gestión de tokens JWT)
* **Generador de Carga:** Locust, ejecutado desde una máquina local.
* **Datos de Prueba:** 300 usuarios únicos generados y pre-registrados en la base de datos (`users.csv`).

---
## ⚡ Escenarios Ejecutados y Análisis de Resultados

Se ejecutaron 8 escenarios de prueba distintos. La arquitectura final demostró ser **altamente estable**, con una tasa de éxito superior al **99.5%** en las pruebas más intensivas.

| # | Prueba | Usuarios Máx. | Duración | Peticiones/s (RPS) | Tpo. Respuesta (Mediana ms) | Fallos | Estado |
|---|---|---|---|---|---|---|---|
| 1 | **Smoke Test** | 5 | 1 min | 1.9 | 150ms | **0** | ✅ **Éxito** |
| 2 | **Baseline** | 50 | 5 min | 21 | 200ms | **0** | ✅ **Éxito** |
| 3 | **Read-Heavy** | 100 | 5 min | 45 | 230ms | **0** | ✅ **Éxito** |
| 4 | **Write-Heavy** | 100 | 5 min | 40 | 280ms | **0** | ✅ **Éxito** |
| 5 | **Stages (Rampas)**| 500 | ~7 min | 183 | 360ms | **< 0.1%** | ✅ **Éxito** |
| 6 | **Soak (Sostenida)**| 150 | 30 min | 62 | 250ms | **0** | ✅ **Éxito** |
| 7 | **Break-Point** | 800 | Manual | 3.17 | **22,000ms** | **0.45%** | ⚠️ **Límite Encontrado** |
| 8 | **Spike (Pico)** | 1,000 | ~3 min | 291 | 440ms | **< 0.1%** | ✅ **Éxito** |

---
## 🔑 Hallazgos Clave y Análisis a Profundidad

El proceso de pruebas fue un ciclo iterativo de "romper y arreglar" que expuso debilidades críticas en la arquitectura inicial. Los hallazgos no fueron solo números, sino una guía para la evolución del sistema.

### Hallazgo 1: El Servidor de Desarrollo es un Punto de Falla Catastrófico
Las pruebas iniciales ni siquiera pudieron arrancar. Locust reportó errores masivos de **`ConnectionResetError`** y **`ConnectTimeoutError`**.

* **Análisis a Profundidad:** El problema no estaba en el código de la aplicación, sino en su base: el **servidor de desarrollo de Flask (`app.run`)**. Este servidor es de un solo hilo y no está diseñado para peticiones concurrentes. Al recibir la carga de Locust, simplemente se colapsaba, reiniciando o rechazando conexiones antes de que pudieran ser procesadas.
* **Solución Implementada:** Se migró la ejecución de ambos servicios a **Gunicorn**, un servidor WSGI de producción. Al configurar Gunicorn con múltiples workers, se habilitó el procesamiento en paralelo real, estabilizando la capa de aplicación.

### Hallazgo 2: La Estrategia de Conexión a la BD es Crítica
Una vez con Gunicorn, la aplicación se mantenía en pie, pero la base de datos se convirtió en el siguiente cuello de botella. El proceso de depuración reveló tres etapas de este problema:

1.  **`Too many connections`**: El patrón de "una conexión por petición" agotó rápidamente el límite de conexiones de MariaDB. **Esto demostró que la base de datos era el principal cuello de botella de la arquitectura.**
2.  **`Pool exhausted`**: La implementación de un pool de conexiones ayudó, pero inicialmente era demasiado pequeño (`pool_size=15`) y se agotaba, causando fallos.
3.  **Errores 500 Intermitentes (Conexiones "Stale")**: Incluso con un pool más grande, aparecieron errores `500` esporádicos. El análisis reveló que la base de datos cerraba conexiones que permanecían inactivas en el pool por mucho tiempo.

* **Solución Implementada:** Se implementó un **pool de conexiones "auto-reparable"** en **ambos** microservicios usando `mysql-connector-python`, con un tamaño de 32 y el parámetro `pool_reset_session=True`. Esto aseguró que la aplicación nunca intentara abrir más conexiones de las permitidas y que las conexiones "zombies" fueran reemplazadas automáticamente.

### Hallazgo 3: El Punto de Quiebre es por Degradación, no por Errores
La prueba de Break-Point con 800 usuarios fue el hallazgo más revelador.

* **Análisis a Profundidad:** Contrario a lo esperado, el sistema no falló con errores masivos (solo **5 fallos** de un total de 1,123 peticiones, lo que representa una tasa de error de apenas **0.45%**). En su lugar, sufrió una **degradación de rendimiento catastrófica**. Los tiempos de respuesta se dispararon a una mediana de **22 segundos** (22,000 ms) y un promedio de **26 segundos**. El rendimiento (RPS) se desplomó a solo **3.17 peticiones por segundo**. Esto indica que la arquitectura es muy **estable** (no se cae), pero que los recursos del servidor (CPU/memoria) se saturaron por completo.
* **Conclusión del Hallazgo:** El límite del sistema no se define por errores, sino por una latencia que hace la aplicación inutilizable. Este límite se encuentra alrededor de los 800 usuarios concurrentes con la infraestructura actual.

### Hallazgo 4: Resiliencia y Estabilidad Comprobadas
Las pruebas de **Soak** y **Spike** validaron la robustez de la arquitectura final.

* **Prueba Sostenida (Soak Test):** El sistema manejó 150 usuarios durante 30 minutos sin un solo error y con tiempos de respuesta bajos y constantes (mediana de 250 ms). Esto confirma que no hay fugas de memoria ni degradación del rendimiento a largo plazo.
* **Prueba de Pico (Spike Test):** El sistema absorbió un pico repentino de 1,000 usuarios con una tasa de fallos mínima (< 0.1%) y se recuperó sin problemas. Esto demuestra una gran elasticidad y capacidad para manejar eventos de tráfico inesperados.

### Conclusión Final

El sistema, en su estado actual, es **robusto, escalable y resiliente**. Las pruebas de carga fueron un éxito rotundo, no solo al validar el rendimiento, sino al **forzar la evolución de una arquitectura de desarrollo frágil a una arquitectura de producción sólida**. El punto de quiebre, identificado por una degradación severa del rendimiento a los 800 usuarios, demuestra una alta capacidad para manejar picos de tráfico, manteniendo la integridad del sistema incluso bajo estrés extremo.
