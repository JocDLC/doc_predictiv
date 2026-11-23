# laboratorio-agent-browser-hang

## Why

Una corrida real del laboratorio con motor `agent_browser` (43 leads) se
colgó después de 9 leads `apto`: el proceso quedó vivo ~70 min sin
progreso, bloqueando la UI (`"ya está corriendo"`). No hubo timeout ni
diagnóstico — solo un stop manual liberó la bandera. Hoy el motor
`agent_browser` no es seguro de operar.

## What Changes

- Diagnóstico: reproducir el hang y determinar dónde se congela
  `laboratory_browser` con el daemon `agent-browser` (espera de respuesta
  CDP, lock de pestaña, navegación, o espera de selector).
- `laboratory_browser.py` / `run_laboratory_queue.py`: timeout por lead y
  watchdog del engine — un lead que excede su presupuesto de tiempo queda
  `error` con motivo (no aborta ni cuelga la corrida).
- Heartbeat/progreso del proceso worker para que la UI pueda distinguir
  "procesando lento" de "colgado" (última actualización de resultados o
  archivo de progreso).
- Recuperación del flag `laboratorio_running` si el worker muere sin
  escribir el resultado final (la UI no queda bloqueada).
- Documentar en el resumen por lead la causa del timeout.

## Capabilities

### New Capabilities
- `laboratorio-timeout-watchdog`: límites de tiempo por lead, detección de
  worker colgado y recuperación del flag de corrida del laboratorio.

### Modified Capabilities
- (ninguna — no hay spec de laboratorio en `openspec/specs/`)

## Impact

- Código: `automation_salesforce/laboratory_browser.py`,
  `automation_salesforce/run_laboratory_queue.py`,
  `automation_salesforce/ui_server.py` (solo si hace falta exponer el
  heartbeat), tests del laboratorio.
- Datos: campos nuevos en el resultado por lead (motivo de timeout) —
  compatibles, son aditivos.
- Sin cambios en el motor `selenium` (queda como está) ni en la mecánica
  de documentación en Salesforce.
