# tiempo-total-informes

## Why

Los informes de fin de proceso no muestran cuánto demoró el ciclo completo.
La métrica ya existe en los JSON (`cycle_elapsed_seconds` en
`productivity_metrics` y `laboratory_metrics`) pero la UI y la consola no la
exhiben, y Distribución ni siquiera la calcula. Sin ese dato no se puede
medir throughput real ni detectar regresiones de performance del bot.

## What Changes

- `documentador_predictivo.html`: `productivityMessage()` agrega el tiempo
  total del ciclo al alert de "Documentar" usando `cycle_elapsed_seconds`
  de `cola_activa.metricas.json`.
- `documentador_predictivo.html` + `ui_server.py` (si el endpoint ya expone
  métricas): el alert de cierre muestra `cycle_elapsed_seconds` de
  `cola_cierre_activa.metricas.json`.
- `run_distribucion_queue.py`: nuevo artefacto de métricas
  (`cola_distribucion_activa.metricas.json`) con `cycle_elapsed_seconds`,
  conteos por estado y per-lead elapsed agregado. **BREAKING** solo si un
  consumidor espera que el archivo no exista (ninguno conocido).
- `documentador_predictivo.html`: el informe final de Distribución muestra
  el tiempo total del ciclo.
- `documentador_predictivo.html`: el informe final del Laboratorio muestra
  `cycle_elapsed_seconds` de sus métricas.
- Los cuatro runners (`run_document_queue`, `run_close_queue`,
  `run_distribucion_queue`, `run_laboratory_queue`) imprimen el tiempo
  total en el "Resumen" final de consola.

## Capabilities

### New Capabilities
- `informes-tiempo-total`: contrato de tiempo total en los informes de fin
  de proceso (UI, tabla de resultados, JSON de métricas y resumen de
  consola) para Documentar, Cierre, Distribución y Laboratorio.

### Modified Capabilities
- `distribucion-leads-archivo`: la cola de distribución ahora emite un
  artefacto de métricas de ciclo con `cycle_elapsed_seconds`.

## Impact

- Código: `documentador_predictivo.html`, `automation_salesforce/ui_server.py`
  (solo si hace falta exponer métricas de cierre), `run_distribucion_queue.py`,
  `run_document_queue.py`, `run_close_queue.py`, `run_laboratory_queue.py`,
  tests asociados.
- Datos: nuevo `cola_distribucion_activa.metricas.json`; los demás JSON de
  métricas ya tienen el campo — el cambio es de presentación.
- Riesgo bajo: sin cambios en mecánica de Salesforce ni formatos de cola.
