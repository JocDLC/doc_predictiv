# Tasks: tomar-leads-selectivo

> Mismas reglas que el monitor: ninguna escritura sin re-verificar el
> propietario; `tomado` exige observar el cambio; nunca repetir Pick Up a
> ciegas; sin datos de clientes en logs/tests/chat.

## 1. Lectura bajo demanda de la bandeja (scan)

- [ ] 1.1 `lead_monitor.py`: `run_scan(driver, config, state)` — para cada
  bandeja habilitada, `read_visible_unassigned_leads` con su
  `unassigned_owner`/`field_aliases`; cada lead QUALIF + `expected_status`
  se registra `detectado` (sin abrir el registro). Reutiliza la rama
  `solo_listar` del ciclo.
- [ ] 1.2 `ui_server.py`: `POST /api/monitor/scan` — adquiere `cycle_lock`
  sin bloquear (`409` si ocupado), corre `run_scan` en hilo daemon con
  `monitor_cycle_active` + eventos `cycle_start`/`cycle_end`.
- [ ] 1.3 Tests: scan registra `detectado` sin llamar al flujo de toma;
  `409` con ciclo en curso; `409` si hay run de documentación activo;
  bandeja sin habilitar se omite.

## 2. Toma selectiva (take)

- [ ] 2.1 `lead_monitor.py`: `take_leads(driver, config, state, lead_ids)` —
  por cada id válido: `build_record_url` → abrir → releer propietario →
  si ya no es la cola `tomado_por_otro` → Pick Up → verificar → `tomado` /
  `no_verificado` / `error`. Actualiza el `results` del estado.
- [ ] 2.2 `ui_server.py`: `POST /api/monitor/take` — body `{"lead_ids": []}`
  validado (patrón Salesforce, no vacío, máx. razonable); mismo lock y
  exclusión mutua; `400` con body inválido.
- [ ] 2.3 Tests con driver falso: toma exitosa, `tomado_por_otro`,
  `no_verificado`, ids inválidos → `400`, `409` con ciclo/run activo,
  estado `detectado` pasa a `tomado`.

## 3. UI: lista completa + selección

- [ ] 3.1 Botón "Ver bandeja ahora" → `POST /api/monitor/scan`; estado
  "leyendo bandejas…" mientras corre; la tabla muestra los `detectado`.
- [ ] 3.2 Checkbox por fila en leads `detectado`/`error` + botón "Tomar"
  por fila + botón "Tomar seleccionados"; al responder `202` las filas se
  marcan "tomando…" hasta el `cycle_end`.
- [ ] 3.3 Resaltar `Preferred mean of contact` (whatsapp / llamada) en la
  columna correspondiente.
- [ ] 3.4 Tests Node/vm: botones visibles, selección arma el body
  `lead_ids`, `Preferred mean of contact` resaltado, `409` muestra mensaje.

## 4. Limpieza de la lista del monitor

- [x] 4.1 `monitor_store.py`: operación pura que vacía únicamente
  `results` y conserva el resto del estado; tests de preservación.
- [x] 4.2 `ui_server.py`: `POST /api/monitor/clear-results` autenticado,
  serializado con `cycle_lock`, `409` durante un ciclo y evento SSE al
  completar; tests del endpoint.
- [x] 4.3 UI: botón "Limpiar lista" con confirmación, advertencia de posible
  repoblación, refresco inmediato y mensaje claro ante `409`; tests Node/vm.
- [x] 4.4 Vaciar la lista persistida actual mediante la operación implementada,
  preservando toggle, modo prueba, bandejas y horarios.

## 5. Verificación

- [ ] 5.1 Suite completa + Ruff limpio + `openspec validate --changes`.
- [ ] 5.2 Piloto real: "Ver bandeja ahora" lista los QUALIF acumulados;
  tomar uno con "Tomar" lo asigna al usuario logueado y queda `tomado`.
- [x] 5.3 Sincronizar `dist/`, reiniciar servidor, `graphify update .`.
