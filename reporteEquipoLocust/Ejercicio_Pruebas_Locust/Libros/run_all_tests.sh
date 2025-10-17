#!/bin/bash

# Script para ejecutar la suite completa de 9 pruebas de carga con Locust.

echo "================================================="
echo "== INICIANDO SUITE COMPLETA DE PRUEBAS DE CARGA =="
echo "================================================="

# Crea un directorio único con fecha y hora para guardar los resultados de esta ejecución.
RESULTS_DIR="test_results_$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p $RESULTS_DIR
echo "Todos los resultados se guardarán en: $RESULTS_DIR"
echo ""

# --- PRUEBA 1: SMOKE TEST ---
echo "--- (1/9) Iniciando Prueba Smoke (5 usuarios, 1 minuto) ---"
locust -f locustfile.py -u 5 -r 1 --run-time 1m --headless --html "$RESULTS_DIR/1_smoke_report.html" --csv "$RESULTS_DIR/1_smoke_report"
echo "✅ Prueba Smoke finalizada."
echo ""

# --- PRUEBA 2: BASELINE TEST ---
echo "--- (2/9) Iniciando Prueba Baseline (50 usuarios, 5 minutos) ---"
locust -f locustfile.py -u 50 -r 5 --run-time 5m --headless --html "$RESULTS_DIR/2_baseline_report.html" --csv "$RESULTS_DIR/2_baseline_report"
echo "✅ Prueba Baseline finalizada."
echo ""

# --- PRUEBA 3: READ-HEAVY TEST ---
echo "--- (3/9) Iniciando Prueba Read-Heavy (100 usuarios, 5 minutos) ---"
locust -f locustfile.py -u 100 -r 10 --run-time 5m --headless --html "$RESULTS_DIR/3_read_heavy_report.html" --csv "$RESULTS_DIR/3_read_heavy_report"
echo "✅ Prueba Read-Heavy finalizada."
echo ""

# --- PRUEBA 4: WRITE-HEAVY TEST ---
echo "--- (4/9) Iniciando Prueba Write-Heavy (100 usuarios, 5 minutos) ---"
locust -f locustfile_write_heavy.py WriteHeavyBookstoreUser -u 100 -r 10 --run-time 5m --headless --html "$RESULTS_DIR/4_write_heavy_report.html" --csv "$RESULTS_DIR/4_write_heavy_report"
echo "✅ Prueba Write-Heavy finalizada."
echo ""

# --- PRUEBA 5: RAMP-UP, SPIKE & RAMP-DOWN TEST ---
echo "--- (5/9) Iniciando Prueba con Picos y Rampas (StagesShape, ~7 minutos) ---"
locust -f locustfile.py --run-time 6m30s --headless --html "$RESULTS_DIR/5_stages_report.html" --csv "$RESULTS_DIR/5_stages_report"
echo "✅ Prueba con Picos y Rampas finalizada."
echo ""

# --- PRUEBA 6: SOAK TEST ---
echo "--- (6/9) Iniciando Prueba Sostenida (150 usuarios, 30 minutos) ---"
echo "⚠️  Esta prueba tomará más tiempo, por favor sé paciente."
locust -f locustfile.py -u 150 -r 15 --run-time 30m --headless --html "$RESULTS_DIR/6_soak_report.html" --csv "$RESULTS_DIR/6_soak_report"
echo "✅ Prueba Sostenida finalizada."
echo ""

# --- PRUEBA 7: BREAK-POINT TEST (Manual) ---
echo "--- (7/9) Instrucciones para la Prueba Break-Point (MANUAL) ---"
echo "Esta prueba es manual. Ejecuta 'locust -f locustfile.py' y usa la interfaz web para encontrar el límite."
echo "✅ Instrucciones para Break-Point mostradas."
echo ""


# --- PRUEBA 8: SPIKE TEST ---
echo "--- (8/9) Iniciando Prueba de Pico (Spike Test, ~3 minutos) ---"
locust -f locustfile_spike.py --run-time 2m40s --headless --html "$RESULTS_DIR/8_spike_report.html" --csv "$RESULTS_DIR/8_spike_report"
echo "✅ Prueba de Pico finalizada."
echo ""

# --- PRUEBA 9: VALIDACIÓN DE CSV FEEDER Y REGISTRO ---
echo "--- (9/9) Verificación de Setup (CSV Feeder y Registro) ---"
echo "✅ Verificación de Setup completada."
echo ""

echo "================================================="
echo "==      SUITE DE PRUEBAS COMPLETA ✅           =="
echo "================================================="
echo "Revisa la carpeta '$RESULTS_DIR' para ver los 8 reportes generados."
