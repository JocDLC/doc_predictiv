# Spec delta: monitor-bandeja-leads

## ADDED Requirements

### Requirement: REQ-814: Equipo destinatario con franjas propias

El estado del monitor MUST persistir una lista `equipo` de personas
destinatarias. Cada persona tiene `nombre` (tal como aparece en el
lookup de Salesforce) y `franjas` horarias propias en formato `hh:mm`
validadas con la misma regla que el horario del monitor. La UI MUST
exponer una sección para agregar/quitar personas y editar sus franjas.

#### Scenario: persistencia del equipo

**Given** el operador agrega una persona con nombre y franjas.
**When** se guarda.
**Then** `monitor_state.equipo` la contiene y sobrevive reinicios.

#### Scenario: franja inválida

**Given** una franja con formato inválido o solapada dentro de la misma
persona.
**When** se guarda.
**Then** se rechaza con error y el estado previo queda intacto.

### Requirement: REQ-815: Encargada activa sin comentario de asignación

Al tomar un lead, el monitor MUST determinar la encargada activa como la
primera persona cuya franja cubre la hora actual. Si el nombre coincide
con el propietario post-pickup (el usuario logueado) o no hay encargada,
la toma MUST NOT escribir comentarios. Si corresponde un envío real
de WhatsApp en AR, se documenta ese contacto según su regla específica.
Si es otra persona, el bot MUST NOT escribir en `Otra información` ni
enviar WhatsApp, cualquiera sea la preferencia de contacto del lead.

#### Scenario: franja del propio usuario

**Given** la encargada activa es el usuario logueado (nombre coincide
con el propietario post-pickup).
**When** finaliza la toma.
**Then** la toma no escribe comentarios y no reasigna; WhatsApp automático
en AR conserva sus condiciones de envío y documentación de contacto.

#### Scenario: encargada distinta y lead whatsapp

**Given** la encargada activa es otra persona y el lead tiene
`preferencia_contacto` con whatsapp.
**When** finaliza la toma.
**Then** no se modifica `Otra información` y NO se envía WhatsApp automático.

#### Scenario: encargada distinta y lead sin preferencia clara

**Given** la encargada activa es otra persona y el lead no declara
whatsapp ni llamada.
**When** finaliza la toma.
**Then** no se modifica `Otra información`.

### Requirement: REQ-816: Cambio de propietario verificado

Con encargada distinta del usuario, tras guardar Contact Client el
monitor MUST: pulsar el botón `Cambiar propietario` (lápiz del campo
`Propietario del candidato`, dentro de shadow DOM), esperar el modal
"Cambiar propietario de Candidato", tipear el nombre en el lookup,
elegir la opción que coincida, pulsar `Cambiar propietario` del footer y
verificar que el propietario del lead es la encargada. Si el toast no
aparece o cualquier paso falla MUST reportar
`reasignacion_error:<paso>` y el lead queda con el usuario del bot. El
clic de confirmación MUST NOT reintentarse a ciegas.

#### Scenario: reasignación exitosa

**Given** encargada distinta y todos los pasos del modal completados.
**When** se confirma `Cambiar propietario`.
**Then** la relectura del propietario coincide con la encargada y
`finalizacion` incluye `reasignado`.

#### Scenario: la opción no aparece

**Given** el lookup no muestra una opción que coincida con el nombre.
**When** se agota la espera.
**Then** `finalizacion` incluye `reasignacion_error:opcion`, se cancela
el modal y el lead queda con el usuario del bot.

#### Scenario: lead reasignado nunca envía WhatsApp

**Given** un lead AR con `preferencia_contacto` "vía whatsapp" y una
encargada distinta al usuario.
**When** finaliza la toma.
**Then** el botón `Send To Whatsapp` NO se pulsa, no se escribe comentario
y se ejecuta la reasignación.
