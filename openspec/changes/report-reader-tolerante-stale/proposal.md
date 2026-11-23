# report-reader-tolerante-stale

## Why

Con Edge/EdgeDriver 158 el scan de la bandeja del reporte emite
`bandeja_error: StaleElementReferenceException`: las filas se devuelven
como `WebElement` y mueren durante el marshaling/lectura entre llamadas.
Es la misma regresión que ya se resolvió en la edición inline; queda el
lector del reporte como superficie expuesta.

## What Changes

- `report_reader.py`: la extracción de datos de la fila se hace dentro de
  la evaluación JS (texto/ids/atributos salen ya materializados) en vez de
  devolver handles que luego se leen en llamadas separadas.
- Reintento acotado del scan cuando una fila o el frame muere a mitad de
  lectura, con conteo de reintentos visible en el estado del monitor.
- `comment_reader`/helpers: extender la tolerancia a stale en
  `execute_in_any_frame`/`find_*_in_any_frame` a las rutas del lector que
  aún no la cubren.
- Diagnóstico: `bandeja_error` registra la excepción con contexto
  (bandeja, intento, tipo) para distinguir stale transitorio de fallo real.

## Capabilities

### New Capabilities
- `lectura-reporte-tolerante-stale`: lectura de filas del reporte de
  Salesforce inmune a la regresión de handles stale de Edge 158, con
  reintento acotado y error contextualizado.

### Modified Capabilities
- `monitor-bandeja-leads`: el scan de la bandeja no puede abortar el ciclo
  por una excepción de serialización/lectura stale — se reintenta y, si se
  agota, marca `bandeja_error` con contexto sin tumbar el monitor.

## Impact

- Código: `automation_salesforce/report_reader.py`,
  `automation_salesforce/comment_reader.py` (helpers),
  `automation_salesforce/lead_monitor.py` (registro del error con
  contexto), tests del lector/monitor.
- Sin cambios en formatos de cola ni en la mecánica de toma/reasignación.
- Mitigación de `bandeja_error` y de tomas abortadas (`-> error`) cuando
  el DOM de Lightning re-renderiza.
