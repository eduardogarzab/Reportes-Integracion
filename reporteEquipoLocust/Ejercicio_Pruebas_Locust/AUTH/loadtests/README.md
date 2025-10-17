Pruebas de Carga para el Microservicio de Autenticación (auth)

Este proyecto contiene un conjunto de scripts y datos para realizar pruebas de carga y rendimiento sobre el microservicio de autenticación, utilizando la herramienta Locust.

Estructura del Directorio

El proyecto está organizado de la siguiente manera para mantener un orden claro entre los scripts, los datos de prueba y los resultados obtenidos.

auth/
└── loadtests/
    ├── data/
    │   └── users.csv         # Archivo con los datos de los usuarios de prueba.
    ├── results/
    │   ├── *.html            # Reportes HTML generados por Locust.
    │   └── *.csv             # Datos estadísticos en formato CSV.
    └── scripts/
        ├── auth.py           # (Opcional) Copia del microservicio bajo prueba.
        ├── generate_users.py # Script para crear el archivo users.csv.
        ├── register_users.py # Script para pre-registrar usuarios en la BD.
        └── locustfile.py     # Define el comportamiento de los usuarios virtuales.


Prerrequisitos

Antes de ejecutar las pruebas, asegúrate de tener Python instalado y de configurar el entorno con las siguientes dependencias:

Instalar librerías:

pip install -r requirements.txt


Microservicio Activo: El microservicio auth debe estar desplegado y accesible en la red. La URL base utilizada en estos tests es http://4.246.170.83:5001.

Proceso de Ejecución de Pruebas (Paso a Paso)

Sigue estos pasos en orden para replicar el ciclo completo de pruebas.

Paso 1: Generar Datos de Prueba

Este script crea el archivo users.csv con 300 usuarios únicos para simular un escenario de login realista.

# Estando en la carpeta /scripts
python generate_users.py


Este comando creará el archivo users.csv en el directorio ../data/.

Paso 2: Pre-registrar Usuarios en la Base de Datos

Para que las pruebas de login funcionen, los usuarios deben existir previamente en el sistema. Este script los registra automáticamente. Asegúrate de que el microservicio esté corriendo antes de ejecutarlo.

# Estando en la carpeta /scripts
python register_users.py


Paso 3: Ejecutar las Pruebas de Carga con Locust

Ejecuta los siguientes comandos desde el directorio raíz (auth/loadtests/). Los resultados se guardarán automáticamente en la carpeta results/.

Prueba Smoke (Verificación Rápida):

locust -f scripts/locustfile.py -u 5 -r 1 --run-time 30s --host [http://4.246.170.83:5001](http://4.246.170.83:5001) --headless --csv=results/smoke --html=results/smoke.html


Prueba Baseline (Carga Ligera):

locust -f scripts/locustfile.py -u 50 -r 5 --run-time 5m --host [http://4.246.170.83:5001](http://4.246.170.83:5001) --headless --csv=results/baseline --html=results/baseline.html


Prueba Soak (Carga Sostenida):

locust -f scripts/locustfile.py -u 200 -r 20 --run-time 30m --host [http://4.246.170.83:5001](http://4.246.170.83:5001) --headless --csv=results/soak --html=results/soak.html


Prueba Break-point (Punto de Quiebre):

locust -f scripts/locustfile.py -u 500 -r 50 --run-time 5m --host [http://4.246.170.83:5001](http://4.246.170.83:5001) --headless --csv=results/breakpoint_500 --html=results/breakpoint_500.html


Tras ejecutar las pruebas, revisa los reportes .html generados en la carpeta results/ para un análisis visual y detallado del rendimiento.