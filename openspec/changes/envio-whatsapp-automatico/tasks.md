# Tasks: envio-whatsapp-automatico

## Implementación

- [x] `lead_monitor.py`: `_ensure_take_mark(driver, timeout, mark_text)` —
      `Asignado` vs línea de intento; "ya documentado" por
      `_lead_documented` (`Asignado` o regex `\d+ INT`).
- [x] `lead_monitor.py`: `_whatsapp_attempt_line()` →
      `1 INT Envío WhatsApp DD/MM/AAAA HH:MM` (hora local).
- [x] `lead_monitor.py`: `send_whatsapp(driver)` — clic en
      `Send To Whatsapp` (ribbon `runtime_platform_actions`), espera del
      toast verde, cierre con X; devuelve
      `wa_ok`/`wa_no_confirmado`/`wa_sin_boton`/`wa_error:<exc>`.
      Nunca reintenta el clic.
- [x] `lead_monitor.py`: `finalize_pick_up(..., whatsapp=)` encadena el
      tercer segmento del outcome; `_wants_whatsapp_send` (AR + toggle +
      preferencia); `take_lead`/`run_bandeja_cycle` pasan details+flag.
- [x] `ui_server.py`/`monitor_store.py`: `enviar_whatsapp` en estado,
      default `False`, persistencia, `POST /api/monitor/whatsapp`,
      `_monitor_payload` y SSE.
- [x] UI (`documentador_predictivo.html` + ambas copias en `dist/`):
      checkbox "WhatsApp auto" junto a Modo prueba.

## Tests

- [x] Rama whatsapp AR+toggle: escribe `1 INT Envío WhatsApp ...` y no
      `Asignado`; outcome `.../wa_ok`.
- [x] Preferencia distinta / toggle apagado / bandeja no-AR → solo
      `Asignado`, sin segmento `wa`.
- [x] Campo ya con `N INT` o `Asignado` → no duplica, envía igual.
- [x] Toast ausente → `wa_no_confirmado`, un solo clic.
- [x] Botón ausente → `wa_sin_boton`, sin excepción.
- [x] Toggle persiste (`test_whatsapp_endpoint_persists_flag`) y figura en
      el payload del monitor.

## Cierre

- [x] Suite completa (432 tests) + `ruff check` limpios.
- [x] Sync a `dist/`, `/api/reload`, `enviar_whatsapp: False` confirmado
      en el payload en vivo.
- [ ] Verificación en vivo del próximo lead AR-whatsapp (toggle primero
      apagado, luego encendido).
- [x] `MEMORY.md` + `graphify update .` + log en Gantt.
