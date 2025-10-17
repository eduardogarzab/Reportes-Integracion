# Pruebas de carga para HeartGuard Superadmin

## 1. Entorno y URLs base del CMS

-   URL base backend SSR: `http://127.0.0.1:8080`
-   Healthcheck: `http://127.0.0.1:8080/healthz`
-   Assets estáticos: `http://127.0.0.1:8080/ui-assets/...`

Para levantar el entorno local:

1. `cp .env.example .env`
2. `make up` (Postgres + Redis)
3. `make db-init && make db-seed`
4. `make dev` (lanza `go run ./cmd/superadmin-api`)

Verifica que el panel responde antes de lanzar Locust (ejecuta los comandos directamente en la VM Ubuntu donde corre el CMS):

```bash
curl -f http://127.0.0.1:8080/healthz
```

Si necesitas exponer el CMS desde otra máquina o red externa, ajusta `HTTP_ADDR` en `.env` y usa la URL correspondiente al ejecutar Locust.

## 2. Datos de prueba y cuentas de load testing

-   Archivo de credenciales: `loadtests/data/users.csv` (300 usuarios `loadtesterXXX@heartguard.dev` / `LoadTest#XXX`).
-   Requisitos del sistema: `sudo apt-get install python3.10-venv`
-   Crear y activar entorno virtual (recomendado):

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

-   Dependencias Python dentro del entorno:

    ```bash
    pip install --upgrade pip
    pip install -r loadtests/requirements.txt
    pip install zope.event zope.interface
    ```

-   Usa la misma variable `DATABASE_URL` que el backend.

Registro de cuentas en la base de datos:

```bash
export DATABASE_URL="postgres://heartguard_app:dev_change_me@127.0.0.1:5432/heartguard?sslmode=disable"
python3 loadtests/scripts/register_users.py
unset DATABASE_URL
```

El script inserta/actualiza usuarios en `heartguard.users` y garantiza el rol `superadmin` (`user_role`). Puedes relanzarlo sin efectos adversos; actualizará hashes y deja los usuarios en estado `active`.

## 3. Escenarios de Locust

Instala dependencias y ejecuta Locust en modo headless. Usa la ruta absoluta del host según tu despliegue.

### Referencia general

-   Archivo: `loadtests/locustfile.py`
-   CSV feeder: se carga automáticamente desde `loadtests/data/users.csv`
-   Reportes: guarda CSV/HTML en `loadtests/results/`
-   Variables útiles: `HEARTGUARD_BASE_URL`, `HEARTGUARD_SHAPE`

### Comandos sugeridos (Bash)

Cada comando genera `*.csv` y `*.html` en la carpeta de resultados. Ajusta `--run-time`, `--users (-u)` y `--spawn-rate (-r)` según tus objetivos.

#### 3.1 Baseline (carga ligera constante)

```bash
HEARTGUARD_SHAPE="baseline" locust -f loadtests/locustfile.py --class BaselineUser --headless -u 25 -r 5 --run-time 15m --csv loadtests/results/baseline --html loadtests/results/baseline.html --host http://127.0.0.1:8080
```

#### 3.2 Smoke (1-5 usuarios, disponibilidad rápida)

```bash
locust -f loadtests/locustfile.py --class SmokeUser --headless -u 5 -r 2 --run-time 5m --csv loadtests/results/smoke --html loadtests/results/smoke.html --host http://127.0.0.1:8080
```

#### 3.3 Read-heavy vs Write-heavy

_Read-heavy (mayoría GET):_

```bash
locust -f loadtests/locustfile.py --class ReadHeavyUser --headless -u 60 -r 6 --run-time 20m --csv loadtests/results/read-heavy --html loadtests/results/read-heavy.html --host http://127.0.0.1:8080
```

_Write-heavy (mayoría POST idempotentes):_

```bash
locust -f loadtests/locustfile.py --class WriteHeavyUser --headless -u 40 -r 4 --run-time 20m --csv loadtests/results/write-heavy --html loadtests/results/write-heavy.html --host http://127.0.0.1:8080
```

#### 3.4 Ramp-up / Ramp-down

```bash
HEARTGUARD_SHAPE="ramp" locust -f loadtests/locustfile.py --class BaselineUser --headless --csv loadtests/results/ramp --html loadtests/results/ramp.html --host http://127.0.0.1:8080
```

> La forma `ramp` escala 20→120 usuarios en etapas de 60 s y luego desciende.

#### 3.5 Spike test

```bash
HEARTGUARD_SHAPE="spike" locust -f loadtests/locustfile.py --class BaselineUser --headless --csv loadtests/results/spike --html loadtests/results/spike.html --host http://127.0.0.1:8080
```

> Incrementa súbitamente hasta ~150 usuarios y vuelve a la línea base.

#### 3.6 Soak (30 minutos carga moderada)

```bash
HEARTGUARD_SHAPE="soak" locust -f loadtests/locustfile.py --class BaselineUser --headless --run-time 35m --csv loadtests/results/soak --html loadtests/results/soak.html --host http://127.0.0.1:8080
```

#### 3.7 Break-point (incremental hasta fallo)

```bash
HEARTGUARD_SHAPE="breakpoint" locust -f loadtests/locustfile.py --class BaselineUser --headless --csv loadtests/results/breakpoint --html loadtests/results/breakpoint.html --host http://127.0.0.1:8080
```

> Esta forma añade 40 usuarios cada minuto (máx. 500). Observa métricas de error/latencia para identificar el umbral.

## 4. Registro de resultados

-   Anota en tu bitácora: comando ejecutado, timestamp, duración, usuarios máximos, spawn rate, CPU/RAM observados.
-   `--csv` produce: `*_stats.csv`, `*_failures.csv`, `*_stats_history.csv`. Incluye estos artefactos junto al reporte HTML en `loadtests/results/`.
-   Complementa con logs del backend (`make dev`) y métricas de infraestructura según tu entorno.

## 5. Notas operativas

-   El backend solo acepta tráfico loopback por defecto (`LoopbackOnly`). Si ejecutas Locust desde otra máquina, elimina/ajusta ese middleware o despliega un túnel seguro.
-   Las operaciones `POST` usadas en las pruebas son idempotentes: reafirman estatus y roles para evitar ensuciar datos.
-   Si necesitas ampliar el conjunto de usuarios, reejecuta el generador CSV o actualiza `users.csv` y vuelve a lanzar `register_users.py`.
