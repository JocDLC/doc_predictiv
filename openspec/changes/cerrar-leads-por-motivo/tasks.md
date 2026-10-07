# Tasks: cerrar-leads-por-motivo

> El auxiliar decide cuándo cerrar: sin mínimo de INT ni conteos. Verificación
> final obligatoria: estado `Cerrado` + propietario `AR_LEAD_COLD`. Nunca
> repetir `Convert Lead → Yes` sin haber confirmado que no se ejecutó.
> Nunca pegar datos de clientes ni contenido de campos en logs/tests/chat.

## 1. Contratos y reglas (puro, sin Salesforce)
- [x] 1.1 `lead_closure.py`: tabla cerrada de motivos con los 3 valores exactos
  (Ilocalizable / Cliente deja de interactuar; Rechazo [no] argumentado;
  Sub-Cualificación correspondiente) y códigos de motivo `ilocalizable`,
  `deja_de_interactuar`.
- [x] 1.2 `closure_store.py`: validación de cola de cierre (`operation`,
  `leads[].lead_id` Salesforce válido, `leads[].reason` conocido), freeze con
  `run_id`, append atómico de resultados y lectura tolerante.
- [x] 1.3 Tests de contratos: motivos desconocidos rechazados, cola inválida,
  freeze inmutable, resultados sin contenido de campos.

## 2. UI: selección y confirmación
- [x] 2.1 Sección de cierre por Lead en la vista de cola: checkbox `Cierre`
  + radios de motivo (sin motivo por defecto), sin afectar el checkbox `Cola`.
- [x] 2.2 Barra: `Seleccionar todos`/`Ninguno`, `Asignar motivo a
  seleccionados`, `Preparar cierre`, `Ejecutar cierre` (disabled hasta motivo
  completo en todos los seleccionados).
- [x] 2.3 Resumen de confirmación con cantidad por motivo y advertencia de
  que se ejecutará Guardar + Convert Lead → Yes.
- [x] 2.4 Persistencia local de selección/motivo que sobreviva al polling;
  estados de cierre separados del badge de documentación.
- [x] 2.5 Tests Node/vm: selección masiva, motivos mixtos, sin cierre sin
  motivo, polling no borra selección.

## 3. Servidor
- [x] 3.1 `PUT /api/close-queue` y `GET /api/close-results` con token.
- [x] 3.2 `POST /run-close`: preflight de navegador (mismo que `/run`),
  freeze bajo `run_lock`, spawn del runner; 409 si hay operación activa.
- [x] 3.3 `/status` incluye `operation` (documentacion|cierre) cuando corre.
- [x] 3.4 Tests del servidor: endpoints, token, freeze, exclusión mutua,
  rechazo de motivos inválidos antes de spawn.

## 4. Runner de cierre
- [x] 4.1 `run_close_queue.py`: misma forma que `run_document_queue.py`
  (create_driver adjunto, prompt de auth, loop por Lead, release_driver).
- [x] 4.2 Lectura previa por Lead: estado candidato, Comentario, hash de
  Otra información, propietario; clasificación `ya_cerrado`/`revision`/
  `conflicto` antes de tocar nada.
- [x] 4.3 Edición: doble clic en Comentario (sección Cualificación), literal
  exacto, Cualificación por etiqueta, Sub-Cualificación dependiente por
  etiqueta (scroll dentro del menú si hace falta).
- [x] 4.4 Guardar con el patrón existente + recuperación de timeout
  (recargar y releer antes de declarar error).
- [x] 4.5 Verificación intermedia: 3 campos persistidos, Cerrado y hash de
  Otra información intacto → hito `conversion_pendiente`.
- [x] 4.6 `Convert Lead` → modal esperado → `Yes`; si el modal no es el
  esperado o no aparece, abortar Lead sin pulsar nada.
- [x] 4.7 Verificación final: Cerrado + `AR_LEAD_COLD` → `cerrado_verificado`.
- [x] 4.8 Tests con driver falso: ambos motivos, ya cerrado, conflicto,
  timeout de Guardar recuperado/no recuperado, modal ausente, fallo tras Yes
  → `conversion_no_verificada`.

- [x] 4.9 Regresión de cualificación: seleccionar y leer el mismo control visible,
  limitar opciones al listbox asociado, ignorar formularios/iframes ocultos,
  rechazar ambigüedad y verificar valores exactos para ambos motivos sin clics repetidos.
- [x] 4.10 Regresión de verificación final: esperar `Cerrado + AR_LEAD_COLD`,
  tolerar carga transitoria, no recargar en bucle con propietario pendiente,
  leer el nombre visible del lookup en vez del ID interno y no repetir `Yes`.
- [x] 4.11 Alternativa de Sub-Cualificación para `ilocalizable`: seleccionar
  `Ilocalizable` preferentemente y `Permanece ilocalizable` solo si la primera
  no está disponible; verificar exactamente la alternativa persistida.

## 5. Verificación y cierre
- [x] 5.1 Suite completa + Ruff + harness.
- [ ] 5.2 `python -m business_contract_graph verify` + `git diff --check`.
  `git diff --check` pasa; `business_contract_graph verify` queda bloqueado por
  el recibo Archify no aprobado (pendiente previo, no por esta corrección).
- [x] 5.3 `graphify update .` al finalizar.
- [ ] 5.4 Piloto autorizado: 1 Lead por motivo, luego lote pequeño; revisar
  efectos secundarios de la conversión.
- [ ] 5.5 Versión menor (1.1.0 si contratos compatibles), CHANGELOG,
  paquete dist sin datos operativos; commit/tag solo con autorización.
