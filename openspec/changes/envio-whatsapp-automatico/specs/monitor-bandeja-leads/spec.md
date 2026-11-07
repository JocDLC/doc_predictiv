# Spec delta: monitor-bandeja-leads

## ADDED Requirements

### Requirement: REQ-811: Envío WhatsApp condicionado por preferencia

Tras la toma verificada y el Save del panel, si la bandeja es `AR`, el
toggle "Enviar WhatsApp auto" está activo y el campo
`preferencia_contacto` del lead contiene "whatsapp" (insensible a
mayúsculas/acentos), el monitor MUST escribir en `Otra información` la
línea `1 INT Envío WhatsApp DD/MM/AAAA HH:MM` (fecha y hora locales, en
lugar de `Asignado`), guardarla con la verificación estricta habitual, y
luego pulsar el botón `Send To Whatsapp` del encabezado del lead.

#### Scenario: lead AR con preferencia whatsapp y toggle activo

**Given** un lead AR tomado cuyo `preferencia_contacto` es "vía whatsapp"
y el toggle activo.
**When** finaliza la toma.
**Then** `Otra información` persiste solo `1 INT Envío WhatsApp
DD/MM/AAAA HH:MM`, se pulsa `Send To Whatsapp`, y `finalizacion` termina
en `wa_ok` si el toast de confirmación aparece.

#### Scenario: lead AR con otra preferencia

**Given** un lead AR con `preferencia_contacto` "llamada telefónica".
**When** finaliza la toma.
**Then** no se modifica `Otra información` y no se pulsa ningún botón de envío.

#### Scenario: toggle apagado

**Given** el toggle "Enviar WhatsApp auto" apagado.
**When** se toma un lead AR con preferencia whatsapp.
**Then** no se escribe ningún comentario ni intento y no se envía nada.

#### Scenario: campo ya documentado

**Given** un lead cuyo `Otra información` ya contiene una línea
`N INT Envío WhatsApp ...` o `Asignado`.
**When** finaliza la toma.
**Then** no se duplica la línea ni se pisa el contenido previo, y el
envío se reporta sin nueva escritura.

### Requirement: REQ-812: Confirmación del envío y cierre del toast

Tras pulsar `Send To Whatsapp`, el monitor MUST esperar el toast verde de
confirmación ("Message sent to Whatsapp") hasta ~15 s y, si aparece,
cerrarlo con su botón de cierre. Si el toast no aparece, MUST reportar
`wa_no_confirmado` y MUST NOT reintentar el clic (riesgo de doble envío).

#### Scenario: toast confirmado

**Given** el clic en `Send To Whatsapp` ejecutado.
**When** aparece el toast verde.
**Then** se cierra con su X y `finalizacion` incluye `wa_ok`.

#### Scenario: toast ausente

**Given** el clic ejecutado y el toast no aparece en la ventana de espera.
**When** vence el tiempo.
**Then** `finalizacion` incluye `wa_no_confirmado` y no hay segundo clic.

### Requirement: REQ-813: Toggle persistente en la UI

La UI del monitor MUST exponer un control "Enviar WhatsApp auto" cuyo
estado MUST persistir en `monitor_state.json` y sobrevivir reinicios del
servidor. MUST arrancar apagado por defecto.

#### Scenario: persistencia tras reload

**Given** el toggle activado por el usuario.
**When** el servidor se reinicia.
**Then** el toggle vuelve activo al arrancar.

#### Scenario: valor por defecto

**Given** una instalación sin estado previo.
**When** arranca el servidor.
**Then** el toggle está apagado y no se envían WhatsApp automáticos.
