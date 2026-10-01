# Propuesta: corregir-documentacion-por-intento

## Contexto

Incidente del 2026-10-01 (ver `automation_salesforce/HANDOFF.md`, sección
PRIORIDAD): Leads marcados en verde como `guardado` que en Salesforce solo
conservaban comentarios anteriores. Se reprodujo que resultados y snapshots
históricos se aplican por `lead_id` y marcan `done: true` sin comprobar las
llamadas del CSV actual; el polling reescribe la cola y excluye esos Leads.
Además, el usuario ya corrigió los casos a mano, así que el reintento no debe
duplicar llamadas ya presentes en Salesforce.

## Objetivo

Pasar del modelo "Lead → hecho/no hecho" a "Lead + llamada (`call_id`) +
ejecución (`run_id`) → estado verificado":

1. La UI deriva pendientes/confirmados por `call_id`, nunca por Lead a secas.
2. Resultados y snapshots históricos quedan como referencia, pero no marcan
   como documentadas llamadas que no contienen.
3. El runner compara los `call_id` solicitados con los presentes en
   `Otra información` antes de escribir: solo agrega los ausentes.
4. Cada ejecución del bot trabaja sobre una cola inmutable identificada por
   `run_id`, y resultados/snapshots/métricas quedan enlazados a esa ejecución.

## Alcance

- `documentador_predictivo.html`: modelo de progreso por `call_id`,
  migración sin borrar del almacenamiento local, polling/importación que no
  confirma llamadas ajenas, cola que solo contiene intentos pendientes.
- `run_document_queue.py`: deduplicación por `call_id`, nuevos estados
  `ya_documentado`/`revision`, y registro de identidades en el resultado.
- `snapshot_store.py`, `queue_loader.py`, `productivity_metrics.py`: esquema
  versionado con `run_id` y `call_ids`.
- `ui_server.py`: `/run` congela la cola en un archivo `run_<run_id>.json`
  bajo exclusión mutua y enlaza los artefactos de la ejecución.
- Tests: reproducción del incidente con las funciones JS reales (Node `vm`)
  y tests Python de deduplicación, partición y contratos.

## Fuera de alcance

- Rediseñar esperas de Lightning ni la mecánica de Guardar.
- Re-procesar los 22 casos ya corregidos a mano por el usuario.
- Cambiar contratos históricos ya escritos: los archivos viejos se leen como
  evidencia histórica, no se reescriben.

## Estados del modelo

| Estado | Significado |
|---|---|
| `guardado` | Escritura nueva verificada releyendo el campo |
| `ya_documentado` | Todas las llamadas solicitadas ya estaban presentes; sin escritura |
| `parcial` | Subconjunto agregado; queda evidencia de cuáles `call_id` faltan |
| `revision` | Identidad insuficiente para decidir (intento sin `call_id` con campo no vacío, conflicto de contenido); sin escritura automática |
| `duplicado` | Comentario `Lead Duplicado` (sin cambios, ya existente) |
| `error` | Fallo de navegación/lectura/verificación |
| `historico` | Evidencia de una ejecución anterior sin `run_id`/`call_ids` asociables |
