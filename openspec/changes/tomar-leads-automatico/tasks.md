# Tasks: tomar-leads-automatico — "Monitor de Bandeja"

> Primera escritura sin confirmación por registro: `Pick Up` solo se pulsa tras
> re-verificar el propietario sin asignar en el registro, y `tomado` exige
> observar el cambio de propietario. Nunca repetir Pick Up a ciegas. Monitor
> apagado por defecto. Nunca datos de clientes ni contenido de campos en
> logs/tests/chat.

## 1. Contratos y estado (puro, sin Salesforce)

- [x] 1.1 `monitor_store.py`: carga/guardado tolerante de
  `ui_output/monitor_state.json` (`enabled`, `bandejas`, `schedule`,
  `last_cycle_at`, `paused_reason`, `results` acotados), validación de
  `lead_id` Salesforce, códigos de estado cerrados (`tomado`,
  `tomado_por_otro`, `no_verificado`, `error`, `session_lost`) y enmascarado de
  `lead_id` para logs.
- [x] 1.2 Validación de bandejas: código `AR|CO|MX`, URL `https://` de reporte
  Lightning, `unassigned_owner` no vacío (default `<CODE>_LEAD_QUALIF`) y
  `expected_status` (default `"Nuevo"`).
- [x] 1.3 Validación de franjas: formato `HH:MM`, `start < end`, sin solapes;
  lista vacía = siempre dentro de horario.
- [x] 1.4 Deduplicación: `lead_id` con estado final no se reprocesa; `error`
  permite un único reintento en el ciclo siguiente.
- [x] 1.5 Tests del store: persistencia, validaciones de bandejas y franjas,
  corte de `results`, estados cerrados, sin datos personales en logs.

## 2. Ciclo de monitoreo (driver falso en tests)

- [x] 2.1 `lead_monitor.py`: `run_cycle(driver, bandeja, store)` → refresh del
  reporte de la bandeja, `read_visible_unassigned_leads` con su
  `unassigned_owner` y `field_aliases`, doble condición propietario +
  `estado_candidato == expected_status`, iteración por Lead y resultados con
  `details`.
- [x] 2.2 Toma por Lead: abrir registro (`build_record_url`), releer
  propietario visible, localizar `Pick Up` por texto exacto en la barra de
  acciones (patrón any-frame existente), clic y relectura del propietario.
- [x] 2.3 Detección de sesión caída (redirect a login) → `session_lost` y
  pausa del monitor.
- [x] 2.4 Tests con driver falso: toma exitosa, `tomado_por_otro`,
  `no_verificado` sin re-clic, botón ausente → `error`, sesión caída → pausa,
  estado ≠ `Nuevo` se ignora, una bandeja caída no frena a las demás.

## 3. Servidor

- [x] 3.1 Hilo monitor daemon: intervalo ~60 s configurable, evalúa franjas,
  salta el ciclo si `current_process` activo, arranca desde `enabled`
  persistido.
- [x] 3.2 Endpoints con token: `GET /api/monitor` (estado + bandejas + franjas
  + últimos leads), `POST /api/monitor/toggle`, `PUT /api/monitor/config`
  (bandejas), `PUT /api/monitor/schedule` (franjas).
- [x] 3.3 `GET /api/events`: SSE con suscriptores en memoria; broadcast de
  eventos del monitor (`taken`, `session_lost`, `paused`) y de fin de runs.
- [x] 3.4 Toast de Windows vía PowerShell nativo (fire-and-forget, solo log en
  fallo), texto genérico sin datos del cliente.
- [x] 3.5 Tests del servidor: endpoints, validaciones 400, SSE emite y tolera
  desconexión, ciclo omitido durante run activo.

## 4. UI: vista "Monitor de Bandeja"

- [x] 4.1 Vista nueva con tabla de leads: fecha creación, campaña, preferencia
  de contacto, propietario, sub-tipo de interés, nombre, apellido, teléfono
  móvil, concesionario, vehículo de interés, correo, Lead ID, otra información;
  columna ausente → "No disponible en bandeja"; nunca mostrar `#` ni
  `Estado de candidato`.
- [x] 4.2 Toggle "Monitor activo" con estado visible (habilitado / pausado +
  motivo).
- [x] 4.3 Selector de bandejas por bandera (AR/CO/MX) con checkbox + campo de
  URL editable y guardado vía `PUT /api/monitor/config`.
- [x] 4.4 Editor de franjas `hh:mm–hh:mm` con agregar/quitar, guardado vía
  `PUT /api/monitor/schedule`.
- [x] 4.5 Cliente `EventSource` a `/api/events`: banner "N lead(s) asignados" +
  beep Web Audio + refresco de la tabla solo al recibir evento.
- [x] 4.6 Reemplazar el polling de ~3 s de estado/resultados por eventos; la
  página no se redibuja en ausencia de novedades.
- [x] 4.7 Tests Node/vm: tabla con columnas, toggle, franjas válidas/invalidas,
  recepción de evento → banner+sonido, sin polling.

## 5. Guardián del servidor

- [x] 5.1 `server_guardian.py`: lanza `ui_server.py` como hijo, sondea
  `GET /status` cada 30 s, reinicia con backoff creciente (0/5/15/30 s …
  máx 5 min), copia la salida de cada caída a `logs/server_crash_<ts>.log` y
  frena tras ≥5 caídas en 10 min con marcador fatal.
- [x] 5.2 Apagado limpio: Ctrl+C del guardián termina también al servidor hijo.
- [x] 5.3 `INICIAR.bat` del paquete lanza el guardián en vez de `ui_server.py`
  directo.
- [x] 5.4 UI: al perder el canal SSE muestra "conexión perdida con el servidor"
  y se recupera sola al reconectar.
- [x] 5.5 Tests: hijo que muere → reinicio + log; hijo colgado (sin respuesta a
  /status) → reinicio; ráfaga de caídas → marcador fatal sin loop.

## 6. Verificación y cierre

- [x] 6.1 Suite completa + Ruff + `harness.py verify`.
- [ ] 6.2 Piloto autorizado: monitor habilitado en 1 bandeja, 1 lead real,
  verificar `Pick Up`, propietario resultante, evento SSE, toast y sonido.
- [ ] 6.3 Piloto del guardián: matar `ui_server.py` a propósito y verificar
  reinicio automático + `server_crash_*.log`.
- [x] 6.4 `graphify update .` al finalizar.
- [ ] 6.5 Versión menor + CHANGELOG + paquete dist con `INICIAR.bat` nuevo;
  commit/tag solo con autorización.
