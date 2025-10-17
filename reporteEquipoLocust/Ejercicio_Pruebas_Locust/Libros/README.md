
# Proyecto de Pruebas de Carga para Microservicios

Este proyecto contiene una suite de pruebas de rendimiento desarrollada con **Locust** para evaluar la robustez y escalabilidad de una arquitectura de microservicios. Las pruebas se diseñaron para identificar cuellos de botella y validar una arquitectura de producción robusta que consiste en:

  * **Microservicio de Autenticación**: Gestiona el registro y login de usuarios.
  * **Microservicio de Libros**: Expone un catálogo de libros a través de una API.
  * **Base de Datos**: MariaDB.
  * **Cache**: Redis para la gestión de tokens.
  * **Servidor de Producción**: Gunicorn.

-----

## 🧠 Lecciones Aprendidas: Por Qué Falló la Configuración Inicial

Las pruebas iniciales revelaron problemas críticos de rendimiento, demostrando por qué una configuración de desarrollo es inadecuada para cargas de producción.

### El Problema con el Servidor de Desarrollo de Flask

El servidor integrado (`app.run()`) es de un solo hilo y no está diseñado para peticiones concurrentes. Cuando Locust envió cientos de "usuarios" simultáneamente, el servidor se convirtió en un cuello de botella inmediato, incapaz de manejar el tráfico. Esto resultó en una cascada de errores de `ConnectionResetError` y `Timeout`.

**Solución:** Reemplazamos el servidor de desarrollo por **Gunicorn**, un servidor WSGI de grado de producción. Al configurar Gunicorn con múltiples "workers" (`--workers 4`), habilitamos un verdadero procesamiento en paralelo, permitiendo que la aplicación maneje múltiples peticiones al mismo tiempo de forma eficiente.

### El Problema con la Gestión de Conexiones a la Base de Datos

Nuestro enfoque inicial para las conexiones a la base de datos causó las fallas más significativas:

1.  **Una Conexión por Petición**: Este enfoque sobrecargó rápidamente al servidor de MariaDB, que tiene un límite de conexiones simultáneas por defecto. Esto condujo al error crítico de **`Too many connections`** (Demasiadas conexiones), provocando que ambos microservicios fallaran.
2.  **Agotamiento del Pool de Conexiones**: Implementar un pool de conexiones básico ayudó, pero se agotaba rápidamente (`pool exhausted`) porque las peticiones llegaban más rápido de lo que las conexiones se liberaban. Además, las conexiones inactivas en el pool eran cerradas por la base de datos, lo que llevaba a errores intermitentes `500 Internal Server Error` cuando la aplicación intentaba usar una conexión "zombie" o muerta.

**Solución:** La solución final y robusta fue implementar un **pool de conexiones "auto-reparable"** en ambos microservicios usando `mysql-connector-python`.

  * **Pool de Conexiones (`pooling`):** Limita el número total de conexiones a la base de datos, previniendo la sobrecarga. En lugar de crear nuevas conexiones (un proceso lento), las peticiones "toman prestada" una existente del pool.
  * **`pool_reset_session=True`**: Este parámetro crucial asegura que cada conexión tomada del pool sea "despertada" o verificada antes de ser usada. Si una conexión se ha vuelto obsoleta, el pool la reemplaza automáticamente, previniendo errores intermitentes y haciendo que la aplicación se repare a sí misma.

Esta arquitectura final (**Gunicorn + Pools de Conexiones**) demostró ser estable, eficiente y capaz de manejar una carga concurrente significativa.

-----

## 🚀 Despliegue y Configuración

Sigue estos pasos para configurar el entorno y desplegar los microservicios.

### 1\. Preparar la Base de Datos

Ejecuta el script `init.sql` en tu instancia de MariaDB para crear la base de datos `Libros`, las tablas necesarias y poblar los datos iniciales.

```bash
mysql -u tu_usuario -p < init.sql
```

### 2\. Instalar Dependencias de Python

Este proyecto incluye un archivo `requirements.txt` con todas las librerías necesarias. Instálalas con un solo comando:

```bash
pip install -r requirements.txt
```

### 3\. Generar y Registrar Usuarios de Prueba

Para simular un entorno realista, necesitamos crear usuarios de prueba.

a. **Generar el archivo `users.csv`**:
Este script creará 300 usuarios con credenciales aleatorias.

```bash
python create_users_csv.py
```

b. **Registrar los usuarios en la Base de Datos**:
Este script leerá `users.csv` y registrará cada usuario llamando al endpoint `/register` del microservicio de autenticación.

```bash
python register_users.py
```

### 4\. Levantar los Microservicios con Gunicorn

El servidor de desarrollo de Flask no es adecuado para pruebas de carga. Usaremos **Gunicorn**. Deberás abrir **dos terminales separadas** en tu servidor (GCP).

a. **Terminal 1: Iniciar el Microservicio de Autenticación**
Navega a la carpeta del proyecto y ejecuta:

```bash
# Reemplaza 'app_jwt_redis.py' con el nombre de tu archivo de autenticación
gunicorn --bind 0.0.0.0:5000 --workers 2 app_jwt_redis:app
```

b. **Terminal 2: Iniciar el Microservicio de Libros**
Navega a la carpeta del proyecto y ejecuta:

```bash
# Reemplaza 'microservicioCQRSRedis.py' con el nombre de tu archivo de libros
gunicorn --bind 0.0.0.0:5001 --workers 4 microservicioCQRSRedis:app
```

> **Importante:** ¡No olvides abrir los puertos `5000` y `5001` en el **firewall** de tu proveedor de nube (GCP)\!

-----

## ⚡ Ejecución de las Pruebas de Carga

Todas las pruebas se ejecutan desde tu máquina local, apuntando a la IP pública de tu servidor.

### Ejecutar la Suite Completa (Recomendado)

El script `run_all_tests.sh` se encarga de ejecutar todas las pruebas automatizadas en secuencia y guardar los resultados en una carpeta con fecha y hora.

1.  **Dar permisos de ejecución** (solo la primera vez):
    ```bash
    chmod +x run_all_tests.sh
    ```
2.  **Lanzar la suite de pruebas**:
    ```bash
    ./run_all_tests.sh
    ```

Al finalizar, encontrarás una nueva carpeta `test_results_...` con todos los reportes en formato `.html` y `.csv`.

### Descripción de las Pruebas Automatizadas

El script ejecuta los siguientes escenarios:

1.  **Smoke Test**: Carga mínima para verificar que el sistema está en línea y funcional.
2.  **Baseline Test**: Carga ligera y constante para establecer una línea base de rendimiento.
3.  **Read-Heavy Test**: Simula una carga donde predominan las operaciones de lectura (GET).
4.  **Write-Heavy Test**: Simula una carga donde predominan las operaciones de escritura (POST).
5.  **Stages Test**: Prueba con rampas de subida y bajada gradual de usuarios.
6.  **Soak Test**: Carga moderada y sostenida durante un largo periodo (30 min) para detectar fugas de memoria o degradación del rendimiento.
7.  **Spike Test**: Simula un pico de tráfico abrupto y masivo para probar la capacidad de recuperación del sistema.

### Ejecutar la Prueba de Break-Point (Manual)

Esta prueba es interactiva y sirve para encontrar el número máximo de usuarios que tu sistema puede soportar.

1.  En tu máquina local, ejecuta Locust en modo de interfaz web:
    ```bash
    locust -f locustfile.py
    ```
2.  Abre tu navegador y ve a `http://localhost:8089`.
3.  Inicia una prueba con una carga base (ej. 200 usuarios).
4.  Si el sistema es estable, **detén la prueba** e inicia una nueva con 100 usuarios más (300, 400, 500...).
5.  Repite el proceso hasta que la tasa de fallos (`Failures`) aumente significativamente o los tiempos de respuesta se disparen. ¡Ese es tu punto de quiebre\!
6.  Descarga el reporte final desde la pestaña "Download Data".

-----

## 📂 Estructura del Proyecto

```
.
├── app_jwt_redis.py            # Microservicio de Autenticación
├── create_users_csv.py         # Script para generar usuarios de prueba
├── init.sql                    # Script para inicializar la base de datos
├── locustfile.py               # Archivo principal de Locust con la mayoría de las pruebas
├── locustfile_spike.py         # Archivo específico para la prueba de Spike
├── locustfile_write_heavy.py   # Archivo específico para la prueba Write-Heavy
├── microservicioCQRSRedis.py   # Microservicio de Libros
├── register_users.py           # Script para registrar usuarios en la BD
├── run_all_tests.sh            # Script para ejecutar la suite completa de pruebas
├── requirements.txt            # Archivo con todas las dependencias de Python
└── users.csv                   # Archivo con los datos de los usuarios de prueba
```
