# Diseño: tomar-leads-selectivo

## Arquitectura

```
UI (Monitor de Bandeja)                    ui_server.py                 lead_monitor.py
─────────────────────                      ─────────────                ───────────────
[Ver bandeja ahora] ──POST /api/monitor/scan──▶ hilo con cycle_lock ──▶ run_scan()
                                              (mismo lock que los        lee bandejas
                                               ciclos: nunca dos           sin tocar leads
                                               a la vez)                   → results detectado
[Tomar / Tomar sel.] ──POST /api/monitor/take──▶ hilo con cycle_lock ──▶ take_leads(ids)
   {lead_ids:[...]}                            force=True                por cada lead:
                                                                        abrir registro
                                                                        verificar cola
                                                                        Pick Up
                                                                        verificar owner
                                                                        actualizar estado
```

## Decisiones

### Un solo candado para todo lo que toca el navegador

`cycle_lock` ya garantiza que nunca hay dos ciclos simultáneos. `scan` y
`take` usan el mismo lock con el patrón de `start_manual_check`: adquieren
sin bloquear → `409` si está ocupado. La exclusión mutua con los bots de
documentación/cierre se hereda gratis: `monitor_cycle_active` se pone en
`True` durante scan/take, y `/run`/`/run-close` responden `409`.

### scan ≠ take

- `scan` (`POST /api/monitor/scan`): recorre las bandejas habilitadas en
  modo solo-lectura y registra cada lead QUALIF/Nuevo como `detectado`
  (estado reprocesable ya existente). Es la respuesta a "quiero ver los
  QUALIF acumulados": no depende del historial del monitor, lee la bandeja
  real en el momento.
- `take` (`POST /api/monitor/take`): recibe `lead_ids` explícitos. Por cada
  uno abre el registro y aplica el flujo ya probado (verificar propietario
  = cola → Pick Up → verificar cambio). Resultados: `tomado`,
  `tomado_por_otro`, `no_verificado`, `error`.

`take` no re-lee la bandeja: la selección viene de la tabla, y la
re-verificación del propietario dentro del registro es el candado real —
si otro auxiliar lo tomó entre la lista y el clic, se marca
`tomado_por_otro` sin tocar nada.

### Ventana dedicada

Ambos corren bajo `ensure_monitor_window`: la navegación ocurre en la
ventana del monitor, no en las pestañas del usuario.

### UI

- Botón **"Ver bandeja ahora"** junto a "Revisar ahora": dispara `scan` y
  deja la tabla con todos los `detectado` del momento.
- Columna de checkbox + botón "Tomar" por fila en leads con estado
  `detectado`/`error` (reprocesables); "Tomar seleccionados" deshabilitado
  sin selección.
- `Preferred mean of contact` ya es una de las 13 columnas; se resalta
  cuando indica WhatsApp/llamada para guiar el contacto posterior.

### Limpieza del historial local

El botón **"Limpiar lista"** invoca `POST /api/monitor/clear-results` después
de una confirmación explícita. El endpoint exige token, intenta adquirir
`cycle_lock` sin bloquear y responde `409` si una revisión está en curso,
evitando que un ciclo vuelva a escribir resultados antiguos después del
borrado. Bajo el lock carga el estado, vacía únicamente `results`, conserva
`enabled`, `solo_listar`, `bandejas`, `schedule`, `last_cycle_at` y
`paused_reason`, persiste y emite un evento SSE para refrescar las vistas.

La limpieza no navega Salesforce ni altera Leads. Si el monitor continúa
activo, una revisión posterior puede volver a listar los QUALIF que sigan
presentes; la confirmación de UI lo advierte.

## Riesgos

- **Doble clic / carrera con otro auxiliar**: mitigado por la
  re-verificación del propietario dentro del registro (igual que el ciclo
  automático).
- **Selección stale**: la fila pudo ser tomada por otro; `tomado_por_otro`
  lo reporta sin acción destructiva.
- **Sesión caída**: se detecta como en el ciclo (`session_lost`), pausa y
  avisa.
