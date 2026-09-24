# Tareas: documentar-automatico-guardado

> Modo lote autorizado por el operador (2026-09-17) tras pilotos supervisados
> exitosos. El bot ahora pulsa **Guardar** y verifica la persistencia
> releyendo el campo. Sigue prohibido: Cancelar, reasignar, cerrar, cambiar
> estado, editar otros campos, automatizar login/2FA.
>
> Convención: `[ ]` pendiente, `[~]` en curso, `[x]` hecha. Una tarea a la vez.
> Tras cada fase: `python -m unittest discover -s tests` y
> `python -m ruff check . --select E4,E7,E9,F` desde `automation_salesforce/`.
> Nunca pegar contenido de `Otra información` ni datos de clientes en chat,
> logs o tests: solo conteos, IDs enmascarados y nombres de campos.

## Fase 0 — Preflight

- [x] 0.1 Releer `run_document_queue.py`, `comment_writer.py`,
      `comment_reader.py`, `local_audit.py` y la parte de `documentador_predictivo.html`
      que arma `buildBotQueue()`, `isDone()` y la tabla DOCUMENTAR.
- [x] 0.2 Suite base anotada (85/85).

## Fase 1 — Guardado automático en el runner (Python)

- [x] 1.1 `comment_writer.py`: `SAVE_BUTTON_SCRIPT` que localiza el botón
      `Guardar`/`Save` del formulario de edición activo (por texto/aria-label,
      atravesando Shadow DOM) y `save_edit_form(driver)` que lo pulsa por JS y
      espera a que el registro salga de modo edición.
- [x] 1.2 `comment_reader.py` (o writer): `verify_saved_value(driver, expected)`
      que reabre el registro (`driver.get` de la misma URL), relee `Otra
      información` y compara igualdad exacta con el texto preparado.
- [x] 1.3 `run_document_queue.py`: flag `--auto` → por Lead, tras
      `prepare_other_information`, llamar `save_edit_form` +
      `verify_saved_value` y registrar `guardado`/`error`. Sin `--auto` el
      flujo supervisado queda igual. Ajustar resumen final y `record_result`
      al nuevo estado.
- [x] 1.4 Tests: `save_edit_form` localiza solo el Guardar del formulario;
      `verify_saved_value` compara tras recarga; `--auto` procesa sin input;
      test estático actualizado (`.click()` permitido solo en lápiz + Guardar
      del formulario; `SaveEdit`/`save_record`/`updateRecord` prohibidos).
- [x] 1.5 Suite + Ruff en verde.

## Fase 2 — UI: selección, estados e importación

- [x] 2.1 Checkbox por fila en la tabla DOCUMENTAR + controles
      "pendientes / todos / ninguno" (estado de selección en memoria).
- [x] 2.2 "Exportar selección para bot": `buildBotQueue()` filtrado a los
      seleccionados (mismo contrato JSON).
- [x] 2.3 Estado por Lead: `pendiente` | `bot` | `manual` persistido en
      localStorage; el check existente marca `manual`; badge/ícono en la fila.
- [x] 2.4 "Importar resultado del bot": `<input type=file>` lee
      `*.resultado.json`; `status: guardado` → `bot`; contadores
      `N bot · M manual · K pendientes` en el encabezado.
- [x] 2.5 Verificar en navegador: selección, exportación filtrada,
      importación y contadores. (Verificado en uso real 2026-09-18/23.)
- [x] 2.6 Persistir localmente por Lead el comentario preparado y los estados
      separados `copiado`/`pegado manualmente`, sin inferir que copiar implica
      guardar en Salesforce.
- [x] 2.7 Tras un resultado `guardado`, cargar el snapshot privado completo de
      `Otra información` para revisión y edición desde la UI, sin incluirlo en
      logs, resultados de cola ni Git.

## Fase 3 — Correcciones verificadas desde la UI

- [x] 3.1 Implementar hash de snapshot, lectura actual de `Otra información` y
      estado `conflicto` cuando Salesforce difiera de la copia base.
      (`correction_loader.py` + `run_corrections.py`: relee el campo y compara
      `content_hash` con `base_hash` antes de cualquier escritura.)
- [x] 3.2 Añadir acción de corrección que reemplace exclusivamente `Otra
      información` tras confirmación, guarde y relea para verificar igualdad.
      (UI "Exportar correcciones" → `run_corrections.py` → `corregido`/`conflicto`;
      snapshot privado actualizado tras verificación; badge `corregido` en UI.)
- [x] 3.3 Pruebas: comentario manual copiado/confirmado, snapshot privado, éxito
      de corrección, conflicto sin escritura y ausencia de contenido en logs.
      (`test_corrections.py`: validación de cola, hash match/mismatch, resultado
      sin contenido. 95/95 OK.)
- [ ] 3.4 Prueba supervisada de una corrección autorizada y una simulación de
      conflicto; verificar que el flujo manual permanece disponible.

## Fase 4 — Documentación

- [x] 3.1 `README.md` + `HANDOFF.md`: modo `--auto`, verificación
      post-guardado, estados de la UI, flujo exportar→correr→importar.
- [x] 3.2 Actualizar notas en este `tasks.md` con lo verificado.

## Fase 4.5 — Correcciones post-prueba (2026-09-18)

- [x] Causa raíz del fallo en la tanda de 10: el editor se cerraba de forma
      optimista y el bot navegaba a verificar antes de que el guardado
      terminara → el save quedaba abortado. Fix: `save_edit_form` espera el
      cierre del editor + pausa fija (`SAVE_SETTLE_SECONDS = 3s`) antes de
      continuar; `verify_saved_value` reintenta la lectura 3 veces con
      normalización de saltos de línea y reporta longitudes para diagnóstico.
- [x] Cola viva en la UI: vista `viewQueue` con los Leads seleccionados;
      `cola_activa.json` se reescribe sola al cambiar la selección (permiso de
      carpeta en IndexedDB); polling de `*.resultado.json` y
      `*.snapshots.json` cada ~3s; los `guardado` salen solos de la cola;
      "Volver" aplica estados a cada Lead.
- [x] Segunda demora de Lightning: el editor aparecía antes de inicializarse y
      pisaba el valor inyectado con el original. Fix: `EDITOR_READY_SECONDS = 2s`
      tras abrir el editor, re-localización, escritura, doble verificación de
      estabilidad (`EDITOR_STABILITY_SECONDS`) y un reintento.
- [x] Falsos `error` con guardado exitoso: (a) la recarga leía caché vieja →
      `verify_saved_value` lee primero en la misma página y recarga solo como
      respaldo, una única verificación por defecto; (b) Salesforce muestra cada
      TAB como espacio en modo lectura → `normalize_persisted_text` colapsa
      espacios/tabs por línea (test de regresión `..._tolerates_display_whitespace`).
- [x] Servidor local `ui_server.py` (127.0.0.1:8765, token por sesión, único
      endpoint `/run` sobre `cola_activa.json`) + botón "Ejecutar bot" en la UI.
- [x] El runner adjunto al navegador persistente abre su propia pestaña
      (`switch_to.new_window`) y no navega la pestaña de la UI.

## Fase 4.6 — Mejoras de la vista de cola (2026-09-23)

- [x] La tarjeta del Lead documentado muestra y copia el campo completo de
      `Otra información` (snapshot), no solo el bloque nuevo; el editor de
      borrador se ajusta al contenido.
- [x] Vista de cola: texto confirmado debajo de cada Lead `guardado`, botón
      "Abrir en Salesforce" por fila, "Quitar" (solo documentados) y "Limpiar
      documentados"; aviso de que re-ejecutar reintenta solo `error`/pendientes.
- [x] Lista principal: botón "Seleccionar pendientes" para armar la cola de una
      sola vez.

## Fase 5 — Verificación supervisada

- [x] 4.1 Suite + Ruff en verde; `git diff --check`. (98/98, Ruff OK.)
- [x] 4.2 Tandas de prueba en `--auto` (10, 5 Leads): verificado en Salesforce
      que quedaron guardados con INT correctos y sin líneas extra.
- [x] 4.3 Importar el resultado en la UI y verificar estados/contadores
      (importación automática vía polling de la cola viva).
- [x] 4.4 Con aprobación explícita: lote completo de los restantes (45 Leads
      del primer archivo, luego 63 de un segundo archivo) documentado.
- [x] 4.5 Revisión de logs/capturas/resultados: solo Lead IDs enmascarados,
      longitudes y estados; sin contenido del campo.
- [ ] 3.4 (Fase 3) Prueba supervisada de una corrección autorizada y una
      simulación de conflicto: pendiente; el flujo manual permanece disponible.

## Fase 6 — Cierre

- [ ] 5.1 `RESULTADOS_DE_PRUEBA.md` con conteos (sin datos de clientes).
- [x] 5.2 `graphify update .` (412 nodos, 768 aristas).
- [ ] 5.3 `openspec validate --changes`: la CLI `openspec` no está instalada en
      la máquina (sin Node/npx); validación estructural manual de los artefactos.
- [x] 5.4 `git status`; autorización de commit otorgada por el usuario.
- [ ] 5.5 Proponer archivo de `documentar-desde-html-supervisado` (queda
      absorbido por este cambio en la parte automática).

## Fuera de alcance

- Editar otros campos o acciones de negocio.
- Headless real (la sesión vive en la ventana persistente).
- Deshacer cambios ya guardados.
