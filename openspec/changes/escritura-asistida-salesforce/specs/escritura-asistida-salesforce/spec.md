# Capability: Escritura asistida y supervisada en Salesforce

## ADDED Requirements

### Requirement: REQ-301: Preparación por Lead del próximo intento

El runner MUST leer el campo `Otra información` de un único Lead, calcular el
mayor patrón `N INT` más uno y usar ese número para construir el nuevo intento.
El cuerpo proporcionado localmente MUST estar libre de prefijo `N INT`.

#### Scenario: historial con un intento

**Given** un Lead cuyo campo contiene una entrada que inicia con `1 INT`.
**When** el usuario proporciona un cuerpo de borrador válido.
**Then** el valor preparado conserva el historial, agrega una línea vacía y
termina con una entrada que inicia con `2 INT`.

### Requirement: REQ-302: Edición limitada a Otra información

El runner MUST activar y completar únicamente el control de edición asociado de
forma inequívoca al campo visible `Otra información`. Si no puede identificarlo
con seguridad, MUST terminar sin escribir.

#### Scenario: control ambiguo o ausente

**Given** un Lead donde el editor de `Otra información` no puede distinguirse.
**When** el runner intenta preparar el borrador.
**Then** toma una captura local, registra solo metadatos seguros y no modifica
ningún control.

### Requirement: REQ-303: Guardado exclusivamente manual

El runner MUST detenerse después de completar el borrador y MUST NOT pulsar
`Guardar`, `Cancelar`, cerrar, reasignar ni modificar estados. La decisión de
guardar o cancelar pertenece exclusivamente al usuario en la interfaz visible.

#### Scenario: revisión del borrador

**Given** que el editor contiene el texto preparado.
**When** el runner finaliza la preparación.
**Then** no emite más acciones Selenium y el usuario puede revisar, guardar o
cancelar manualmente desde Salesforce.

### Requirement: REQ-304: Privacidad y auditoría local

El runner MUST mantener login y 2FA manuales y MUST registrar solo Lead ID
enmascarado, métricas, etapa y errores locales. No MUST registrar el historial,
cuerpo del comentario, teléfonos, emails, cookies, contraseñas ni códigos 2FA.

#### Scenario: error de preparación

**Given** un error de DOM o de validación del borrador.
**When** el runner termina.
**Then** deja una evidencia local segura y no envía ni persiste datos fuera de la
PC del usuario.
