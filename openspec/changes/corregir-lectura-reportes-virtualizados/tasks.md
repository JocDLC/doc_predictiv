## 1. Línea base y pruebas RED

- [x] 1.1 Ejecutar y registrar la línea base del lector y Monitor antes del cambio: `python -m unittest tests.test_report_reader tests.test_lead_monitor tests.test_ui_server -v` desde `automation_salesforce`. Resultado: 226 pruebas OK.
- [x] 1.2 Añadir pruebas RED para extraer Lead ID desde atributos de descendientes y rechazar rutas/IDs de otro objeto; verificar con `python harness.py tdd-red tests.test_report_reader.ReportReaderTests.test_extract_lead_id_reads_descendant_record_attributes`.
- [x] 1.3 Añadir una prueba RED de grilla virtualizada donde propietario e ID aparecen en pasadas horizontales distintas con la misma clave estable; verificar con `python harness.py tdd-red tests.test_report_reader.ReportReaderTests.test_horizontal_scan_merges_stable_row_fragments`.
- [x] 1.4 Añadir regresiones RED de seguridad para clave ausente, duplicada y secuencia cambiante; ninguna puede producir un `VisibleLead`. Verificar con `python -m unittest tests.test_report_reader -v` y confirmar fallos por aserción del comportamiento faltante. Resultado RED: 5 fallos de aserción esperados, sin errores.

## 2. Captura e identidad de fragmentos

- [x] 2.1 Implementar en `report_reader.py` la representación interna y las funciones puras para capturar fragmentos sin PII, resolver su clave estructural y validar unicidad/estabilidad entre pasadas.
- [x] 2.2 Ampliar `extract_lead_id` para inspeccionar enlaces y atributos estructurales en fila y descendientes, conservando validación de objeto y longitud 15/18.
- [x] 2.3 Implementar la unión de fragmentos por clave estable, combinando detalles visibles y fallando cerrado ante ausencia, duplicidad o cambio de secuencia.
- [x] 2.4 Ejecutar las pruebas del lector hasta GREEN: `python -m unittest tests.test_report_reader -v`.

## 3. Barrido horizontal del Monitor

- [x] 3.1 Incorporar un lector horizontal acotado: reset a la izquierda, hasta 20 pasadas, espera de re-render, corte al extremo y sin scroll vertical.
- [x] 3.2 Cambiar `lead_monitor.read_bandeja_leads` para usar el lector horizontal seguro sin alterar las reglas de estado, cobertura, Pick Up ni reasignación.
- [x] 3.3 Añadir pruebas de Monitor para AR fragmentada, CO/MX en una sola vista y continuidad de otra bandeja cuando una queda irresoluble.
- [x] 3.4 Verificar la integración local: `python -m unittest tests.test_report_reader tests.test_lead_monitor -v`.

## 4. Observabilidad y ventana dedicada

- [x] 4.1 Agregar a `bandeja_scan` los metadatos `horizontal_passes`, `viewport_width`, `owner_without_id` y `unstable_or_ambiguous_rows`.
- [x] 4.2 Actualizar el log de `ui_server.py` para distinguir bandeja vacía de QUALIF sin identidad, sin registrar valores de celdas ni Lead IDs completos.
- [x] 4.3 Añadir pruebas de privacidad y formato del evento/log; verificar con `python -m unittest tests.test_lead_monitor tests.test_ui_server -v`.
- [x] 4.4 Hacer best-effort el ancho adaptativo de la ventana dedicada, manteniendo 1150x760 como fallback y sin maximizar/minimizar ni recuperar foco innecesariamente.
- [x] 4.5 Añadir pruebas del ajuste de ventana disponible/rechazado; verificar con `python -m unittest tests.test_ui_server -v`.

## 5. Harness y validación determinística

- [x] 5.1 Ejecutar formato, lint y compilación: `python automation_salesforce/harness.py format-check`, `python automation_salesforce/harness.py lint` y `python automation_salesforce/harness.py compile`.
- [x] 5.2 Ejecutar la suite completa y cobertura: `python automation_salesforce/harness.py test` y `python automation_salesforce/harness.py coverage`.
- [x] 5.3 Ejecutar el harness integral: `python automation_salesforce/harness.py verify`.
- [x] 5.4 Validar los artefactos SDD: `openspec validate --changes`.

## 6. Piloto y liberación 1.5.1

- [ ] 6.1 Ejecutar un piloto autorizado en modo prueba sobre notebook de 13 pulgadas con AR y CO habilitadas; comprobar detección, conteos de diagnóstico, ausencia de filas ambiguas y cero escrituras en Salesforce.
- [ ] 6.2 Ejecutar un piloto autorizado con un único Lead real: verificar identidad, Pick Up, propietario final y continuidad de la segunda bandeja.
- [x] 6.3 Cambiar `APP_VERSION` a `1.5.1` y documentar el arreglo y sus pruebas-regla en `CHANGELOG.md`.
- [x] 6.4 Construir el paquete reproducible con `python packaging/build_zip.py` y validar `dist/DocumentadorPredictivo_v1.5.1.zip` con `python -m zipfile -t dist/DocumentadorPredictivo_v1.5.1.zip`.
- [x] 6.5 Actualizar el grafo con `graphify update .`, revisar el diff del grafo y documentar cualquier omisión residual.
- [ ] 6.6 Sincronizar/archivar el cambio según Fase 7, registrar la release `v1.5.1` en Gantt y dejar commit/tag/push pendientes de autorización explícita.
