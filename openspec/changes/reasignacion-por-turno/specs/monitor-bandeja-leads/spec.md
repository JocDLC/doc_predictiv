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

### Requirement: REQ-815: Encargada activa y comentario con método

Al tomar un lead, el monitor MUST determinar la encargada activa como la
primera persona cuya franja cubre la hora actual. Si el nombre coincide
con el propietario post-pickup (el usuario logueado) o no hay encargada,
el flujo MUST seguir el comportamiento vigente (`Asignado` o intento
WhatsApp + envío automático en AR). Si es otra persona, `Otra
información` MUST quedar `Asignado - Enviar Whatsapp`,
`Asignado - Llamarlo` o `Asignado - Gestionarlo` según la
`preferencia_contacto` del propio lead (whatsapp → Enviar Whatsapp,
llamada/teléfono → Llamarlo, otro/vacío → Gestionarlo), con la misma
verificación estricta de siempre.

#### Scenario: franja del propio usuario

**Given** la encargada activa es el usuario logueado (nombre coincide
con el propietario post-pickup).
**When** finaliza la toma.
**Then** el flujo es el normal: `Asignado` o WhatsApp automático en AR,
sin reasignación.

#### Scenario: encargada distinta y lead whatsapp

**Given** la encargada activa es otra persona y el lead tiene
`preferencia_contacto` con whatsapp.
**When** finaliza la toma.
**Then** `Otra información` persiste `Asignado - Enviar Whatsapp` y NO se
envía WhatsApp automático.

#### Scenario: encargada distinta y lead sin preferencia clara

**Given** la encargada activa es otra persona y el lead no declara
whatsapp ni llamada.
**When** finaliza la toma.
**Then** `Otra información` persiste `Asignado - Gestionarlo`.

### Requirement: REQ-816: Cambio de propietario verificado

Con encargada distinta del usuario, tras documentar el comentario el
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
**Then** el botón `Send To Whatsapp` NO se pulsa, el comentario es
`Asignado - <método>` y se ejecuta la reasignación.
