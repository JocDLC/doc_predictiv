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

### Toma y reasignación sin comentarios

Guardar Contact Client no escribe en `Otra información`. No se llama
al escritor de comentarios al tomar ni reasignar, independientemente de
la preferencia de contacto. El resultado incluye `sin_comentario`.
Si se reasigna, el WhatsApp automático queda forzado a off.
Solo un envío real habilitado al propio usuario conserva la documentación
del intento de WhatsApp.

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
- Campo con notas o marcas históricas → la toma y reasignación no lo editan.
