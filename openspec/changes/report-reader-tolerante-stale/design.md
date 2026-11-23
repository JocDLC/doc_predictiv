# Diseño: report-reader-tolerante-stale

## Context

Edge/EdgeDriver 158 dejó stale los `WebElement` devueltos por JS entre
llamadas — el mismo bug resuelto en la edición inline y en los helpers de
frames. El scan del reporte (`report_reader`) sigue trayendo handles de
filas y leyéndolos en llamadas separadas → `bandeja_error:
StaleElementReferenceException`. El scan también puede abortar tomas
(`-> error`) cuando la excepción sube desde lecturas auxiliares.

## Goals / Non-Goals

**Goals:**
- El scan del reporte no exporta handles: los datos salen materializados.
- Reintento acotado con contexto en `bandeja_error`.
- Ninguna excepción de lectura tumba el ciclo del monitor.

**Non-Goals:**
- No se cambia la lógica de cobertura/franjas ni la mecánica de toma.
- No se toca la escritura/documentación (ya atómica).
- No se agregan endpoints ni formatos nuevos.

## Decisions

1. **Materializar dentro del JS**, igual que el patrón ya validado para el
   lápiz/editor/Guardar: una evaluación devuelve
   `{nombre, lead_id, fecha_creacion, ...}` por fila; Python nunca recibe
   el `WebElement`. Alternativa: re-leer el handle con try/except por
   campo — rechazada, sigue siendo una carrera por llamada.
2. **Reintento acotado (2-3) con pequeña espera** ante stale, no re-render
   infinito: Lightning asienta el DOM; si persiste, es un fallo real.
3. **`bandeja_error` estructurado** (bandeja, excepción, intentos) en vez
   del string plano actual — mejora el diagnóstico sin romper el contrato
   del estado (el campo ya existe).
4. **Reusar los helpers tolerantes** ya agregados en `comment_reader` para
   las lecturas auxiliares del scan.

## Risks / Trade-offs

- [Materializar todo en JS complica el script] → ya hay scripts de scroll/
  extracción extensos en `report_reader`; se mantiene el mismo estilo.
- [Reintentos suman latencia al ciclo] → acotados y solo ante fallo; el
  camino feliz no cambia.
- [El DOM del reporte es virtualizado (filas recicladas)] → la extracción
  materializada es justamente la defensa: se lee lo que está visible en la
  evaluación, no una referencia que puede ser reutilizada.

## Migration Plan

Aditivo: cambio interno del lector + reintentos. `bandeja_error` gana
contexto pero sigue siendo un campo del estado. Rollback = revert.
