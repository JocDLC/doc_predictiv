## 1. Cobertura por hora de ingreso (REQ-817)

- [x] 1.1 Tests: lead ingresado en-franja revisado post-cierre se toma (10:58 → revisado 11:01); lead ingresado pre-franja no se toma aunque el ciclo corra en franja (10:30 → revisado 12:01); lead sin fecha usable cae al comportamiento actual
- [x] 1.2 `run_bandeja_cycle`: `covered` pasa a evaluación por lead con `_usable_entry_moment`/`_lead_entry_moment` (misma semántica de franja propia/equipo/por-bandeja; fallback hora del ciclo)

## 2. Ventana de gracia post-cierre (REQ-818)

- [x] 2.1 Tests: gate activo durante ~`MONITOR_INTERVAL_SECONDS` tras el cierre de franja de bandeja habilitada; pausa vuelve tras la gracia; lead 09:59 con franja hasta 10:00 se recupera en ciclo 10:02; lead 10:03 no se toma en gracia
- [x] 2.2 `_any_turno_activo`/helpers de franja: devuelve activo si una franja que cubre bandeja habilitada terminó hace menos de `GRACE_SECONDS`

## 3. Toasts con bandeja (REQ-819)

- [x] 3.1 Tests: cada línea de estado (tomado/error/no verificado/otro propietario/detectado) incluye bandera+código de bandeja
- [x] 3.2 `_lead_toast_lines`: prefijo `🇦🇷 AR` / `🇨🇴 CO` / `🇲🇽 MX` en todas las líneas

## 4. Owner de cola por bandeja (REQ-820)

- [x] 4.1 Test: reporte CO sin columna de propietario mapeada → detalle muestra `CO_LEAD_QUALIF`
- [x] 4.2 `column_offset`/`is_unassigned_owner`: usar el `unassigned_owner` de la bandeja en curso

## 5. Verificación

- [x] 5.1 Suite completa + ruff en verde
- [x] 5.2 `openspec validate --changes` OK; `graphify update .`
- [x] 5.3 Entrada en CHANGELOG `[Sin publicar]` + `log` en Gantt (`wv-asignacion`)
