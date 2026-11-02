# Tareas — distribuir-leads-modo-prueba

1. [x] `lead_monitor.py`: `verify_persona_option(driver, nombre, timeout)` — reutiliza
   `open_change_owner_dialog` + `_wait_owner_search_input` + `_pick_owner_option` y
   SIEMPRE cierra con `_dismiss_owner_dialog`; nunca pulsa confirmar. Devuelve
   `opcion_ok` / `reasignacion_error:modal|busqueda|opcion`.
2. [x] `distribucion_loader.py`: `validate_distribucion_queue` acepta `modo`
   opcional (`"real"` | `"prueba"`, default `real`); `load_distribucion_queue`
   lo devuelve.
3. [x] `run_distribucion_queue.py`: si `modo == "prueba"` corre
   `simulate_one_lead` — lee propietario y clasifica; para reasignables verifica
   el nombre vía `verify_persona_option`. Estados: `prueba_ok:ya_asignado`,
   `prueba_ok:cola_excluida`, `prueba_ok:reasignar`,
   `prueba_ok:pickup_y_reasignar`, `prueba_nombre_no_encontrado`,
   `prueba_inaccesible`, `prueba_error:<paso>`. Jamás llama a
   `press_pick_up`/`reassign_owner`/`_confirm_owner_dialog`.
4. [x] `ui_server.py`: la cola PUT acepta `modo` y el resultado de la corrida
   queda distinguible (los estados `prueba_*` ya lo son).
5. [x] UI (`documentador_predictivo.html` + dist): casilla "Modo prueba" muy
   visible en el paso de vista previa (banner violeta estilo Monitor de Bandeja);
   con la casilla marcada el botón pasa a "Probar (sin guardar)"; la tabla de
   resultados muestra los estados `prueba_*` traducidos y un banner
   "Simulación — nada se guardó en Salesforce".
6. [x] Tests: loader (modo en cola), runner simulado por rama (mock driver,
   verificar que nunca se llaman pickup/reassign/confirm), `verify_persona_option`
   (siempre cierra el modal, nunca confirma), endpoint (modo aceptado).
7. [x] Verificación: `python harness.py test`, `ruff check`, sync a `dist/`,
   `openspec validate --changes`, `graphify update .`, log en Gantt.
