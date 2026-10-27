## Context

`#viewMonitor` en `documentador_predictivo.html` muestra hoy: título, texto
explicativo, banners de aviso, una línea `#monitorStatus` gris (13 px) y una fila
`.actions` que mezcla 4 botones con 4 checkboxes y "Probar aviso".
`renderMonitor()` arma el texto de estado concatenando partes con " · ", sin
distinguir el estado elegido por el usuario (`enabled`) del estado efectivo
(`paused_reason`, `bot_running`). Por eso aparecen frases contradictorias como
"Monitor activo · pausado: fuera del horario configurado".

La UI se testea en `automation_salesforce/tests/test_ui_monitor.py` corriendo
el `<script>` real en Node `vm` con stubs de DOM (`__elements[id]`,
`textContent`, `classList`, `setAttribute` según el stub).

## Goals / Non-Goals

**Goals:**
- Que el estado efectivo del monitor se entienda de un vistazo (color + texto).
- Reemplazar el botón de toggle por un switch dentro de la tarjeta de estado.
- Ordenar las opciones en dos grupos con título.

**Non-Goals:**
- Cambios en backend, API o en `monitor_state.json`.
- Exponer el intervalo del monitor por API (el texto "~2 minutos" queda fijo).
- Rediseñar la tabla de resultados, la configuración plegable o los banners de eventos.

## Decisions

1. **Función pura `monitorVisualState(state)`** que devuelve
   `{ level: "ok"|"wait"|"alert"|"off", title, details[] }`. `renderMonitor()` solo
   la pinta. Así la precedencia del semáforo queda testeable sin DOM y no se
   repite lógica. *Alternativa*: seguir concatenando en `renderMonitor()`, que
   descartamos porque mezcla la lógica con el render.
2. **Clasificación de motivos en constantes** (`MONITOR_ALERT_REASONS`,
   `MONITOR_WAIT_REASONS`) reutilizando `MONITOR_PAUSE_LABELS` para los textos
   (se quita el prefijo "pausado: " al armar el título).
3. **El switch es un `<button role="switch" aria-checked>`** con id
   `monitorToggle` (se conserva el id para reutilizar el listener
   `toggleMonitor`). No usamos `<input type=checkbox>` porque el estado lo manda
   el servidor y no queremos que el click lo cambie localmente antes de la
   respuesta.
4. **La tarjeta reutiliza `#monitorStatus`** para el título y suma
   `#monitorStatusDetail` para la línea de detalle; el nivel se aplica con las
   clases `.state-ok/.state-wait/.state-alert/.state-off` en `#monitorStateCard`.
   Los mensajes transitorios existentes ("Revisión manual en curso…", errores de
   lectura) siguen escribiendo en `#monitorStatus`; ante un error de lectura la
   tarjeta pasa a `state-alert`.
5. **Colores**: verde `--accent2` (#0e7a3d), ámbar #b45309, rojo #b91c1c, gris
   `--muted`; fondo tenue del mismo tono y borde izquierdo de 5 px. Siempre texto
   y punto de color juntos (no depender solo del color, por accesibilidad).
6. **Opciones**: `.monitor-options` con CSS grid de 2 columnas
   (`grid-template-columns: 1fr 1fr`) que pasa a 1 columna debajo de 720 px;
   cada grupo es un `<fieldset>` con `<legend>`.
7. **Orden del layout**: título → tarjeta de estado → banners → fila de
   acciones (Revisar ahora / Actualizar / Reiniciar navegador) → opciones → texto
   explicativo → configuración plegable.

## Risks / Trade-offs

- [Los tests existentes validan el texto del botón ("pausar" / "Activar monitor")]
  → se reemplazan por asserts equivalentes sobre `aria-checked` y el semáforo; requiere OK explícito del usuario (AGENTS.md: no debilitar tests sin autorización).
- [El cambio en curso `renombrar-ui-gestion-leads` toca el mismo HTML]
  → hacer los cambios acotados a `#viewMonitor` y su CSS; revisar `git diff` antes de empezar.
- [El stub de DOM puede no soportar `setAttribute`] → extender el stub del
  harness de tests si hace falta (sin cambiar los checks existentes).
- ["~2 minutos" fijo puede quedar desactualizado si cambia `MONITOR_INTERVAL_SECONDS`]
  → aceptado; queda anotado como pregunta abierta.

## Open Questions

- ¿Conviene exponer el intervalo en `/api/monitor` para que el texto sea dinámico? (fuera de alcance por ahora)
