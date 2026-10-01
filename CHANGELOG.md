# Historial de versiones

La versión vigente es la constante `APP_VERSION` de `documentador_predictivo.html`
(única fuente). `ui_server.py` la expone en `GET /status` como `version`.

Esquema: [SemVer](https://semver.org/lang/es/) — `MAYOR.MENOR.PARCHE`.

- **MAYOR**: cambios que rompen compatibilidad (formato de cola, resultados, snapshots).
- **MENOR**: funcionalidad nueva compatible.
- **PARCHE**: correcciones de defectos.

Cada versión liberada lleva un tag de Git `v<versión>`.

## [1.0.0] — 2026-10-01

Primera versión etiquetada. Corrige el incidente de "falsos documentados"
detectado el 2026-10-01.

### Corregido

- Un Lead ya no se marca como documentado por un resultado o snapshot
  histórico que solo coincide por `lead_id`: el estado ahora es por
  Lead + `call_id` concretos.
- Resultados/snapshots legados (sin `run_id` ni `call_ids`) se muestran como
  `histórico` y no confirman intentos nuevos.
- La marca manual registra el conjunto de intentos visto al marcar
  (`manualDoneScope`): un intento nuevo del mismo CSV no hereda el check.
- La cola activa solo exporta intentos pendientes; `pollBotResults` no la
  reescribe mientras el bot corre.
- El bot es idempotente: antes de escribir en `Otra información` lee el campo,
  deduce los `call_id` presentes y agrega solo los faltantes. Estados nuevos:
  `ya_documentado` (sin escritura) y `revision` (intento no verificable).

### Agregado

- `attempt_identity.py`: extracción de `call_id` y partición de intentos.
- `run_id` estable por ejecución: el servidor congela la cola en
  `run_<run_id>.json` bajo lock; resultados, snapshots y métricas quedan
  enlazados a ese run.
- Snapshots con `run_id`, `call_ids`, `content_hash` y `read_at`.
- Botón "Reiniciar navegador del bot" (`POST /api/restart-browser`).
- Badge de versión en el pie + aviso si el servidor tiene versión distinta.
- 21 tests nuevos (identidad, cola, snapshots, servidor, UI en Node `vm`).

### Compatibilidad

- El formato de cola/resultados/snapshots gana campos nuevos pero acepta los
  archivos anteriores (se tratan como históricos).

## Hitos previos (sin etiquetar)

| Commit | Descripción |
|--------|-------------|
| `9a3d1e7` | Documentación automática con guardado verificado y cola viva |
| `35a451f` | Aviso de columnas omitidas y alto de fila ajustable |
| `1fdf366` | UI local para leads QUALIF |
| `e0850e1` | Automatización local asistida de Salesforce |
| `7119405` | Aplicación de campañas predictivas inicial |
