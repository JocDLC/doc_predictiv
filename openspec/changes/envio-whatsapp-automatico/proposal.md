# Propuesta: envio-whatsapp-automatico

## Why

Cuando un lead pidió contacto por WhatsApp (`Preferred mean of contact` =
"vía whatsapp"), el primer contacto **debe** ser por WhatsApp — es lo que la
persona eligió. Hoy el bot toma y asigna el lead, pero el envío del mensaje
queda a cargo del auxiliar, con el mismo problema de siempre: alguien tiene
que estar pendiente para no dejar pasar el contacto inicial.

## What Changes

- Tras la toma y el Save del panel "Contact Client", si la bandeja es **AR**,
  el toggle de UI está activo y `preferencia_contacto` contiene "whatsapp":
  - Se escribe en `Otra información` **solo** la línea de intento
    `1 INT Envío WhatsApp DD/MM/AAAA HH:MM` (sin la marca `Asignado` —
    para estos leads el intento documentado ES la evidencia de la toma).
  - Se pulsa el botón `Send To Whatsapp` del encabezado del lead.
  - Se espera el toast verde de confirmación y se cierra con su X.
- Nuevo toggle "Enviar WhatsApp auto" en la UI del monitor, persistido en
  `monitor_state.json`, **apagado por defecto** hasta validar envíos reales.
- Nuevos outcomes en `finalizacion`: `wa_ok`, `wa_no_confirmado`,
  `wa_error:<exc>`.
- Alcance: **solo bandeja AR** en esta iteración; CO/MX quedan con el
  toma sin comentarios ni envío automático.

## Capabilities

### New Capabilities

(ninguna — extiende el monitor de bandeja existente)

### Modified Capabilities

- `monitor-bandeja-leads`: el flujo de finalización de la toma gana el paso
  de envío WhatsApp condicionado por preferencia de contacto, bandeja y
  toggle de UI.

## Impact

- `automation_salesforce/lead_monitor.py`: rama WhatsApp en la
  finalización; escritura del intento; click `Send To Whatsapp`; espera y
  cierre del toast de confirmación; outcomes `wa_*`.
- `automation_salesforce/ui_server.py`: toggle `enviar_whatsapp` en estado,
  endpoint de toggle, SSE.
- `documentador_predictivo.html` (y su copia en `dist/`): checkbox/botón del
  toggle junto a los controles del monitor.
- `automation_salesforce/tests/test_lead_monitor.py` y `test_ui_server.py`:
  cobertura de la rama nueva.
