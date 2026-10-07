# Implementación paso a paso: seleccionar-campos-por-pais

Trabajar una tarea a la vez y marcarla solo tras su prueba. No ejecutar Selenium sobre Leads reales ni regenerar el ZIP antes de aprobar las regresiones. La fuente de verdad es la BD Wolkvox cargada; `TEL1` permanece local en memoria de la UI.

## 1. Preparación y contrato de país

- [x] 1.1 Revisar `AGENTS.md`, los cuatro artefactos de este cambio y la infraestructura de tests/lint. Ejecutar la suite base y registrar fallos previos sin modificar controles de seguridad; confirmar que `openspec` está disponible o anotar el bloqueo.
- [x] 1.2 Agregar pruebas sintéticas de clasificación de **todas las filas** de la BD (también las que no tienen Lead ID): `91549` → Argentina, `9352` → México, `957` → Colombia; lote homogéneo válido, AR+COL inválido, COL+MEX inválido aun con modo compartido, prefijo desconocido, vacío/dañado y solo un Lead seleccionado entre varios incompatibles. Nunca usar teléfonos reales.
- [x] 1.3 Implementar detección determinística sobre el `TEL1` de cada fila parseada antes del filtro de `buildLeads`, sin cambiar el valor ni consultar servicios externos. Devolver país concreto, modo compatible y recuentos seguros; bloquear lote de cero Leads y cualquier entrada inválida, sin mostrar números en mensajes/logs/colas.
- [x] 1.4 Agregar tests de `queue_loader.py` y `closure_store.py` para `country` conocido, desconocido y ausente (legacy = Argentina). Implementar un contrato único de campos por modo y validar códigos antes de abrir Selenium; no introducir `TEL1` en colas ni en endpoints.

## 2. Interfaz y guardas de ejecución

- [x] 2.1 Agregar tests de UI para selector de solo dos modos, bandera y nombre del país concreto detectado, mapeo visual de campos, estado sin país confirmado, sugerencia para cambiar un modo incompatible y rechazo de mezcla sin bypass.
- [x] 2.2 Implementar selector y emblema/bandera mediante recursos locales (CSS/SVG inline, sin peticiones externas) en la pantalla del bot. Al importar BD válida, detectar país y proponer modo compatible; guardar selección por archivo/sesión y no reinterpretar progreso antiguo de otro modo.
- [x] 2.3 Antes de `runBot`, `runClose`, exportación total y exportación de selección, volver a comprobar la **BD completa** y el modo. Si hay discrepancia, impedir escritura/POST, mostrar país detectado y ofrecer cambio explícito de selector. Los errores informan solo cantidades y categorías. Mantener la confirmación comercial existente para cerrar.
- [x] 2.4 Propagar `country` a ambas colas por UI, conservarlo al congelar en `ui_server.py` y comprobar que no cambia durante una tanda aunque cambie la UI. Probar con Node/vm o infraestructura actual de tests y comprobar ausencia de teléfonos en payloads/resultados.

## 3. Documentación en el campo correcto

- [x] 3.1 Añadir regresiones DOM y runner para lectura/escritura/verificación del mismo campo visible: Argentina en `Otra información`; Colombia y México en `Comentario` de Cualificación. Cubrir conservación de texto, cálculo de próximo `INT`, deduplicación de `call_id`, `Lead duplicado`, control ambiguo, guardado tardío y modos `--auto`/supervisado.
- [x] 3.2 Adaptar `comment_reader.py`, `comment_writer.py` y `run_document_queue.py` para usar el contrato por modo sin cambiar la semántica argentina ni tocar el campo de cierre. Leer el mismo campo tras recarga antes de afirmar `guardado`; no reescribir texto no verificado.

## 4. Cierre sin pérdida de datos

- [x] 4.1 Añadir regresiones para ambos motivos y ambos modos en `lead_closure.py`/`run_close_queue.py`: texto anterior conservado, anexado del motivo una vez (también tras timeout/reintento), campo de intentos intacto, picklists actuales, estado `Cerrado`, propietario `AR_LEAD_COLD`, reanudación segura y `Yes` no repetido.
- [x] 4.2 Implementar el cierre por contrato: Argentina reemplaza el motivo en `Comentario` y conserva `Otra información`; Colombia/México anexa el motivo exacto en `Otra información` y conserva `Comentario`. Verificar formulario, contenido completo persistido y campo no elegido antes de `Convert Lead → Yes`; ante incertidumbre, revisión sin conversión adicional.

## 5. Progreso, correcciones y compatibilidad

- [x] 5.1 Agregar pruebas de snapshots/resultados/progreso separados por modo/campo, importación de copia legacy, cambio de país tras cargar un CSV y rechazo de corrección con hash/procedencia incompatibles.
- [x] 5.2 Ajustar `snapshot_store.py`, `run_corrections.py`, `correction_loader.py` y UI para metadatos de modo/campo, verificación del hash del campo correcto y aislamiento de progreso. Mantener compatibilidad de colas históricas sin `country` como Argentina, sin afirmar validación de prefijo si se invoca CLI con JSON sin teléfonos.

## 5a. Regresiones detectadas en México

- [x] M1 Tratar `call_id` como texto opaco completo en Python y UI, extraído de la posición del ID después de fecha/hora en una línea INT; cubrir múltiples puntos, letras, números, ceros iniciales y coincidencia exacta sin subcadenas. Reejecutar sobre historial existente no debe agregar intentos ni cambiar su numeración.
- [x] M2 Reconocer `Sub cualificación`/`Sub cualificacion` además de las etiquetas existentes, tanto en edición como en lectura/verificación; probar el DOM con Cualificación y Sub cualificación presentes sin seleccionar el control ajeno.
- [x] M3 Bloquear el cierre antes de cualquier escritura si el estado/propietario no se pudo leer; cubrir México ya cerrado y reanudación sin convertir ante picklists no verificados.
- [x] M4 Ejecutar regresiones, suite completa, Ruff, compilación y diff; actualizar Graphify. No reparar historiales reales ni publicar ZIP/commit hasta completar los pendientes de servidor y pilotos autorizados de México/Colombia.

Verificación de M1–M4: 273 tests completos y 67 pruebas enfocadas con el Python embebido y los módulos de la copia local del paquete; Ruff, compilación y `git diff --check` aprobados. Copia local de runtime sincronizada, ZIP sin regenerar. OpenSpec CLI no disponible; pilotos reales aún pendientes.

- [ ] M5 Evitar ejecución de documentación sin intentos pendientes o tras fallo de sincronización; validar la cola congelada en el servidor antes de lanzar el runner y distinguir código 2 de fallo del navegador. Mantener cierre independiente de documentación. Probar sin Salesforce real.

## 6. Verificación y entrega para otro equipo

- [x] 6.1 Ejecutar suite completa de `automation_salesforce/tests`, tests de UI, Ruff, compilación y `git diff --check`; revisar casos Given/When/Then del spec sin Salesforce real. Corregir con regresiones sin debilitar tests existentes.
- [x] 6.2 Actualizar instrucciones visibles, README/LEEME y CHANGELOG; verificar que el prefijo del CSV es un control de coherencia local y no garantía de origen/estado de Salesforce. Ejecutar `openspec validate --changes` si se dispone de la CLI; si no, dejar bloqueo explícito. Actualizar `graphify update .` tras modificar código.
- [x] 6.3 Reconstruir **solo** `dist/DocumentadorPredictivo.zip` desde lista blanca runtime y comprobar versión, imports con Python embebido, integridad del ZIP y exclusión de tests, ejemplos, harnesses, Graphify/Archify/OpenSpec, sesiones/tokens, colas, logs y datos de clientes. No copiar datos operativos de la máquina de desarrollo.
- [ ] 6.4 Solicitar permiso por separado para pilotos supervisados sobre **un Lead autorizado por país** (sin cerrar ni convertir de prueba sin autorización). Solo si se verifica el comportamiento real y se aprueba la distribución, compartir el nuevo ZIP; no hacer commit/tag/push sin confirmación del usuario.
