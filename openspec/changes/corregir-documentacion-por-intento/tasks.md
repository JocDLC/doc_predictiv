# Tareas: corregir-documentacion-por-intento

> Convención: `[ ]` pendiente, `[~]` en curso, `[x]` hecha. Una tarea a la vez.
> Tras cada fase: `python -m unittest discover -s tests` y
> `python -m ruff check . --select E4,E7,E9,F` desde `automation_salesforce/`.
> Nunca pegar contenido de `Otra información` ni datos de clientes en chat,
> logs o tests: solo conteos, IDs enmascarados y nombres de campos.

## Fase 0 — Preflight

- [x] 0.1 Respaldo fechado en `_respaldo/20261001_pre_fix/` (ignorado por Git).
- [x] 0.2 Suite base anotada: 145 tests OK, Ruff OK. Servidor arriba pero
      sin tanda activa (`{"running": false}`).

## Fase 1 — Identidad por llamada (Python)

- [x] 1.1 `attempt_identity.py`: `documented_call_ids(field_text)` y
      `partition_attempts(existing_comment, attempts)` →
      `(missing, present_ids, unverifiable)`. Comparación exacta de strings;
      un intento sin `call_id` con campo no vacío queda `unverifiable`.
- [x] 1.2 `queue_loader.py`: `load_queue_file()` devuelve
      `{leads, run_id, source_file}`; `load_queue()` conserva su contrato.
- [x] 1.3 `snapshot_store.record_snapshot(path, lead_id, field_value, run_id, call_ids)`.
- [x] 1.4 `run_document_queue.py`: args `--run-id`, `--results`,
      `--snapshots`, `--metrics`; estados `ya_documentado`/`revision`;
      `result_entry` con `run_id`, `request_call_ids`, `documented_call_ids`,
      `added_call_ids`; snapshot desde el texto verificado.
- [x] 1.5 `productivity_metrics.summarize_results`: buckets nuevos.
- [x] 1.6 Tests: partición, dedupe, ya_documentado, revision, métricas.

## Fase 2 — Cola inmutable y `/run` (servidor)

- [x] 2.1 `ui_server.py`: lock de ejecución, freeze a `run_<run_id>.json`,
      `--run-id` y overrides de salidas; PUT sigue siendo borrador.
- [x] 2.2 Tests del endpoint: run_id generado, cola congelada, lock
      frente a ejecuciones simultáneas.

## Fase 3 — UI: modelo por `call_id` (JS)

- [x] 3.1 Helpers: `documentedCallIdSet`, `pendingAttempts`,
      `extractCallIdsFromText`, nuevo `isDone`.
- [x] 3.2 `applyBotResult`/`applySnapshot`/`importBotResults`/
      `importSnapshots` con la nueva semántica (legado = histórico).
- [x] 3.3 `buildBotQueue` exporta solo intentos pendientes.
- [x] 3.4 `pollBotResults` no reescribe la cola si el bot corre; etiqueta
      `historico` en `renderQueueList` para resultados sin `run_id`.
- [x] 3.5 `setDone` manual registra `manualDone` + `call_ids` visibles.
- [x] 3.6 Tests JS en Node `vm` (fixture ficticia; salta si no hay node):
      reproduce el incidente y cubre migración, polling e importación.

## Fase 4 — Integración

- [x] 4.1 Suite Python + tests JS + Ruff + harness + `git diff --check`.
- [x] 4.2 Prueba aislada del flujo UI con datos ficticios (sin Salesforce).

## Fase 5 — Paquete

- [x] 5.1 Copiar módulos runtime actualizados a `dist/DocumentadorPredictivo/app/`.
- [x] 5.2 ZIP limpio, extracción nueva, `INICIAR.bat`, sin datos operativos.

## Fuera de alcance

- Volver a ejecutar los 22 casos ya corregidos por el usuario.
- Cambios de esperas Lightning ni rediseño del Guardar.
