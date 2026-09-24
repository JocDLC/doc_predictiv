# Spec: guardado-automatico

## ADDED Requirements

### Requirement: REQ-601: Modo automático por lotes

El runner MUST procesar la cola completa sin pausas cuando se invoca con
`--auto`. Por cada Lead MUST abrir el registro, leer `Otra información`,
calcular el próximo `N INT` real, componer los intentos, cargarlos en el
editor, pulsar Guardar y verificar la persistencia. El modo sin `--auto`
MUST conservar el comportamiento supervisado actual.

#### Scenario: lote automático

**Given** una cola válida de N Leads.
**When** se ejecuta `run_document_queue.py --auto queues/cola.json`.
**Then** cada Lead se prepara y se guarda sin intervención, y el resumen
final informa guardados y errores.

#### Scenario: modo supervisado intacto

**Given** el runner sin `--auto`.
**When** se procesa una cola.
**Then** cada Lead requiere `PREPARAR`/`s`/`q` y el Guardar sigue siendo manual.

### Requirement: REQ-602: Guardar limitado al botón Guardar del formulario

El runner MUST pulsar únicamente el botón `Guardar`/`Save` del formulario de
edición activo tras cargar el texto verificado. MUST NOT pulsar Cancelar,
reasignar, cerrar, cambiar estado ni invocar acciones de negocio
(`SaveEdit`, `save_record`, `updateRecord`).

#### Scenario: solo Guardar

**Given** un Lead con el borrador cargado y verificado.
**When** el runner guarda.
**Then** el único control pulsado es el Guardar del formulario de edición.

### Requirement: REQ-603: Verificación post-guardado

El estado `guardado` MUST confirmarse reabriendo el registro y releyendo
`Otra información`; el estado se afirma solo si el contenido coincide
exactamente con el texto preparado. Si difiere, el Lead se registra `error`.

#### Scenario: persistencia confirmada

**Given** un Lead preparado y guardado.
**When** el runner reabre el registro.
**Then** `Otra información` contiene exactamente el texto preparado y el
resultado es `guardado`.

#### Scenario: guardado no confirmado

**Given** un Lead cuyo campo re-leído no coincide.
**When** termina su procesamiento.
**Then** el resultado es `error` con métricas seguras (longitudes), sin contenido.

### Requirement: REQ-604: Selección y exportación desde la UI

La UI MUST permitir seleccionar Leads de la vista DOCUMENTAR y exportar una
cola JSON solo con los seleccionados, en el mismo contrato que la cola
completa. MUST ofrecer seleccionar pendientes, todos y ninguno.

#### Scenario: exportar selección

**Given** 3 Leads marcados con checkbox.
**When** se pulsa "Exportar selección para bot".
**Then** el JSON contiene exactamente esos 3 Leads con sus intentos.

### Requirement: REQ-605: Estados de documentación en la UI

La UI MUST mostrar por Lead uno de: `pendiente`, `documentado por bot`,
`documentado manual`. La importación de un `*.resultado.json` MUST marcar
como `documentado por bot` los Leads con `status: guardado`. Los estados se
persisten en localStorage y el encabezado muestra los tres contadores.

#### Scenario: importar resultado

**Given** un resultado con 5 Leads `guardado` y 1 `error`.
**When** se importa en la UI.
**Then** los 5 quedan `documentado por bot`, el `error` sigue `pendiente` y
los contadores reflejan los totales.

### Requirement: REQ-606: Registro del flujo manual

La UI MUST conservar localmente el comentario preparado para cada Lead y MUST
distinguir el evento `copiado` del evento `pegado manualmente`. El estado
`copiado` solo confirma que se solicitó la copia al portapapeles; el estado
`pegado manualmente` MUST requerir confirmación explícita del operador.

#### Scenario: comentario preparado para documentación manual

**Given** un Lead con intentos transformados desde Wolkvox.
**When** el operador pulsa `Copiar texto` y confirma que lo pegó en Salesforce.
**Then** la UI conserva el comentario preparado y registra los estados `copiado`
y `pegado manualmente` sin asumir que la copia por sí sola fue guardada.

### Requirement: REQ-607: Snapshot completo confirmado por el bot

Después de un guardado automático verificado, el sistema MUST conservar una copia
local privada del contenido completo de `Otra información`, junto con su hash y
fecha de lectura. MUST NOT incluir ese contenido en Git, consola, logs, capturas
ni resultados de cola.

#### Scenario: guardado automático confirmado

**Given** un Lead cuyo guardado se verificó releyendo `Otra información`.
**When** el bot registra el resultado `guardado`.
**Then** la UI puede mostrar el campo completo confirmado para revisión local y el
archivo de resultado conserva solamente metadatos seguros.

### Requirement: REQ-608: Corrección centralizada con detección de conflicto

La UI MUST permitir editar localmente un snapshot completo y solicitar su
aplicación. Antes de guardar, el bot MUST releer `Otra información` y comparar el
hash con el snapshot base. Si difiere, MUST registrar `conflicto` y MUST NOT
sobrescribir Salesforce.

#### Scenario: aplicar una corrección sin cambios externos

**Given** un snapshot cuyo hash base coincide con el valor actual de Salesforce.
**When** el operador confirma `Aplicar corrección`.
**Then** el bot reemplaza solo `Otra información`, guarda, relee y actualiza el
snapshot únicamente si la igualdad exacta fue confirmada.

#### Scenario: conflicto por edición externa

**Given** un snapshot cuyo hash base no coincide con Salesforce.
**When** el operador solicita aplicar la corrección.
**Then** el bot no guarda, registra el estado `conflicto` y deja el Lead disponible
para recargar o documentar manualmente.
