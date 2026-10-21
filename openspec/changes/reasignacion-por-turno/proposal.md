# Propuesta: reasignacion-por-turno

## Why

El control de la bandeja y el pickup se reparte entre varias personas por
horarios (división equitativa configurable: 1h cada uno, luego 2h, etc.).
Hoy el bot toma los leads con el usuario logueado y ahí quedan — pero
mientras no todos tengan la app, los leads de la franja de otro auxiliar
hay que **reasignarlos manualmente** en Salesforce. Es el mismo problema
de siempre: alguien pendiente de la bandeja.

## What Changes

- La UI gana una sección **"Equipo"**: personas destinatarias con
  - **nombre exacto** tal como aparece en el lookup de Salesforce
    (`Nombre + usuario`, ej. `Micaela Caetano f063810`),
  - **franjas horarias propias** (formato hh:mm igual al menú de horario
    actual; el mismo usuario logueado puede figurar con sus franjas).
- En cada toma, el monitor determina la **encargada activa** según la
  franja vigente:
  - Si no hay encargada o la franja pertenece al **propio usuario
    logueado** → flujo actual intacto (`Asignado`, o intento + WhatsApp
    automático en AR).
  - Si la encargada es **otra persona** → el comentario queda
    `Asignado - <método>` derivado de `preferencia_contacto` del lead
    (whatsapp → `Enviar Whatsapp`, llamada/teléfono → `Llamarlo`, otro →
    `Gestionarlo`; nunca el intento WhatsApp), se abre el modal
    "Cambiar propietario de Candidato" desde el lápiz del campo
    `Propietario del candidato`, se tipea el nombre, se elige la opción
    del lookup y se confirma con `Cambiar propietario`. Luego se verifica
    que el propietario cambió.
- **Regla dura**: un lead reasignado NUNCA recibe el WhatsApp automático —
  el envío sale de la sesión del usuario logueado; para leads reasignados
  el primer contacto lo hace la encargada (documentado en el comentario).
- Nuevos outcomes en `finalizacion`: cuarto segmento `reasignado` /
  `reasignacion_error:<paso>` (el lead nunca se pierde: si la
  reasignación falla queda con el usuario del bot y el fallo queda
  registrado).

## Capabilities

### New Capabilities

(ninguna — extiende el monitor de bandeja existente)

### Modified Capabilities

- `monitor-bandeja-leads`: el flujo de finalización gana la reasignación
  condicionada por franja horaria de la encargada, y el estado del
  monitor gana la lista `equipo` (personas + franjas).

## Impact

- `automation_salesforce/lead_monitor.py`: helper de reasignación
  (lápiz en shadow DOM → modal → lookup → confirmar → verificar),
  `finalize_pick_up`/`take_lead`/`run_bandeja_cycle` reciben la
  encargada activa.
- `automation_salesforce/monitor_store.py`: `equipo` en el estado,
  validación de franjas reutilizando `validate_schedule`.
- `automation_salesforce/ui_server.py`: endpoint `POST
  /api/monitor/equipo`, payload y SSE.
- `documentador_predictivo.html` (+ copias en `dist/`): sección Equipo.
- Interacción Salesforce ya verificada en vivo sobre el lead
  `00QbD00000vUTK1UAO` (modal abierto, lookup tipeado, opciones
  listadas, cancelado sin guardar).
