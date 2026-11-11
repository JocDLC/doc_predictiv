## Why

El Monitor de Bandeja puede ver una fila cuyo propietario es la cola QUALIF y,
sin embargo, descartarla porque Salesforce Lightning virtualiza horizontalmente
las columnas: el propietario queda en un fragmento renderizado y el enlace o
Lead ID queda en otro. El incidente se reprodujo en una bandeja Argentina ancha
y es más probable en notebooks con viewport reducido o escalado de Windows.

## What Changes

- Incorporar una lectura horizontal segura de reportes Lightning virtualizados
  para el Monitor de Bandeja.
- Extraer el Lead ID desde enlaces, atributos estructurales de la fila y sus
  descendientes, o la columna visible `Lead ID`.
- Unir fragmentos horizontales solamente cuando exista una identidad de fila
  estable; ante ambigüedad, omitir la toma y fallar de forma segura.
- Exponer diagnóstico estructural sin PII: filas QUALIF sin ID, pasadas
  horizontales y ancho del viewport.
- Ajustar el tamaño de la ventana del monitor como mitigación complementaria,
  sin convertir el ancho de pantalla en requisito de funcionamiento.
- Añadir regresiones determinísticas para reportes AR anchos y preservar el
  comportamiento vigente de CO y MX.
- Liberar el arreglo como parche `1.5.1` en un ZIP reproducible después de que
  el harness completo y un piloto controlado pasen.

## Capabilities

### New Capabilities

- `lectura-reportes-virtualizados`: lectura segura de filas distribuidas entre
  varios fragmentos horizontales de una grilla Lightning, con identidad estable,
  extracción robusta de Lead ID y observabilidad sin datos personales.

### Modified Capabilities

Ninguna. El repositorio aún no tiene una especificación principal del Monitor
de Bandeja sincronizada en `openspec/specs/`; este cambio introduce un contrato
independiente y reutilizable para el lector de reportes.

## Impact

- Código: `automation_salesforce/report_reader.py`,
  `automation_salesforce/lead_monitor.py` y `automation_salesforce/ui_server.py`.
- Pruebas: `test_report_reader.py`, `test_lead_monitor.py` y
  `test_ui_server.py`.
- Empaquetado: `documentador_predictivo.html`, `CHANGELOG.md` y
  `packaging/build_zip.py` para producir `DocumentadorPredictivo_v1.5.1.zip`.
- Salesforce: no cambia Pick Up, reasignación, horarios ni configuración de
  bandejas; solo cambia la lectura previa a cualquier escritura.
- Dependencias y contratos externos: sin dependencias nuevas y sin cambios de
  API pública ni del formato persistido de `monitor_state.json`.
