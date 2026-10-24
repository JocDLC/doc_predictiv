# Tasks: distribuir-leads-desde-archivo

## Implementación

- [x] `requirements.txt`: fijar `openpyxl==3.1.5`.
- [x] `distribucion_loader.py` (nuevo): `parse_archivo(filename, bytes)`
      → `{sheets: [{name, headers, rows}]}` para `.xlsx` (openpyxl) y
      `.csv` (sniff separador + utf-8-sig/cp1252), tope 1000 filas/hoja.
- [x] `lead_monitor.py`: extraer `save_contact_panel_if_present(driver,
      timeout)` (panel "Contact Client" best-effort, sin marcas) y
      reusarlo dentro de `finalize_pick_up`.
- [x] `run_distribucion_queue.py` (nuevo): runner por lote — abre cada
      lead, resuelve propietario (destino / usuario del bot / cola
      configurada / otro), pickup si cola + panel best-effort,
      `reassign_owner`, `record_result` por lead (patrón
      `closure_store` + `local_audit`).
- [x] `ui_server.py`: `POST /api/distribucion/parse`,
      `PUT /api/distribucion-queue` (persiste cola, validación +
      warning `monitor_activo`), `GET /api/distribucion-results`,
      `POST /run-distribucion` (guard de proceso único).
- [x] UI (`documentador_predictivo.html` + ambas copias en `dist/`):
      módulo "Distribuir leads" en el selector de inicio — carga de
      archivo (base64), selector de hoja, mapeo con autodetección,
      vista previa editable con exclusiones, ejecutar y resultados.

## Tests

- [x] `parse_archivo`: xlsx multi-hoja (estructura de `QUALIF 24-10.xlsx`:
      hojas `Leads`/`Duplicados`, destino en `Otra información`);
      csv con `;` y con `,`; cp1252; archivo corrupto → error.
- [x] Runner con driver mockeado: owner=destino → `ya_asignado` sin
      tocar; owner=cola excluida (COLD/EXPORT_GETLEAD/LEADIT_EXPORT) →
      `cola_excluida` sin tocar; owner=cola de ingreso → pickup +
      reassign; owner=tercero/bot → reassign directo; fallo de lookup →
      `reasignacion_error:opcion`.
- [x] Endpoints: parse devuelve hojas sin persistir; queue persiste solo
      lead_id+persona + warning monitor; queue inválida → 400; results
      vacío → `[]`.
- [x] `finalize_pick_up` sin regresión tras extraer el helper de panel.
- [x] Suite completa (512 tests) + `ruff check` OK.

## Cierre

- [ ] Prueba de parseo+preview con `ARCHIVOS_UTILES/QUALIF 24-10.xlsx`
      en la UI real (sin tocar Salesforce — pedido explícito del usuario).
- [ ] Prueba real acotada: 1 lead de la BD reasignado en vivo, con el
      usuario presente y monitor pausado.
- [x] Sync a `dist/`.
- [x] `MEMORY.md` + `graphify update .` + log en Gantt.
