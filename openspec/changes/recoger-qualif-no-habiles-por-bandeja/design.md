## Context

El monitor toma leads según cobertura por franja (REQ-817/818): la franja de la
hora de creación decide el titular. Lo que nadie cubre —leads nocturnos, de fin
de semana o feriado— hoy cae al fallback "hora del ciclo" cuando la fecha no es
usable, o queda `detectado` sin un camino de toma: el operador termina
asignando a mano.

Se suma una tercera operación junto a *monitor por turno* y *Distribuir leads*:
**recogida de apertura**, una toma de custodia explícita y manual por bandeja
y rango, cuyos éxitos alimentan la vista de distribución.

Piezas reutilizables ya existentes: `tz_offset` por bandeja
(`monitor_store.validate_bandeja`, hoy usado para documentar intentos),
`read_bandeja_leads`/`take_lead`/`_lead_covered` (`lead_monitor.py`),
`cycle_lock`/`monitor_cycle_active` (`ui_server.py`), la cola validada
`{lead_id, persona}` (`distribucion_loader.validate_distribucion_queue`) y la
mezcla de la vista (`documentador_predictivo.html`).

Las franjas son `HH:MM` sin día de semana ni vigencia: cubren la misma hora
todos los días. La `fecha_creacion` del reporte se muestra en la zona local de
cada país (AR confirmada; CO/MX se fijan con `tz_offset` en el panel de la
bandeja, campo ya existente).

## Goals / Non-Goals

**Goals:**
- El monitor normal solo toma leads cuya hora de creación cae en una franja de
  su bandeja; los nocturnos y los de fecha ilegible nunca se toman por ciclo.
- El operador puede previsualizar y recoger QUALIF de un rango manual
  (`[desde, hasta)`) por bandeja, con exclusión total respecto del monitor y
  comprobante persistente por lead.
- Distribuir leads acepta esos QUALIF como fuente opcional mezclada con el
  archivo por `Lead ID`, sin duplicar ni pisar destinos.

**Non-Goals:**
- Calendario laboral automático, feriados o plantillas recurrentes (rango
  manual por uso — decisión del usuario).
- Coordinación de tomas entre PCs distintos (la exclusión es local al
  servidor; las carreras externas se detectan releyendo el propietario).
- Cambios en mecánica Salesforce (se reusan las primitivas de `take_lead`),
  en el runner ni en el formato de cola de distribución.
- Reasignación ni WhatsApp dentro de la apertura (custodia = usuario logueado).

## Decisions

**1. Clasificador puro en módulo propio (`apertura.py`).**
Función `classify_lead(bandeja, franjas_propias+equipo, details, rango, now)` →
`turno_personal | no_habil_elegible | habil_sin_cobertura | fuera_de_rango |
revision`. Compara la hora de creación (convertida por `tz_offset`) contra las
franjas de la bandeja — día-agnóstica, igual que `within_schedule`. Por qué
así: el período es manual, no hay calendario que invocar; y la misma función
alimenta preview y monitor normal, eliminando dobles interpretaciones.

**2. El fallback de fecha desaparece, no se reconfigura.**
`_usable_entry_moment` dejaba todo lo no-de-hoy en "ahora". Con la
clasificación por hora, un lead de ayer a las 15:00 es `turno_personal` (su
franja lo cubre igual) y uno de las 23:30 es `no_habil`. La fecha ilegible va a
`revision` listada, nunca se toma. Riesgo aceptado: un `fecha_creacion` que
falle deja leads sin tomar hasta revisión — preferible a tomar leads ajenos.

**3. Persistencia en almacén nuevo (`apertura_store.py`), no en
`monitor_state.results`.** El historial del monitor se puede vaciar con un
botón; el comprobante de apertura debe sobrevivirlo. JSONL por lote con
estado `en_curso` antes del clic → `tomado_confirmado` | `revisar` | error,
escritura atómica por lead y reconciliación tras reinicio leyendo el
propietario real.

**4. Exclusión por `cycle_lock` extendida, no lock nuevo.** La confirmación
corre dentro del mismo lock que `monitor_tick`/`start_manual_check` y marca
`monitor_cycle_active`; el gate existente (`PAUSE_RUN_ACTIVO`) ya bloquea los
otros runners. Alternativa descartada: lock por bandeja — complejidad sin
ganancia, el navegador es uno solo.

**5. Identidad = Lead ID tal cual (15 u 18 chars).** Las colas y el reporte
ya emiten el ID completo validado por `SALESFORCE_ID_PATTERN`. La mezcla usa
`lead_id` normalizado (trim + match exacto; el mismo registro nunca llega con
formatos distintos en una misma sesión). No se introduce canonicalización
15↔18: los reportes de la app entregan el ID de un solo formato por bandeja.
Si aparecieran mezclados, la duplicidad se muestra como dos filas revisables
— peor caso benigno.

**6. UI mínima en la vista Monitor + fila de origen en Distribuir.** Botón
"Recoger QUALIF fuera de horario" → formulario bandeja + Desde/Hasta
(datetime-local) → preview con selección por checkbox → confirmación con
cantidad. En Distribuir, "Agregar QUALIF de apertura" lista lotes no consumidos
con checkbox por lead; la fila resultante lleva marca de origen `apertura`.

## Risks / Trade-offs

- [Franjas editadas cambian la clasificación retroactivamente] → Una franja
  creada hoy cubre sábados pasados; el preview muestra los excluidos con
  motivo `turno_personal` para revisión del operador (rango manual → revisión
  humana siempre previa). Sin vigencia por fecha en v1.
- [tz_offset mal configurado clasifica mal] → El campo ya existe y se valida
  (-12..+12); la preview etiqueta la zona usada por bandeja. El usuario
  confirmó AR y debe fijar CO/MX al configurar la recogida.
- [Ciclo colgado sostiene el lock y la apertura espera] → `cycle_lock` ya
  serializa; la confirmación muestra "ocupado" si hay ciclo corriendo. El
  hang de Edge es un problema aparte (watchdog pendiente).
- [Un lead tomado en apertura vuelve a aparecer en el reporte QUALIF] → El
  cambio de propietario lo saca del reporte; y `apertura_store` lo marca
  consumido para no re-ofrecerlo.
- [Duplicado 15/18 entre fuentes → dos filas] → Benigno y revisable; si se
  confirma que el feed mezcla formatos se evalúa canonicalización.

## Migration Plan

Sin migración de datos. `tz_offset` ya persiste por bandeja (defaults AR:+2,
CO:0, MX:-1); se le da uso adicional en el panel sin cambiar su formato. La
apertura es opt-in por uso: sin intervención del operador no toma nada.

## Open Questions

- Valores exactos de `tz_offset` que reportan CO y MX en la práctica (el
  usuario confirma viendo un lead de hora conocida en cada reporte).
- ¿La vista previa debe poder incluir leads `revision` para toma manual
  asistida, o solo listarlos? En v1: solo listarlos.
