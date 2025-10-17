# HeartGuard Load Test Results

## Environment & Test Data

-   CMS under test corriendo en `http://127.0.0.1:8080` (SSR backend + Redis + Postgres vía `make up`, `make dev`).
-   Comprobación previa de salud: `curl -f http://127.0.0.1:8080/healthz`.
-   Datos sintéticos: `loadtests/data/users.csv` contiene 300 credenciales (`loadtesterXXX@heartguard.dev` / `LoadTest#XXX`).
-   Alta en base ejecutada con:
    ```bash
    export DATABASE_URL="postgres://heartguard_app:dev_change_me@127.0.0.1:5432/heartguard?sslmode=disable"
    python3 loadtests/scripts/register_users.py
    unset DATABASE_URL
    ```
-   Locust 2.41.6 ejecutado dentro de `python3 -m venv .venv`; dependencias instaladas desde `loadtests/requirements.txt` más `zope.event` y `zope.interface`.

## Escenarios ejecutados

| Escenario     | Descripción breve                                                  | Comando base                                                       | Usuarios / Spawn     | Duración real    | Requests | Fails | Avg ms | P95 ms | P99 ms | Observaciones                                                                                                                  |
| ------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ | -------------------- | ---------------- | -------- | ----- | ------ | ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------ |
| Baseline      | Carga ligera y sostenida para validar navegación típica.           | `HEARTGUARD_SHAPE="baseline" locust ... -u 25 -r 5 --run-time 15m` | 25 / 5 s⁻¹           | 2 m 21 s (stats) | 1 827    | 0     | 13.8   | 28     | 190    | Carga estable; respuestas típicamente <30 ms. El run se detuvo antes de los 15 min planeados.                                  |
| Smoke         | Sanity check rápido de disponibilidad post-despliegue.             | `locust ... --class SmokeUser -u 5 -r 2 --run-time 5m`             | 5 / 2 s⁻¹            | 1 m 50 s         | 206      | 0     | 12.1   | 27     | 83     | Chequeo rápido sin errores ni latencias altas.                                                                                 |
| Read-heavy    | Mayoría de lecturas del dashboard y listados del CMS.              | `locust ... --class ReadHeavyUser -u 60 -r 6 --run-time 20m`       | 60 / 6 s⁻¹           | 2 m 10 s         | 4 011    | 0     | 16.5   | 39     | 230    | GET dominantes; ningún 4xx/5xx. El ensayo concluyó tras ~130 s.                                                                |
| Write-heavy   | Valida POST idempotentes (status y roles) bajo concurrencia media. | `locust ... --class WriteHeavyUser -u 40 -r 4 --run-time 20m`      | 40 / 4 s⁻¹           | 2 m 44 s         | 3 331    | 0     | 12.2   | 24     | 150    | POST idempotentes (`status`, `roles`) con latencias controladas; duración efectiva ~164 s.                                     |
| Ramp          | Escalada progresiva y descenso para observar degradación gradual.  | `HEARTGUARD_SHAPE="ramp" locust ...`                               | Forma 20→120→20      | 4 m 34 s         | 8 321    | 12    | 21.5   | 62     | 300    | 12 fallos (`429 Too Many Requests`) en `/superadmin/dashboard` durante el pico.                                                |
| Spike         | Aumento abrupto a ~150 usuarios simulando un pico de tráfico.      | `HEARTGUARD_SHAPE="spike" locust ...`                              | Forma 15→150→15      | 1 m 10 s         | 3 300    | 205   | 211.8  | 1 400  | 2 100  | 6.2 % de fallos (rate limiting en `/login`, `/superadmin/dashboard` y `/superadmin/users`). Latencia P99 >2 s durante el pico. |
| Soak (10 min) | Carga moderada prolongada; versión abreviada de la prueba de soak. | `HEARTGUARD_SHAPE="soak" locust ... --run-time 10m`                | 40 constantes        | 10 m 21 s        | 12 323   | 0     | 12.7   | 25     | 33     | Versión abreviada (10 min); métricas estables, sin fallos.                                                                     |
| Break-point   | Incrementos de 40 usuarios/min hasta encontrar el límite de fallo. | `HEARTGUARD_SHAPE="breakpoint" locust ...`                         | +40 u/min (máx. 500) | 7 m 48 s         | 41 088   | 3 998 | 53.0   | 120    | 1 200  | 9.7 % de fallos, principalmente `GET /superadmin/dashboard` (3 864 respuestas 429) a partir de ~40 usuarios concurrentes.      |

## Hallazgos clave

-   **Autenticación realista**: cada usuario virtual inicia sesión con credenciales únicas del CSV y mantiene estado (`_csrf`, roles, status). Se validó que el script de registro deja los usuarios activos y en rol `superadmin`.
-   **Límites actuales**: las pruebas de `spike` y `break-point` gatillan protección anti-abuso (HTTP 429) tan pronto como la concurrencia supera ~40 clientes. Esto marca el umbral operativo para planificación de capacidad o ajustes del middleware de rate limit.
-   **Escenarios sostenidos**: baseline, read-heavy, write-heavy y soak (10 min) completaron sin errores, con medias <17 ms y P95 <40 ms. Esto confirma que el CMS maneja carga moderada con holgura.
-   **Ramp-up controlado**: se observaron 12 respuestas 429 únicamente en la cumbre de 120 usuarios; considerar relajar el rate limit o escalar la infraestructura si se requiere ese throughput.
-   **Spike & break-point**: la degradación severa de latencia (P95 ~1.4 s, P99 >2 s) y fallos en login/dashboard indican que la protección actual impide escalar verticalmente sin ajuste. Útil para definir alertas e inspeccionar logs del middleware (`internal/middleware/ratelimit.go`).
