## Context

`run_bandeja_cycle` evalúa `covered` una sola vez por bandeja con
`datetime.now()` y descarta el lead sin llegar a `take_lead`. Dos mitades
del problema ya existen sueltas:

- `_lead_entry_moment`/`_usable_entry_moment` ya parsean `fecha_creacion`
  del reporte y deciden la **asignación** (`_encargada_para_lead`) a la
  hora de ingreso — v1.4.3/v1.5.0.
- `_any_turno_activo` (ui_server) decide si el tick corre un ciclo:
  sin franja vigente que cubra bandeja habilitada → pausa.

Falta la pieza central: usar la hora de ingreso también para la **toma**,
y mantener el ciclo vivo un tramo tras el cierre para los rezagados.

Evidencia de producción: diagnóstico del 17/11 (20 leads CO `sin_cobertura`
a las 11:01:50, todos ingresados en-franja 09:51–10:58) y tomas del 18/11
(leads creados antes de las 12:00 tomados al abrir la franja 12:00–13:59).

## Goals / Non-Goals

**Goals:**

- Cobertura por lead a `fecha_creacion` (propia o equipo), con fallback a
  la hora del ciclo cuando la fecha no es usable.
- Ventana de gracia post-cierre que deja correr ~1 ciclo extra para
  recuperar rezagados ingresados en-franja.
- Toasts con bandeja+bandera en todos los estados.
- `column_offset` alinea con el `unassigned_owner` de la bandeja.

**Non-Goals:**

- No se toca la mecánica de toma: Pick Up, modal "Cambiar propietario",
  verificación, panel, comentarios, WhatsApp.
- No cambian formatos de cola/resultados/snapshot ni la UI.
- No se reordena el procesamiento de bandejas ni se paraleliza.
- No se afirma verificación en Salesforce real — solo tests determinísticos.

## Decisions

### D1: Cobertura por lead, no por bandeja

`covered` pasa de booleano del ciclo a función `coverage_at(moment)`:
para cada lead, si `fecha_creacion` es usable se evalúa la franja vigente
**en ese instante** (misma lógica de franja-propia/equipo/por-bandeja que
hoy); si no, se evalúa "ahora". Un lead ingresado antes de la franja actual
queda `sin_cobertura` — no se toma aunque el ciclo corra en franja.

- Alternativa descartada: congelar la hora del ciclo al arranque. No
  resuelve el caso de producción (ciclo que arranca 11:02 seguiría sin
  tomar el lead de 10:58) y asignaría cobertura muerta a leads creados
  después del cierre.

### D2: Gracia = un intervalo de monitor tras el fin de franja

`GRACE_SECONDS = MONITOR_INTERVAL_SECONDS` (~120s): el gate
`_any_turno_activo` devuelve `True` también si **alguna franja que cubre
bandeja habilitada terminó hace menos de GRACE**. Fuera de la gracia el
monitor pausa igual que hoy.

- La gracia no puede tomar leads post-cierre: REQ-817 ya descarta todo lead
  cuyo ingreso cae fuera de franja. La gracia solo da *una chance más* de
  lectura a los ingresados en-franja.
- Solo cuenta el cierre de franjas que cubren bandejas habilitadas (igual
  que el gate actual), para no sostener ciclos por franjas ajenas.
- Alternativa descartada: gracia configurable por bandeja/franja — más
  superficie de config sin necesidad demostrada; un intervalo de monitor
  cubre el caso real (lead 09:59 leído a las 10:02).

### D3: Mismo chequeo de franja para cobertura y gracia

Tanto "¿hay franja vigente ahora?" como "¿hubo franja vigente a
`fecha_creacion`?" como "¿terminó una franja hace < GRACE?" usan
`within_schedule` con los mismos filtros por bandeja — una sola semántica
de franja (minutos inclusivos, wrap de medianoche igual que hoy).

### D4: Bandeja+bandera en todas las líneas del toast

`_lead_toast_lines` anteponen `🇦🇷 AR` / `🇨🇴 CO` / `🇲🇽 MX` a cada línea
(los "detectado" ya nombraban la cola; se unifica el formato). El toast de
Windows no admite color de texto — la bandera es el indicador de país
pedido.

### D5: `column_offset` recibe el owner de la bandeja

La detección de columna-propietario pasa el `unassigned_owner` de la
bandeja en curso a `is_unassigned_owner` en lugar del default AR.

## Risks / Trade-offs

- **`fecha_creacion` no parseable o de otro día** → el lead cae al
  comportamiento actual; mismo fallback que ya usa la asignación.
- **Gracia agrega 1 lectura extra de reportes por cierre de franja** →
  costo acotado (un ciclo), beneficio: recupera rezagados sin re-verificación
  manual.
- **Lead ingresado dentro de la gracia (10:01, franja cerrada 10:00)** →
  sin cobertura a su ingreso → no se toma. Es la regla pedida: "después del
  cierre no corresponde a la franja muerta".
- **`within_schedule` inclusivo en el minuto de cierre** → un lead creado
  10:00 en franja "hasta 10:00" cuenta en-franja (consistente con la
  semántica vigente de franjas, ej. fin 13:59).
