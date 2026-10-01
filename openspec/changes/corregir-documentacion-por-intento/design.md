# Diseño: corregir-documentacion-por-intento

## Modelo de identidad

- La identidad mínima de un intento documentado es `(lead_id, call_id)`.
  `call_id` es un **string opaco** (p. ej. `1790709220.356411`): nunca se
  convierte a número ni se comparan subcadenas.
- En `Otra información`, una línea documentada tiene la forma
  `N INT<TAB>resultado<TAB>fecha<TAB>hora<TAB>callId`. El extractor solo toma
  el último token de líneas que empiezan con `N INT` y solo si cumple
  `\d{5,}\.\d{3,}`. Otros números (teléfonos, importes, fechas) no califican.
- Cada ejecución tiene `run_id` (`run_<UTC>_<rand>`). La cola congelada lo
  lleva como campo de nivel superior; cada `result_entry` y `record_snapshot`
  lo repite.

## Esquema de resultados (v2)

```json
{
  "lead_id": "00Q…",
  "status": "guardado|ya_documentado|parcial|revision|duplicado|error|omitido|preparado",
  "run_id": "run_20261001T163000Z_ab12cd",
  "source_file": "predictive-….csv",
  "request_call_ids": ["1790709220.356411"],
  "documented_call_ids": ["1790709220.356411"],
  "added_call_ids": [],
  "next_int": 6, "attempts": 2, "at": "…", "elapsed_seconds": 21.3
}
```

`documented_call_ids` es la lista verificada como presente tras el proceso;
`added_call_ids` los que se escribieron en esta ejecución. Las entradas sin
estos campos son legadas: solo informan historial, nunca confirman intentos.

## Esquema de snapshots (v2)

Igual que hoy (`lead_id`, `field_value`, `base_hash`, `read_at`) más
`run_id` y `call_ids` extraídos del `field_value` verificado.

## Flujo del runner

```text
por Lead:
  abrir registro → Comentario != "Lead Duplicado" → leer Otra información
  → partition_attempts(campo, intentos):
       presentes  → documentados sin escritura
       faltantes  → se componen y escriben (con numeración desde el último INT real)
       sin call_id con campo no vacío → revision
  → todos presentes: ya_documentado (sin abrir el editor ni Guardar)
  → faltantes escritos y verificados: guardado | parcial
  → snapshot desde el MISMO texto verificado
```

## Flujo de la UI

- `documentedCallIds(lead)` = unión de: `progress[].documentedCallIds`,
  `call_ids` extraídos del `fieldSnapshot` vigente.
- `isDone(lead)` = todo intento del CSV actual tiene `call_id` y está en el
  conjunto documentado, o el operador marcó `manualDone` explícitamente.
- `applyBotResult` aplica `documented_call_ids` del resultado; una entrada
  legada solo deja `historicalStatus` para mostrar "histórico" en la cola.
- `applySnapshot` extrae `call_ids` del `field_value` (evidencia real) y los
  marca; ya no pone `done` incondicional.
- `buildBotQueue` solo incluye intentos pendientes por Lead.
- `pollBotResults` solo reescribe `cola_activa.json` cuando el bot NO está
  corriendo, para no mezclar con la tanda en curso.
- `setDone(lead, true)` registra `manualDone` + `call_ids` visibles como
  declaración manual del operador.

## Migración local sin borrar

Los registros viejos de `dp_progress_*` conservan `done`, `fieldSnapshot`,
`preparedComment`, `editedSnapshot`, `baseHash`, etc. La lectura deriva
`documentedCallIds` desde `fieldSnapshot`; un `done` legado sin evidencia
de llamadas queda como estado `historico` y el Lead vuelve a ser elegible,
donde el runner idempotente lo resuelve en `ya_documentado` si corresponde.

## Concurrencia

`POST /run` toma un lock, copia `cola_activa.json` + `run_id` a
`queues/run_<run_id>.json` y lanza el runner sobre esa copia con
`--results/--snapshots/--metrics` apuntando a los archivos activos, para que
el polling siga mostrando el progreso en vivo sin releer el archivo mutable.
Un `PUT /api/queue` concurrente solo prepara el borrador de la próxima tanda.
