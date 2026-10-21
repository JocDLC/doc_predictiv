# Tasks: reasignacion-por-turno

## Implementación

- [x] `monitor_store.py`: `equipo` en estado + validación (nombre
      requerido, franjas con `validate_schedule` por persona).
- [x] `lead_monitor.py`: `_encargada_activa(equipo, ahora)` + helpers del
      modal (lápiz shadow-DOM → "Cambiar propietario de Candidato" →
      lookup → opción → confirmar) + `reassign_owner(driver, nombre)`
      con verificación del propietario.
- [x] `lead_monitor.py`: `finalize_pick_up(..., encargada=)` — marca
      `Asignado - <método>` derivada de `preferencia_contacto` del lead,
      fuerza `whatsapp=False`, encadena segmento
      `reasignado`/`reasignacion_error:<paso>`;
      `take_lead`/`run_bandeja_cycle` calculan la encargada con el
      propietario post-pickup.
- [x] `ui_server.py`: `POST /api/monitor/equipo`, payload + SSE.
- [x] UI (`documentador_predictivo.html` + ambas copias en `dist/`):
      sección Equipo (nombre, franjas por persona).

## Tests

- [x] `_encargada_activa`: sin franja, franja vigente, solape (gana la
      primera), franja fuera de hora.
- [x] Encargada = propietario post-pickup → flujo normal (WA si aplica).
- [x] Encargada distinta → comentario `Asignado - <método>` según
      `preferencia_contacto`, sin envío WhatsApp, outcome `reasignado`
      con propietario verificado.
- [x] Lookup sin opción → `reasignacion_error:opcion`, modal cancelado,
      lead queda con el bot.
- [x] Endpoint persiste `equipo` y rechaza franjas inválidas.
- [x] Suite completa + `ruff check`.

## Cierre

- [x] Sync a `dist/` + `/api/reload` + verificar estado en vivo.
- [x] `MEMORY.md` + `graphify update .` + log en Gantt.
- [x] Borrar `probe_dom.py` / `probe_reassign.py`.
- [ ] Prueba real con `00QbD00000vUTK1UAO` (o próximo lead en franja de
      otra persona) — validar comentario y propietario final.
