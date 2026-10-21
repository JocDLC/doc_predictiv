# Design: reasignacion-por-turno

## Decisiones

### Encargada activa por franja

`monitor_state.equipo` es una lista de personas:

```json
{"nombre": "Micaela Caetano", "franjas": [{"start": "09:00", "end": "12:00"}]}
```

`_encargada_activa(equipo, ahora)` devuelve la primera persona cuya
franja cubre la hora actual (reutiliza la lógica de `within_schedule`).
Si dos franjas solapan, gana la primera de la lista — se registra en el
diagnóstico.

### ¿Es el propio usuario?

`take_lead` ya lee el propietario tras el pickup (`read_record_owner`).
Si el nombre de la encargada normalizado coincide con ese propietario,
la franja es del usuario del bot → **flujo normal** (incluye WhatsApp
automático en AR). Sin flag extra — la comparación por nombre es la
fuente de verdad.

### Comentario con método

Lead reasignado: `Otra información` queda `Asignado - <método>` donde el
método se deriva de `preferencia_contacto` del lead (lo que pidió el
cliente en el formulario), no de la persona:

| preferencia del lead | texto |
|---|---|
| contiene `whatsapp` | `Asignado - Enviar Whatsapp` |
| contiene `llamad`/`telefon` | `Asignado - Llamarlo` |
| otro / vacío | `Asignado - Gestionarlo` |

Se reutiliza `_ensure_take_mark(mark_text=...)` con el mismo saneado y
verificación estricta. `drop_take_mark` NO aplica (la línea empieza con
`Asignado`, no es la marca solitaria). El WhatsApp automático queda
forzado a off para ese lead (`whatsapp=False`), pase lo que pase.

### Mecánica del modal (verificada en vivo)

1. Botón `aria-label="Cambiar propietario"` dentro del
   `records-record-layout-item` del campo `Propietario del candidato`
   — vive en **shadow DOM**: hay que descender por `shadowRoot`
   (`deepAll`), `querySelector` plano no lo ve.
2. Modal "Cambiar propietario de Candidato" → input
   `Buscar Usuarios…` (combobox) → tipear el nombre → esperar
   `[role="option"]`/`lightning-base-combobox-item` y elegir la opción
   cuyo texto normalizado contiene el nombre.
3. Confirmar con el botón `Cambiar propietario` del footer (jamás
   `Cancelar`), esperar el cierre del modal y **releer el propietario**
   para verificar el cambio.

### Outcomes

```
<panel>/<marca>/<contacto>
contacto: wa_*            (lead se queda con el bot — comportamiento actual)
          reasignado      (propietario verificado = encargada)
          reasignacion_error:lapiz|modal|opcion|confirmar|verificacion
```

Si la reasignación falla, el lead queda con el usuario del bot: dato
preservado, error explícito en `finalizacion` — nada se traga.

## Riesgos

- Nombre mal escrito en la UI → el lookup no matchea →
  `reasignacion_error:opcion`, lead queda con el bot. Mitigación: la UI
  muestra el recordatorio "nombre exacto como en Salesforce".
- Franjas solapadas entre personas → se toma la primera; queda en
  `finalize_diag`.
- Campo ya documentado por una toma previa con `Asignado` pelado → no se
  reescribe a `Asignado - <método>` (idempotencia conservadora).
