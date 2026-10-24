# Propuesta: distribuir-leads-desde-archivo

## Why

Los leads que ingresan en horario no hábil quedan acumulados y, al iniciar
la jornada, hay que repartirlos entre las personas que trabajan ese día.
Hoy esa distribución es manual en Salesforce: abrir cada lead, abrir el
modal "Cambiar propietario", tipear el nombre, confirmar — un lead a la
vez, con alguien pendiente de la bandeja.

## What Changes

- La UI gana un módulo **"Distribuir leads"** (entrada desde el selector
  de inicio) con el flujo:
  1. **Cargar archivo**: `.xlsx` o `.csv` (export de Salesforce con la BD
     de leads, ej. `QUALIF 24-10.xlsx`). El parseo lo hace el servidor
     local vía `POST /api/distribucion/parse`; nada sale de la máquina.
  2. **Mapear columnas**: autodetección + selección manual (mismo patrón
     que "Preparar campaña predictiva"): columna de `Lead ID` y columna
     de persona destino (ej. `Otra información`). Si el archivo trae
     varias hojas, se elige cuál usar.
  3. **Vista previa editable**: tabla lead → persona con el destino
     editable por fila (situaciones especiales) antes de ejecutar.
  4. **Ejecutar**: `PUT /api/distribucion-queue` persiste la cola y
     dispara el runner `run_distribucion_queue.py`; resultados por lead
     visibles en la UI (mismo patrón que cola de cierre).
- El runner abre cada lead por `lead_id`, resuelve el propietario actual
  y reasigna con la maquinaria existente (`press_pick_up` si el lead está
  en cola, `reassign_owner` para el cambio de propietario). **No escribe
  nada en `Otra información`** — solo cambia el propietario.
- **Regla del propietario**: si el lead ya está asignado a la persona
  que indica el archivo → no se toca (`ya_asignado`). Si está en una
  cola excluida (`AR_LEAD_COLD`, `AR_LEAD_EXPORT_GETLEAD`,
  `AR_LEAD_LEADIT_EXPORT` — frío/exportados) → no se toca
  (`cola_excluida`). Si está en la cola de ingreso (ej.
  `AR_LEAD_QUALIF`) → Pick Up y luego reasignar. Si está asignado a
  cualquier otra persona → reasignar directo al destino del archivo.
- Resultados por lead: `reasignado`, `ya_asignado` (idempotente),
  `cola_excluida`, `pickup_error`, `lead_inaccesible`,
  `reasignacion_error:<paso>` — ningún lead se pierde ni se traga un
  error.

## Capabilities

### New Capabilities

- `distribucion-leads-archivo`: distribución por lote de leads hacia
  personas destino leídas de un archivo cargado en la UI, con mapeo de
  columnas, vista previa editable y reasignación verificada en
  Salesforce.

### Modified Capabilities

(ninguna — reutiliza la mecánica de reasignación del monitor sin cambiar
sus requisitos)

## Impact

- `automation_salesforce/run_distribucion_queue.py` (nuevo): runner por
  lote siguiendo el patrón de `run_close_queue.py`.
- `automation_salesforce/distribucion_loader.py` (nuevo): parseo y
  validación de `.xlsx`/`.csv` → filas `{lead_id, persona}`.
- `automation_salesforce/ui_server.py`: endpoints
  `POST /api/distribucion/parse`, `PUT /api/distribucion-queue`,
  `GET /api/distribucion-results`, `POST /run-distribucion` y lanzamiento del runner.
- `automation_salesforce/lead_monitor.py`: reutiliza `open_record`,
  `read_record_owner`, `press_pick_up`, `wait_owner_changed`,
  `reassign_owner` — sin cambios funcionales.
- `documentador_predictivo.html` (+ copias en `dist/`): vista
  "Distribuir leads" + entrada en el selector de inicio.
- `requirements.txt`: `openpyxl` (parseo de `.xlsx` server-side; ya
  instalado en el entorno, se fija la versión).
- Interacción Salesforce ya verificada en vivo sobre el modal "Cambiar
  propietario" (cambio `reasignacion-por-turno`); el lote de prueba usa
  `ARCHIVOS_UTILES/QUALIF 24-10.xlsx` **sin ejecutar cambios reales**
  hasta validación del usuario.
