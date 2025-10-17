Resumen de Comandos y Hallazgos de Pruebas

Este documento sirve como bitácora de los comandos ejecutados durante las pruebas de carga del microservicio de autenticación y resume los hallazgos clave de cada etapa.

Fase 1: Diagnóstico (Pre-Optimización)

El objetivo de esta fase fue evaluar el rendimiento inicial del servicio.

1. Prueba Smoke

Comando: locust -f locustfile.py -u 5 -r 1 --run-time 30s --host http://4.246.170.83:5001 --headless --csv=smoke --html=smoke.html

Hallazgo: Se detectó un cuello de botella crítico. El endpoint /auth/login mostró una latencia mediana de 11 segundos, causando inestabilidad general y picos de hasta 19 segundos en otras operaciones.

2. Prueba Baseline

Comando: locust -f locustfile.py -u 50 -r 5 --run-time 5m --host http://4.246.170.83:5001 --headless --csv=baseline --html=baseline.html

Hallazgo: Se confirmó la gravedad del problema. La alta latencia del login provocó fallos en cascada en endpoints que antes eran estables, como /api/user-profile, que registró 9 errores y un tiempo de respuesta máximo de 56 segundos.

Acción Correctiva: Se aplicaron índices a las columnas username y email de la tabla de usuarios en la base de datos.

Fase 2: Validación (Post-Optimización)

El objetivo de esta fase fue verificar la efectividad de la optimización y encontrar los nuevos límites del sistema.

3. Prueba Soak (Carga Sostenida)

Comando: locust -f locustfile.py -u 200 -r 20 --run-time 30m --host http://4.246.170.83:5001 --headless --csv=soak --html=soak.html

Hallazgo: Éxito total. El sistema manejó 200 usuarios concurrentes durante 30 minutos con cero fallos. La latencia del login se estabilizó en un promedio saludable de ~2.8 segundos. El sistema demostró ser robusto y estable.

4. Prueba Break-point (Punto de Quiebre)

Comando: locust -f locustfile.py -u 500 -r 50 --run-time 5m --host http://4.246.170.83:5001 --headless --csv=breakpoint_500 --html=breakpoint_500.html

Hallazgo: Se identificó el nuevo límite de rendimiento. El sistema no colapsó, pero a partir de ~200 usuarios concurrentes, la latencia comenzó a degradarse severamente (P99 de hasta 51 segundos), indicando que se alcanzó el límite de capacidad de la base de datos para procesar peticiones simultáneas.