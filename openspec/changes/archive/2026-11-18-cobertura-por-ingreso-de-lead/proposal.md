## Why

La cobertura de la bandeja se evalúa con la hora en que el ciclo *llega* a
procesar el lead, no con la hora en que el lead **ingresó** a la cola. Dos
fallos de producción en días consecutivos:

- **Bandeja saltada**: el ciclo arrancó dentro de la franja de Colombia
  (09:40–11:00), leer Argentina (51 filas) llevó ~2 min y al llegar a CO el
  bot volvió a mirar el reloj (11:01) — 20 leads ingresados 09:51–10:58
  quedaron `detectado`/`sin_cobertura` y nunca se intentaron.
- **Rezagados perdidos**: un lead que entra minutos antes del cierre
  (ej. 09:59 con franja hasta 10:00) no se vuelve a revisar: el gate del
  monitor pausa los ciclos apenas termina la última franja.
- **Tomas fuera de turno** (el espejo inverso): leads creados antes de que
  abriera la franja vigente fueron tomados apenas abrió — p.ej. QUALIF
  creados 10:xx tomados a las 12:01 con la franja 12:00–13:59, aunque su
  cobertura era de otra franja o de nadie.

La mitad de *asignación* por fecha de creación ya existe (v1.4.3/v1.5.0:
`_encargada_para_lead` elige la persona según la hora de ingreso), pero la
decisión de *tomar* sigue mirando el reloj actual — así que el lead ni
siquiera llega a la toma, o llega tarde y cae en manos equivocadas.

## What Changes

- **Cobertura por lead a su hora de ingreso**: en `run_bandeja_cycle`, la
  decisión de tomar cada lead evalúa la franja vigente **en la
  `fecha_creacion` del lead** (propia o del equipo), no solo "ahora". Leads
  sin fecha usable conservan el comportamiento actual (hora del ciclo).
- **Ventana de gracia post-cierre**: tras el final de una franja, el
  monitor sigue corriendo ciclos durante un intervalo (~`MONITOR_INTERVAL_SECONDS`)
  para re-verificar leads que ingresaron en-franja y quedaron pendientes —
  sin tomar leads creados después del cierre.
- **Regla de negocio completa**: lead ingresado 10:58 en franja 09:00–11:00
  revisado 11:01 → se toma y se asigna a la encargada de las 10:58. Lead
  ingresado 11:02 → no se toma en la gracia de esa franja.
- **Toast de Windows con bandeja**: todas las líneas (tomado, error,
  no verificado, otro propietario, detectado) incluyen la bandeja y su
  bandera (🇦🇷🇨🇴🇲🇽) — hoy solo los "detectado" la llevan.
- **Menor**: `column_offset` en el lector de reportes usa el
  `unassigned_owner` de la bandeja (hoy busca siempre `AR_LEAD_QUALIF`,
  lo que desalinea el detalle de propietario en reportes CO/MX).

## Capabilities

### New Capabilities

### Modified Capabilities

- `monitor-bandeja-leads`: la cobertura de la toma se decide por lead a su
  hora de ingreso (no solo a la hora del ciclo); el monitor corre una
  ventana de gracia post-cierre para rezagados; las notificaciones Windows
  identifican la bandeja en todos los estados.

## Impact

- `automation_salesforce/lead_monitor.py` — `run_bandeja_cycle`: cobertura
  por lead con `fecha_creacion` (`_usable_entry_moment`/`_lead_entry_moment`
  ya existen para la asignación).
- `automation_salesforce/ui_server.py` — `_any_turno_activo`/`_monitor_cycle`:
  gate del ciclo con ventana de gracia; `_lead_toast_lines`: bandeja+bandera
  en todas las líneas.
- `automation_salesforce/monitor_store.py` — helpers de franja/gracia si
  hace falta extender `within_schedule`.
- `automation_salesforce/report_reader.py` — `column_offset` con owner de
  la bandeja.
- Tests: `test_lead_monitor.py`, `test_monitor_store.py`, `test_ui_server.py`
  (nuevos casos determinísticos, sin navegador).
- Sin cambios de formato de cola/resultados ni de la mecánica de toma
  (Pick Up, modal, reasignación) — solo *cuándo* se intenta y *cómo* se
  notifica.
