# Reintentar el panel "Contact Client" con recarga de la ficha

## Why

~17% de las tomas terminan con `sin_panel`: el panel "Contact Client"
(estatuto de la llamada) nunca renderiza — error transitorio de Salesforce o
un formulario de edición colgado que lo tapa. Su Save es lo que mueve
`Estado del candidato` de "Nuevo" a "En curso", así que esos leads quedan
tomados por el bot pero visibles como nuevos en la bandeja: otro bot o un
auxiliar puede volver a tomarlos y Compliance ve la toma sin gestión.

## What Changes

- Tras la ventana inicial y el chequeo tardío, si el panel sigue ausente el
  monitor espera ≤3 s, **recarga la página del lead** y vuelve a buscar el
  panel con la misma ventana inicial. Si aparece, pulsa su Save.
- Nuevo outcome `panel_tras_reload` en `finalizacion`; el caso no resuelto
  sigue reportándose como `sin_panel` con su diagnóstico actual.
- Si la recarga ocurrió, la marca documentada en `Otra información` se
  re-verifica (el reload descarta una edición inline abierta).
- Sin cambios en Pick Up, cobertura, reasignación ni envío de WhatsApp.

## Impact

- `automation_salesforce/lead_monitor.py`: `finalize_pick_up` +
  `_save_contact_panel_after_reload` + `RELOAD_PANEL_WAIT_SECONDS`.
- `automation_salesforce/tests/test_lead_monitor.py`: regresiones del
  reintento y de la re-verificación.
