## Why

Los leads que ingresan fuera del horario laboral de cada país (noches, fines de
semana, feriados) quedan en la cola QUALIF sin dueño de franja: nadie debería
tomarlos como "turno", pero sí hay que recogerlos para repartirlos cuando la
persona entra temprano. Hoy el monitor los toma en la franja vigente del momento
del procesado (fallback por fecha no usable/ayer), lo que los adjudica mal y
mezcla la custodia con el reparto.

## What Changes

- Nueva acción opcional en la vista Monitor: **"Recoger QUALIF fuera de
  horario"**, por bandeja, con `Desde`/`Hasta` (fecha + hora) editables en cada
  uso. Rango `[desde, hasta)` — viernes 18:00 incluye, lunes 06:00 excluye.
- Vista previa estrictamente de lectura: muestra los QUALIF elegibles del
  período y los excluidos con motivo. Ninguna acción de apertura (incluido
  entrar a la pantalla) toma leads sin confirmación explícita.
- Elegibilidad por lead: `fecha_creacion` convertida a la hora de la PC con el
  `tz_offset` ya configurable de la bandeja, dentro del rango pedido y **sin
  franja** (propia ni de equipo) que cubriera ese horario. Un lead que cayó en
  la franja de alguien sigue siendo de esa persona aunque se procese después
  (regla ya vigente, se conserva). Fecha ilegible → se lista para revisión,
  nunca se toma.
- Confirmación acotada a los IDs seleccionados: antes de cada Pick Up se relee
  que el lead sigue en la cola QUALIF de esa bandeja. La toma es a nombre del
  usuario logueado (custodia), sin reasignación ni WhatsApp.
- Los QUALIF tomados en apertura aparecen en **Distribuir leads** como fuente
  opcional mezclable con el Excel/CSV actual, con `Lead ID` como identidad
  única: mismo ID en ambas fuentes → una sola fila que conserva el destino del
  archivo. El reparto por archivo sigue igual; simular o agregar no consume
  nada.
- El fallback de la cobertura cambia de alcance: un lead sin fecha usable **no**
  se toma como si fuera de la franja actual si la clasificación lo deja en
  `revision`. **(cambio de comportamiento respecto al fallback actual)**

## Capabilities

### New Capabilities
- `apertura-qualif-no-habiles`: vista previa por bandeja y rango, clasificación
  por fecha de creación (turno personal / no laboral elegible / hábil sin
  cobertura / fuera de rango / revisión), confirmación exclusiva con el
  monitor, persistencia del lote y disponibilidad en la vista Distribuir.

### Modified Capabilities
- `monitor-bandeja-leads`: el fallback de la cobertura por lead para fecha no
  usable se restringe (pasa a `revision` cuando la clasificación no prueba
  cobertura); los nocturnos no se toman por franja del momento.
- `distribucion-leads-archivo`: la vista acepta como fuente adicional los
  QUALIF tomados en apertura, mezclados por Lead ID sin duplicar ni pisar
  destinos del archivo.

## Impact

- `automation_salesforce/lead_monitor.py` (clasificación por lead, toma de
  apertura), `monitor_store.py` (validaciones), `ui_server.py` (endpoints de
  preview/confirm/disponibles bajo `cycle_lock`), `documentador_predictivo.html`
  (UI de apertura y mezcla en Distribuir), nuevo módulo de dominio
  (`apertura.py`) y almacén (`apertura_store.py`).
- `distribucion_loader.py`/`reparto_equitativo.py` se reutilizan sin cambio de
  contrato; el runner de distribución no se toca.
- Sin endpoints públicos nuevos fuera del servidor local autenticado; sin
  cambios en formato de cola de distribución ni en mecánica de Salesforce
  (se reusan las primitivas de `take_lead`).
