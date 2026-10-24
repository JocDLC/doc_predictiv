# Design: distribuir-leads-desde-archivo

## Context

Los leads que entran en horario no hábil quedan en la bandeja/cola
(`AR_LEAD_QUALIF`, `Propietario del candidato` = cola). A la mañana el
supervisor exporta el reporte (`QUALIF 24-10.xlsx`: hoja `Leads` +
`Duplicados`, ~17 filas) con la persona destino ya resuelta en una
columna (en el ejemplo, `Otra información` trae el nombre; `Distribucion`
está vacía). La mecánica de reasignación ya existe y fue verificada en
vivo (`reassign_owner`, `press_pick_up`, `wait_record_owner` en
`lead_monitor.py`).

## Goals / Non-Goals

**Goals:**

- Subir `.xlsx`/`.csv`, mapear columnas (Lead ID + destino), revisar y
  editar destinos por fila, ejecutar la reasignación en lote con
  resultados por lead.
- Reutilizar `run_close_queue.py` como patrón de runner y el patrón
  cola JSON → `.resultado.json` → UI.
- Nunca escribir en `Otra información`; solo cambiar el propietario.

**Non-Goals:**

- Reparto automático (round-robin): el archivo dice el destino.
- Escribir comentarios, cerrar leads ni enviar WhatsApp.
- Integración con Wolkvox ni subida a servidores externos.

## Decisions

### Parseo server-side con openpyxl

`POST /api/distribucion/parse` recibe `{filename, content_b64}` y
devuelve `{sheets: [{name, headers, rows}]}` (tope 1000 filas por hoja).
El archivo nunca se persiste en disco — solo la cola derivada
(`lead_id` + `persona`, sin datos personales).

- **vs. parser xlsx en JS**: un lector xlsx hand-rolled (zip + XML +
  sharedStrings + multi-hoja) suma ~300 líneas frágiles al HTML único;
  openpyxl ya está en el entorno y cubre los casos borde. El servidor es
  localhost: la privacidad "100% local" se mantiene.
- `.csv` se parsea por el mismo endpoint (sniff `;`/`,`/tab, encoding
  `utf-8-sig` → `cp1252` fallback): una sola ruta de parseo.
- `requirements.txt` gana `openpyxl==3.1.5` (versión ya instalada).

### Contrato de endpoints

```
POST /api/distribucion/parse   {filename, content_b64}
                             → {sheets:[{name,headers,rows}]}
PUT /api/distribucion-queue   {source_file, leads:[{lead_id,persona}]}
                             → escribe queues/cola_distribucion.json
                               + spawns run_distribucion_queue.py
GET  /api/distribucion-results → cola_distribucion.resultado.json
```

La UI envía a la cola **la vista previa ya editada** — el servidor no
relee el archivo ni conoce las columnas.

### Flujo del runner por lead

```
open_record → wait_record_owner
 ├─ owner == destino              → ya_asignado (no se toca nada)
 ├─ owner == cola excluida        → cola_excluida (frío/exportados,
 │                                  SKIP_OWNERS: AR_LEAD_COLD,
 │                                  AR_LEAD_EXPORT_GETLEAD,
 │                                  AR_LEAD_LEADIT_EXPORT)
 ├─ owner == cola (unassigned_*)  → press_pick_up → wait_owner_changed
 │                                 → save panel best-effort → reassign_owner
 └─ owner == cualquier otro       → reassign_owner directo al destino
```

- "En cola" = matchea cualquier `unassigned_owner` de las bandejas del
  `config.json` (reutiliza `owner_is_unassigned`). La lista se pasa al
  runner por argumento/config — la cola JSON no necesita el dato.
- Tras el pickup, el panel "Contact Client" se guarda best-effort con
  `PANEL_PRESENT_SCRIPT`/`PANEL_SAVE_CLICK_SCRIPT` **sin** escribir la
  marca `Asignado` — un helper chico `save_contact_panel_if_present`
  compartido con `finalize_pick_up` (extrae el bloque existente, cero
  duplicación).
- `reassign_owner` devuelve `reasignado`/`reasignacion_error:<paso>`
  verificado por relectura del propietario — sin cambios.
- La comparación destino/propietario usa `normalized_key` con match en
  ambos sentidos (igual que `_encargada_para_lead`), así "ROGER FABIAN
  VELASCO CAMERO" en el archivo matchea "Roger Fabian Velasco Camero"
  en Salesforce.

### Resultados incrementales

`record_result` por lead (patrón `closure_store`): el `.resultado.json`
se actualiza por lead, la UI lo relee mientras corre el proceso — igual
que la cola de cierre. Outcomes: `reasignado`, `ya_asignado`,
`otro_propietario`, `pickup_error`, `lead_inaccesible`,
`reasignacion_error:<paso>`.

### Vista previa editable

Tabla con checkbox (excluir filas puntuales), lead_id, nombre si la
columna se mapeó, y **input de destino editable** por fila. El payload
de `/queue` es exactamente lo que quedó en la tabla.

## Risks / Trade-offs

- Monitor activo sobre la misma bandeja mientras corre el lote → puede
  tomar/reasignar leads en paralelo con reglas distintas (franjas del
  equipo). → La UI avisa "pausá el monitor antes de ejecutar"; el
  endpoint `/queue` devuelve `monitor_activo: true` como advertencia,
  no como bloqueo.
- Nombre mal escrito → el lookup no matchea → `reasignacion_error:opcion`;
  el lead queda donde estaba y el error queda explícito.
- Archivo con destino equivocado sobre un lead de un tercero → el bot
  reasigna igual (la BD manda); la vista previa editable es la defensa:
  el operador revisa/corrige destinos antes de ejecutar.
- Panel "Contact Client" bloqueando la siguiente navegación → se guarda
  best-effort; si no se pudo, el lead ya quedó reasignado igual (igual
  que en el monitor: el panel no degrada el outcome).
- Lote interrumpido → resultados incrementales permiten re-ejecutar;
  `ya_asignado` lo hace idempotente.

## Open Questions

- ¿La columna de nombre del lead (para mostrar en la tabla) se mapea
  opcionalmente o se muestra solo lead_id + destino? → propuesta: mapeo
  opcional de "Nombre" para legibilidad, sin uso funcional.
