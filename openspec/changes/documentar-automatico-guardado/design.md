# Diseño: documentar-automatico-guardado

## Flujo del modo automático

```text
por cada Lead de la cola (sin pausas):
  driver.get(lead_url) → wait_for_lightning_ready
  find_other_information → next_attempt_number → compose_attempts
  prepare_other_information (lápiz → editor → escribir → verificar)
  save_record():
    localizar botón "Guardar" del formulario de edición → click por JS
    esperar a que el editor se cierre / registro salga de modo edición
  verificación post-guardado:
    driver.get(lead_url) → re-leer Otra información
    confirmar que el contenido coincide con el texto preparado
  record_result(status="guardado" | "error", next_int, attempts, at)
resumen final: guardados / errores
```

## Decisiones

| Tema | Decisión |
|---|---|
| Guardar | Click por JS solo sobre el botón `Guardar`/`Save` del formulario de edición activo. Ningún otro control de negocio. |
| Verificación | `guardado` solo se afirma tras reabrir el Lead y releer el campo con igualdad exacta al texto preparado. |
| Modos | `--auto` = lote completo sin pausas. Sin flag = comportamiento supervisado actual (PREPARAR/s/q). |
| Cancelar | Nunca se pulsa automáticamente; si un Lead falla, el registro queda como estaba (el error aborta antes de Guardar). |
| Test estático | Se permite `.click()` en el botón Guardar del formulario; siguen prohibidos `SaveEdit`, `save_record` de Aura, `updateRecord`, reasignar, cerrar, cambiar estado. |
| Navegador | Mismo mecanismo persistente; el lote corre en la ventana abierta (minimizable). |

## Contrato del resultado

`queues/<cola>.resultado.json` por Lead:

```json
{"lead_id": "...", "status": "guardado|error", "next_int": 6, "attempts": 2, "at": "..."}
```

El resultado de un guardado exitoso también referencia un snapshot local privado
del valor completo y confirmado de `Otra información`. El snapshot queda bajo un
directorio ignorado por Git y no se imprime ni se agrega a logs o capturas.

## Registro local y correcciones

Cada Lead conserva localmente dos conceptos distintos:

- `comment_prepared`: solo las líneas nuevas derivadas de Wolkvox para copiar en
  el flujo manual; `copied_at` registra que el navegador recibió la orden de
  copiar, y `manual_pasted_at` solo se asigna cuando el operador lo confirma.
- `field_snapshot`: el valor completo de `Otra información` releído después de
  un guardado automático confirmado, con `base_hash` y fecha de lectura.

La UI permite editar `field_snapshot` como borrador de corrección. Al seleccionar
**Aplicar corrección**, el bot abre ese Lead, relee el campo y compara su hash con
`base_hash`. Si coincide, reemplaza exclusivamente `Otra información`, guarda y
relee para comprobar igualdad exacta. Si no coincide, registra `conflicto` y no
escribe nada: el operador puede recargar la copia actual o resolverla manualmente.

Los snapshots son datos personales/operativos locales y se almacenan solo en
`automation_salesforce/ui_output/`; la UI no los inserta en resultados, logs ni
capturas de diagnóstico.

## UI (documentador_predictivo.html)

- Checkbox por fila de DOCUMENTAR + "seleccionar pendientes/todos/ninguno".
- "Exportar selección para bot": mismo contrato `buildBotQueue()` filtrado a
  los seleccionados.
- "Importar resultado del bot": `<input type=file>` sobre `*.resultado.json`;
  Leads con `status: guardado` pasan a `botDone` en localStorage.
- Estado por Lead: `pendiente` | `documentado por bot` | `documentado manual`
  (el manual se marca como hoy, con el check existente).
- Contadores en el encabezado: `N por bot · M manual · K pendientes`.
- El detalle de cada Lead distingue **Comentario preparado** de **Otra
  información confirmada**, muestra `Copiado` y `Pegado manualmente` como estados
  separados, y ofrece editar/aplicar una corrección solo cuando existe snapshot.
