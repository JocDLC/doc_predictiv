## 1. Clasificador de apertura (REQ-830)

- [x] 1.1 Tests: `apertura.classify_lead` — nocturno → `no_habil_elegible`; sábado con franja → `turno_personal`; fuera de rango; fecha ilegible → `revision`; `tz_offset` desplaza la hora (AR+2, MX-1); lead de ayer se clasifica por su hora igual que uno de hoy
- [x] 1.2 `automation_salesforce/apertura.py`: `classify_lead` pura (sin Selenium), `parse_apertura_range` validando `desde < hasta` y `hasta` no futuro, conversión de `fecha_creacion` con `tz_offset` de la bandeja

## 2. Cobertura del monitor sin fallback (REQ-817 modificado)

- [x] 2.1 Tests: lead nocturno (ayer 23:30) con ciclo en franja → `detectado` sin_cobertura, no se toma; lead de ayer en-franja → se toma con su franja; fecha ilegible → listado, no se toma
- [x] 2.2 `lead_monitor.py`: `_lead_covered`/`_equipo_para_lead`/`_encargada_para_lead` dejan de usar `_usable_entry_moment` (hoy) y pasan a evaluar la hora de creación día-agnóstica via `apertura.classify_lead`; sin fallback a hora del ciclo
- [x] 2.3 Suite `tests.test_lead_monitor` en verde con los casos 2.1

## 3. Almacén de apertura (REQ-834)

- [x] 3.1 Tests: persistir lote, éxito parcial, `en_curso`→`tomado_confirmado`, reinicio deja `revisar`, consumidos no se re-ofrecen
- [x] 3.2 `automation_salesforce/apertura_store.py`: JSONL por lote en `ui_output/`, escritura atómica por lead, consulta de disponibles por bandeja

## 4. Endpoints de apertura (REQ-831/832/833)

- [x] 4.1 Tests: `POST /api/apertura/preview` — rango válido lista clasificados sin tocar driver ni colas; rango inválido → 400; sin token → 403; lectura fallida no muestra "cero pendientes"
- [x] 4.2 `ui_server.py`: preview que usa `read_bandeja_leads` + `classify_lead` dentro de `cycle_lock` (lectura también exclusiva); devuelve candidatos, exclusiones con motivo y preview_id ligado a sesión/bandeja/rango
- [x] 4.3 Tests: `POST /api/apertura/confirm` — acepta solo IDs elegibles del preview; rechaza IDs ajenos y concurrencia; antes del clic re-verifica cola QUALIF; dueño cambiado → `tomado_por_otro`
- [x] 4.4 `ui_server.py` + `lead_monitor.py`: confirmación bajo `cycle_lock` con `monitor_cycle_active`, take a nombre del usuario de sesión (sin equipo ni WhatsApp), persistencia por lead vía `apertura_store`
- [x] 4.5 `GET /api/apertura/disponibles`: lotes con `tomado_confirmado` no consumidos por bandeja

## 5. UI de apertura en la vista Monitor (REQ-831/832/833)

- [x] 5.1 Botón "Recoger QUALIF fuera de horario" → formulario bandeja + Desde/Hasta `datetime-local` con zona mostrada por bandeja
- [x] 5.2 Vista previa con selección por checkbox (cada fila muestra Lead ID, nombre, fecha de creación), resumen de excluidos con motivo; solo `no_habil_elegible` seleccionables
- [x] 5.3 Confirmación explícita con cantidad → POST confirm → resumen de resultados por estado

## 6. Fuente apertura en Distribuir leads

- [x] 6.1 Tests: mezcla por `lead_id` — duplicado archivo+apertura una sola fila con destino del archivo; nombres iguales IDs distintos → dos filas; agregar no consume; sin archivo también funciona
- [x] 6.2 `documentador_predictivo.html`: "Agregar QUALIF de apertura" lista lotes no consumidos, filas marcadas con origen, aplicación de reparto por ID (no posición) en `calcularReparto`
- [x] 6.3 Marcar consumidos al congelar la cola con `reasignado`/`ya_asignado` confirmados por `run_id`; `restoreDistribucionRun` no pisa el borrador

## 7. Verificación y cierre

- [x] 7.1 `python harness.py unit` + `lint` + `format-check` en verde desde `automation_salesforce/`
- [x] 7.2 `openspec validate --changes` OK; `graphify update .`
- [x] 7.3 CHANGELOG `[Sin publicar]` + log Gantt `wv-asignacion`
- [ ] 7.4 Confirmar `tz_offset` real de CO y MX con el usuario (lead de hora conocida por reporte) antes de uso productivo
