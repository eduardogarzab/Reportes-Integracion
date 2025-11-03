# Microservicio de Gestión de Imágenes (Azure + Flask)

Este microservicio permite subir, listar y visualizar imágenes almacenadas en un contenedor de Azure Blob Storage, con registro de metadatos en una base de datos MariaDB.

La API está protegida por un token Bearer y ofrece respuestas en XML (default) y JSON.

## 1. Configuración del Entorno

El servicio se configura completamente a través de variables de entorno.

### Variables de Entorno Requeridas

**Autenticación del Servicio (Token):**
* `API_TOKEN`: Tu token secreto para autenticar las solicitudes (ej: `super_secret_token_123`).

**Conexión a Azure (Service Principal):**
* `AZURE_CLIENT_ID`: El "Application (client) ID" de tu Service Principal.
* `AZURE_CLIENT_SECRET`: El "Client Secret" (Valor) que generaste.
* `AZURE_TENANT_ID`: El "Directory (tenant) ID" de tu organización.
* `AZURE_STORAGE_ACCOUNT_URL`: La URL de tu cuenta de almacenamiento (ej: `https://imagenesintegracion.blob.core.windows.net`).
* `CONTAINER_NAME`: El nombre de tu contenedor (ej: `microservicio-libros`).

**Conexión a MariaDB:**
* `DB_HOST`: La dirección del servidor de MariaDB (ej: `localhost` o una IP).
* `DB_USER`: El usuario de la base de datos.
* `DB_PASSWORD`: La contraseña del usuario de la base de datos.
* `DB_NAME`: El nombre de la base de datos donde está la tabla `images`.

## 2. Instalación

1.  Clona este repositorio (o copia los archivos).
2.  Crea un entorno virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```
3.  Instala las dependencias:
    ```bash
    pip install -r requirements.txt
    ```
4.  Ejecuta el script `images.sql` en tu base de datos MariaDB para crear la tabla.

## 3. Ejecución

1.  Exporta todas las variables de entorno listadas arriba.
    ```bash
    # Ejemplo en Linux/macOS
    export API_TOKEN="tu_token_secreto"
    export AZURE_CLIENT_ID="8df9c5f9-..."
    export AZURE_CLIENT_SECRET="Evv8Q~A..."
    export AZURE_TENANT_ID="ff31d2c0-..."
    export AZURE_STORAGE_ACCOUNT_URL="[https://imagenesintegracion.blob.core.windows.net](https://imagenesintegracion.blob.core.windows.net)"
    export CONTAINER_NAME="microservicio-libros"
    export DB_HOST="localhost"
    export DB_USER="root"
    export DB_PASSWORD="tu_db_pass"
    export DB_NAME="nombre_de_tu_db"
    ```
2.  Inicia la aplicación Flask:
    ```bash
    flask run
    # O para producción:
    # gunicorn --bind 0.0.0.0:5000 app:app
    ```

## 4. Ejemplos de Uso (curl)

Asegúrate de reemplazar `tu_token_secreto` con el valor de tu `API_TOKEN`.

### Subir una imagen

```bash
curl -X POST [http://127.0.0.1:5000/upload](http://127.0.0.1:5000/upload) \
     -H "Authorization: Bearer tu_token_secreto" \
     -F "image=@/ruta/a/tu/imagen.jpg"