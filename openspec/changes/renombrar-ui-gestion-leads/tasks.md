## 1. Línea base

- [ ] 1.1 Ejecutar los tests de UI (`test_ui_monitor`, `test_ui_closure`, `test_ui_documentation_state`) y registrar que pasan antes del cambio

## 2. Nombre y marca

- [ ] 2.1 Cambiar `<title>` y `<h1>` a "Automatización Gestión de Leads"
- [ ] 2.2 Agregar "LBS REC" (`.brand-sub`) junto a "RENAULT GROUP" en el header
- [ ] 2.3 Actualizar el texto introductorio de Home al alcance nuevo (sin mencionar IA)

## 3. Visual moderna clara (CSS)

- [ ] 3.1 Redefinir variables `:root` (paleta azul/violeta, `--heading`, `--accent-hover`, radios, sombras) y reemplazar colores hardcodeados equivalentes
- [ ] 3.2 Header con degradado estático azul a violeta
- [ ] 3.3 Tarjetas de Home: `.module-num` + modificadores de color por módulo, hover liviano
- [ ] 3.4 Pulir botones, inputs, cards, paneles, badges y encabezados de tabla con la paleta nueva, manteniendo clases e IDs
- [ ] 3.5 Agregar `@media (prefers-reduced-motion: reduce)` y verificar que no haya `backdrop-filter`, `blur(`, `@import`, `url(http` ni animaciones infinitas

## 4. Verificación y cierre

- [ ] 4.1 Ejecutar los tests de UI y ruff: todo pasa sin modificar tests
- [ ] 4.2 Verificación visual de Home, Preparar, Documentar, Monitor y Distribuir en el navegador
- [ ] 4.3 Sincronizar el HTML a `dist/DocumentadorPredictivo/app/` y verificar con `diff`
- [x] 4.4 Registrar en MEMORY.md los pendientes: renombre completo del proyecto y migración a sidebar
