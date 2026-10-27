## Why

En la vista **Monitor de Bandeja** el estado del bot no se percibe: el botón
"Monitor activo — tocar para pausar" no tiene color que indique si corre, la
línea de estado se confunde con el texto explicativo y puede mostrar mensajes
contradictorios ("Monitor activo · pausado: fuera del horario configurado").
Además los checkboxes de opciones quedan dispersos en la fila de botones. Las
personas no saben de un vistazo si el monitor está tomando leads o no.

## What Changes

- Nueva **tarjeta de estado** arriba de la vista, con semáforo calculado a partir
  del estado *real* del monitor (no solo de `enabled`):
  - verde: activo y trabajando;
  - ámbar: activo pero en espera (fuera de horario, bot de documentación/cierre corriendo);
  - rojo: requiere atención (sesión de Salesforce vencida, navegador trabado, error del último ciclo, sin bandejas);
  - gris: apagado por el usuario.
  Texto principal grande en negrita y una línea de detalle (modo prueba,
  WhatsApp auto, última revisión).
- El botón "Monitor activo — tocar para pausar" se reemplaza por un **interruptor
  (switch) Encendido/Apagado** dentro de la tarjeta de estado. Usa el mismo
  endpoint `POST /api/monitor/toggle`.
- Los checkboxes se agrupan en **dos columnas con título**:
  - *Comportamiento*: Modo prueba, WhatsApp auto;
  - *Avisos*: Sonido, Notificar + botón "Probar aviso".
- Los botones "Revisar ahora", "Actualizar" y "Reiniciar navegador del bot"
  quedan en una fila propia debajo de la tarjeta.
- El texto explicativo pasa debajo de la tarjeta y se actualiza a "cada ~2
  minutos" (el intervalo del servidor pasó a 120 s).
- Sin cambios en el backend ni en la API.

## Capabilities

### New Capabilities
- `monitor-ui-estado`: presentación del estado del Monitor de Bandeja
  (semáforo, interruptor encendido/apagado y agrupación de opciones).

### Modified Capabilities
<!-- monitor-bandeja-leads aún no está archivada en openspec/specs/; su comportamiento no cambia. -->

## Impact

- `documentador_predictivo.html`: markup de `#viewMonitor`, CSS nuevo
  (`.monitor-state-card`, `.switch`, `.monitor-options`) y `renderMonitor()`.
- `automation_salesforce/tests/test_ui_monitor.py`: los asserts del texto del
  botón (`includes('pausar')`, `=== 'Activar monitor'`) se reemplazan por asserts
  del switch y del semáforo (requiere autorización explícita, ver tasks).
- Posible solapamiento con el cambio en curso `renombrar-ui-gestion-leads`
  (mismo archivo HTML): coordinar para evitar conflictos.
- `dist/` se regenera en el próximo build.
