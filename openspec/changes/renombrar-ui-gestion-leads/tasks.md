## 1. Línea base

- [x] 1.1 Ejecutar los tests de UI (`test_ui_monitor`, `test_ui_closure`, `test_ui_documentation_state`) y registrar que pasan antes del cambio

## 2. Nombre y marca

- [x] 2.1 Cambiar `<title>` y `<h1>` a "Automatización Gestión de Leads"
- [x] 2.2 Agregar "GBS REC" (`.brand-sub`) junto a "RENAULT GROUP" en el header
- [x] 2.3 Actualizar el texto introductorio de Home al alcance nuevo (sin mencionar IA)

## 3. Visual moderna clara (CSS)

- [x] 3.1 Ajustar variables `:root` a la variante azul discreto aprobada, con sombras mínimas
- [x] 3.2 Restaurar el degradado azul-violeta y marca blanca del header a pedido del usuario
- [x] 3.3 Tarjetas de Home con fondo azul intenso y texto/iconos blancos en hover y foco, sin desplazamiento
- [x] 3.4 Pulir botones, inputs, cards, paneles, badges y encabezados de tabla con la paleta nueva, manteniendo clases e IDs
- [x] 3.5 Agregar `@media (prefers-reduced-motion: reduce)` y verificar que no haya `backdrop-filter`, `blur(`, `@import`, `url(http` ni animaciones infinitas
- [x] 3.6 Restaurar los colores originales de estados, avisos, controles y tabla del Monitor a pedido del usuario

## 4. Verificación y cierre

- [x] 4.1 Ejecutar los tests y ruff: 539 tests OK, lint OK; contraste de texto/acento >= 4.5:1
- [ ] 4.2 Verificación visual de Home, Preparar, Documentar, Monitor y Distribuir en el navegador
- [x] 4.3 Sincronizar el HTML a `dist/DocumentadorPredictivo/app/` y verificar con `cmp`
- [x] 4.4 Registrar en MEMORY.md los pendientes: renombre completo del proyecto y migración a sidebar

Revisión de la muestra B: el usuario pidió recuperar el degradado del header,
los colores del monitor y fondo azul intenso al pasar el mouse por las tarjetas.
Pendiente en 4.2: valoración de esta revisión y de las demás vistas.
