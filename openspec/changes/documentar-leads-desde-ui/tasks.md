## 1. Harness y contratos de lote

- [ ] 1.1 Verificar el arnés actual: dependencias fijadas, `unittest`, Ruff, CI y
  ejecutar `python -m unittest discover -s tests -v` y Ruff desde
  `automation_salesforce/`.
- [ ] 1.2 Definir pruebas sintéticas y un modelo local de trabajo con IDs
  confirmados y estados `pendiente`, `procesando`, `documentado` y `error`, sin
  contenido de comentarios ni datos de clientes.
- [ ] 1.3 Implementar persistencia local de resultados y recuperación del lote;
  rechazar IDs fuera del lote confirmado y un segundo trabajo concurrente.

## 2. Puente de la UI existente

- [ ] 2.1 Servir la UI generada desde el proceso de `run_leads_ui.py` mediante un
  puente loopback temporal, manteniendo el aspecto y la ventana actuales.
- [ ] 2.2 Añadir selección de Leads, contador de selección, confirmación explícita
  del lote y botón `Documentar seleccionados`.
- [ ] 2.3 Añadir actualización de estados, colores y acciones manuales por Lead,
  sin insertar texto de comentarios en el HTML ni en los endpoints.
- [ ] 2.4 Escribir pruebas de renderizado, validación de solicitudes locales y
  actualización de estados; cubrir rechazo de lote vacío y no confirmado.

## 3. Documentación automática y guardado controlado

- [ ] 3.1 Extraer un worker secuencial reutilizable del runner de cola existente
  que procese solo un Lead confirmado por vez y abra/cierre únicamente su pestaña
  Salesforce de trabajo.
- [ ] 3.2 Implementar la acción de Guardar limitada al editor de `Otra información`
  después de verificar exactamente el texto compuesto; prohibir cambios de otros
  campos y reintentos automáticos de escritura.
- [ ] 3.3 Integrar el worker con el puente local para publicar estados y continuar
  tras un error, manteniendo la UI abierta y habilitando la opción manual.
- [ ] 3.4 Añadir pruebas del worker: orden secuencial, solo IDs confirmados,
  verificación fallida sin guardado, error continuable y ausencia de acciones
  prohibidas.

## 4. Verificación supervisada y cierre

- [ ] 4.1 Ejecutar suite completa, Ruff y `openspec validate --changes`; corregir
  fallos con pruebas de regresión.
- [ ] 4.2 Prueba manual con un único Lead autorizado: confirmar que conserva el
  historial, agrega los intentos, guarda `Otra información`, actualiza la UI y no
  cierra la lista.
- [ ] 4.3 Prueba manual con lote pequeño que incluya un error controlado; confirmar
  continuación secuencial, estado `error` y opción manual disponible.
- [ ] 4.4 Registrar solo métricas y resultados sin datos personales, actualizar
  Graphify y solicitar autorización antes de commit o push.
