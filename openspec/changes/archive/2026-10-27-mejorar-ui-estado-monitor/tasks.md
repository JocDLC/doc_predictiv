## 1. Tests primero

- [x] 1.1 Pedir autorización al usuario para reemplazar los asserts del texto del botón en `test_ui_monitor.py` (líneas "toggle dice pausar" / "toggle ofrece activar") por asserts del switch
- [x] 1.2 Agregar tests de `monitorVisualState()`: verde (activo sin motivo), ámbar (`fuera_de_horario`, `run_activo`, `bot_running`), rojo (`session_lost`, `navegador_trabado`, `sin_bandejas`, `error:x`), gris (`enabled=false` con motivo → detalle "último ciclo")
- [x] 1.3 Agregar tests de render: clase de nivel en `monitorStateCard`, `aria-checked` y etiqueta del switch, detalle con "modo prueba" / "WhatsApp auto" / "última revisión"; extender el stub de DOM (`setAttribute`) si hace falta

## 2. Lógica de estado

- [x] 2.1 Agregar constantes `MONITOR_ALERT_REASONS` / `MONITOR_WAIT_REASONS` y la función pura `monitorVisualState(state)`
- [x] 2.2 Refactorizar `renderMonitor()` para pintar tarjeta + switch desde `monitorVisualState()`; ante error en `loadMonitorState()` poner la tarjeta en `state-alert`

## 3. Markup y estilos

- [x] 3.1 Crear la tarjeta `#monitorStateCard` (punto de color, `#monitorStatus`, `#monitorStatusDetail`, switch `#monitorToggle` con `role="switch"`)
- [x] 3.2 Mover los botones de acción a su propia fila debajo de la tarjeta
- [x] 3.3 Agrupar opciones en `.monitor-options` con fieldsets "Comportamiento" y "Avisos" (ids sin cambios)
- [x] 3.4 Mover el texto explicativo debajo de las opciones y actualizar a "cada ~2 minutos" (también el mensaje de revisión manual si corresponde)
- [x] 3.5 CSS: `.monitor-state-card` + niveles, `.switch`, grid responsivo de `.monitor-options`

## 4. Verificación

- [x] 4.1 Correr la suite completa de tests y el linter
- [x] 4.2 Verificación manual en el navegador de los 4 estados (verde/ámbar/rojo/gris) y del switch
- [x] 4.3 Actualizar CHANGELOG.md y `graphify update .`
