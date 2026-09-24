## Why

La lista local ya permite identificar los Leads `AR_LEAD_QUALIF`, pero el equipo
debe iniciar y completar manualmente la documentación de cada registro. El flujo
deben permitir seleccionar un lote desde la misma UI, documentar cada Lead en
Salesforce y conservar la lista visible con el resultado de cada operación.

## What Changes

- Añadir selección por Lead y una acción **Documentar seleccionados** a la UI
  local existente.
- Incorporar un puente local interno, iniciado por `run_leads_ui.py`, para recibir
  el lote seleccionado sin añadir una segunda interfaz visible.
- Procesar el lote de a un Lead: abrir el registro en una pestaña Salesforce,
  leer y conservar `Otra información`, añadir los intentos de Wolkvox, verificar
  el valor escrito y guardar el registro.
- Publicar el estado por Lead en la UI: pendiente, procesando, documentado o
  error; mantener disponibles las opciones manuales para los errores.
- Persistir resultados locales sin texto de comentarios ni datos personales, para
  que una ejecución interrumpida pueda revisarse y reintentarse de forma segura.

## Capabilities

### New Capabilities

- `documentacion-automatica-desde-ui`: coordinación local de lotes seleccionados,
  escritura y guardado verificados en Salesforce, y resultados por Lead.

### Modified Capabilities

- `lista-leads-sin-gestion`: la UI de lectura local permitirá seleccionar Leads,
  iniciar documentación y reflejar su estado sin cerrarse.

## Impact

- Afecta `automation_salesforce/leads_ui.py`, `run_leads_ui.py`, la automatización
  existente de comentarios y sus pruebas.
- Salesforce se modifica únicamente en el campo `Otra información` de Leads
  seleccionados y confirmados por el operador.
- No se añaden servicios externos, credenciales ni una interfaz distinta de la UI
  local actual.
