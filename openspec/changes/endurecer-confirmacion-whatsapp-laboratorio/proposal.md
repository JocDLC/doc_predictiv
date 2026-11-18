## Why

El piloto registró documentación persistida y envíos sin confirmación observable. Eso no permite atribuir los 30 casos históricos al detector ni afirmar entrega de mensajes. El detector actual acepta coincidencias amplias, no distingue avisos previos al clic y no conserva evidencia suficiente para reconstruir el resultado.

## What Changes

- Instrumentar y correlacionar la confirmación con la operación, registro y pestaña; observar antes del clic y conservar eventos transitorios.
- Rechazar errores, avisos previos, ajenos o ambiguos; mantener separados documentación, acción aceptada por Salesforce y entrega al destinatario.
- Fortalecer identidad, clic único y bloqueo de reenvío, incluyendo otra campaña/importación dentro del laboratorio.
- Crear pruebas adversariales determinísticas y una fixture local con ambos motores antes de otro piloto.
- Conservar resultados por corrida y evidencia mínima consultable en el laboratorio; distinguir comparación de lectura de auditoría del texto persistido.
- Medir tiempos pareados sin mezclar descartados de 0 segundos ni confundir operaciones con leads únicos.

## Capabilities

### New Capabilities

- `laboratorio-confirmacion-segura`: evidencia de confirmación, identidad, aislamiento, persistencia y prevención de duplicados.
- `laboratorio-validacion-adversarial`: escenarios reproducibles, auditoría cruzada y criterios medibles para habilitar otro piloto.

### Modified Capabilities

Ninguna spec principal existente define el laboratorio. Revisar compatibilidad con el cambio abierto `envio-whatsapp-automatico` sin modificar su alcance implícitamente.

## Impact

Adaptadores `agent_browser.py` y `laboratory_browser.py`, orquestador `run_laboratory_queue.py`, journal `laboratory_store.py`, contratos/métricas, endpoints existentes en `ui_server.py` y resultados en `documentador_predictivo.html`. Tests existentes de laboratorio y nueva fixture local si no existe una adecuada.

SDD: modifica mecánica Salesforce y contratos de evidencia. Este cambio entrega planificación y diagnóstico reproducible; la implementación productiva queda para el agente ejecutor. No se reenvían los casos históricos ambiguos ni se declara una migración completa.
