# Design: envio-whatsapp-automatico

## Decisiones

### Dónde engancha

`finalize_pick_up` (lead_monitor.py) hoy devuelve `<panel>/<marca>`. La
rama WhatsApp extiende la parte `<marca>`: si aplica, el "texto a
garantizar" en `Otra información` es la línea de intento en vez de
`Asignado`, y después se encadena el envío como tercer segmento del
outcome: `<panel>/<marca>/<wa>`.

```
panel_guardado/marca_ok/wa_ok
sin_panel/marca_ok/wa_no_confirmado
panel_guardado/marca_presente/wa_ok
```

### Decisión de texto: intento en vez de `Asignado`

El usuario confirmó que para leads WhatsApp el campo queda **solo** con
`1 INT Envío WhatsApp DD/MM/AAAA HH:MM`. La línea de intento cumple el
mismo rol de evidencia que `Asignado` (registra quién/cuándo), así que
`_ensure_take_mark` se parametriza con un "texto objetivo" por lead:
`Asignado` por defecto, la línea de intento para AR+whatsapp+toggle.

Idempotencia: se considera "ya documentado" si el campo contiene la marca
o cualquier línea `\d+ INT ` (otro intento humano/bot previo) — nunca se
duplica ni se pisa.

### Detección de preferencia

`lead.details["preferencia_contacto"]` ya viene del reporte (columna
"Preferred mean of contact"). Match: `"whatsapp" in normalize(texto)` —
cubre "vía whatsapp", "WhatsApp", etc.

### Botón Send To Whatsapp

Botón del encabezado de la ficha (visible en capturas del usuario, texto
"Send To Whatsapp"). Script dedicado sobre `CLOSURE_HELPERS_SCRIPT`:
buscar `button`/`[role="button"]`/enlaces visibles cuyo texto normalizado
sea "send to whatsapp" (o contenga "whatsapp"), exacto preferido. Clic
JS como el resto de acciones.

### Toast de confirmación

Toast verde con texto "Message sent to Whatsapp! Please follow status...".
Espera ~15 s buscando un elemento visible tipo toast
(`[class*="toast"], lightning-toast-container, [role="status"], [role="alert"]`)
cuyo texto contenga "whatsapp" y ("sent"/"envi"); cierre: botón X dentro
del toast (`button[title*="lose"], .slds-notify__close, button` con icono
close). Si no aparece → `wa_no_confirmado`, sin reintento.

### Toggle UI

Mismo patrón que `solo_listar`:

- `monitor_state["enviar_whatsapp"]` (default `False`).
- Endpoint `/api/monitor/whatsapp` POST `{enabled: bool}` (o se reusa el
  toggle genérico si existe — revisar).
- Checkbox en la UI del monitor junto a "Modo prueba".
- SSE: el estado se propaga con el snapshot existente.

### Outcomes `wa_*`

- `wa_ok`: clic + toast visto y cerrado.
- `wa_no_toast`→`wa_no_confirmado`: clic hecho, toast no visto (no reintenta).
- `wa_sin_boton`: no se encontró `Send To Whatsapp` en el encabezado.
- `wa_error:<Exc>`: excepción durante el envío.
- Sin segmento `wa` cuando la rama no aplica (comportamiento actual).

### Riesgos

- **Doble envío**: nunca reintentar el clic tras `wa_no_confirmado`; los
  resultados `tomado` son terminales así que un lead no se reprocesa.
- **Botón con otro nombre** en versiones futuras de SF: el outcome
  `wa_sin_boton` + diag lo delata.
- **Fecha/hora**: `datetime.now()` local de la máquina del operador
  (Argentina) — coincide con la convención de los auxiliares.
