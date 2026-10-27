## Why

El proyecto creció: ya no solo documenta el predictivo, también prepara campañas, monitorea bandejas, toma y reasigna leads y los distribuye. El nombre visible "Gestión de Campañas Predictivas" ya no lo representa. El nombre nuevo es **"Automatización Gestión de Leads"**. Además, la UI necesita una visual más moderna, alineada con la lámina "AS IS Process" (LBS REC). Todavía no se menciona IA: falta definir dónde va.

## What Changes

- Título de pestaña y header de la UI: "Automatización Gestión de Leads".
- Marca del header: "RENAULT GROUP" + "LBS REC".
- Rediseño visual **"moderno claro"** solo con CSS: header con degradado azul a violeta, tarjetas de módulo con número, ícono de color propio por módulo, bordes redondeados y sombras suaves, botones y tablas más limpios.
- Texto introductorio de la pantalla de inicio actualizado al alcance nuevo (preparar, documentar, monitorear, distribuir).
- **Restricción de rendimiento**: sin fuentes externas, sin `backdrop-filter`/`filter: blur`, sin animaciones infinitas ni transiciones en filas de tablas. La UI no debe sumar carga de CPU al monitor.
- Sin cambios en IDs, clases usadas por el JS, endpoints ni lógica.
- Fuera de alcance (queda registrado como pendiente en MEMORY.md):
  - Renombre completo de archivos y carpetas (`documentador_predictivo.html`, `dist/DocumentadorPredictivo`, ZIP, `INICIAR.bat`, `verificar_pc.py`).
  - Migración a un layout con **sidebar** cuando todo esté documentado.

## Capabilities

### New Capabilities
- `identidad-visual-ui`: nombre visible de la aplicación, marca del header y lineamientos visuales/rendimiento de la UI.

### Modified Capabilities

## Impact

- `documentador_predictivo.html`: bloque `<style>`, `<title>`, `<header>` y textos de la vista Home. El `<script>` no se toca.
- `dist/DocumentadorPredictivo/app/documentador_predictivo.html`: sincronización del archivo.
- `MEMORY.md`: pendientes (renombre completo y sidebar).
- Tests UI existentes (`test_ui_monitor`, `test_ui_closure`, `test_ui_documentation_state`): deben seguir pasando sin modificaciones.
