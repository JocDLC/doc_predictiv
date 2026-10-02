## 1. Fuente y pruebas

- [ ] 1.1 Localizar las fuentes de los tres HTML publicados y añadir una configuración de favicon SVG distintiva por página. Verificación: los candidatos y la presentación contienen un `rel="icon"` local.
- [ ] 1.2 Añadir pruebas unitarias y smoke que exijan el tipo SVG, las tres firmas visuales y la ausencia de dependencias externas. Verificación: los casos válidos pasan y un favicon ausente o incorrecto falla.

## 2. Generación y publicación

- [ ] 2.1 Regenerar y finalizar el workflow de negocio con Archify. Verificación: `validate`, `deliver`, `check` y `browser-check` pasan en recibos nuevos.
- [ ] 2.2 Regenerar y finalizar el diagrama de arquitectura con Archify sin modificar su contenido de arquitectura. Verificación: los cuatro gates pasan y el HTML declara su favicon.
- [ ] 2.3 Publicar las dos salidas Archify y la presentación de productividad con sus favicons. Verificación: las tres URLs locales responden 200 y sirven el icono esperado.

## 3. Harness y cierre

- [ ] 3.1 Ejecutar formato, lint, pruebas, smoke, validación OpenSpec y revisión visual de las pestañas. Verificación: todos los controles devuelven código cero y las capturas muestran iconos diferenciados.
- [ ] 3.2 Actualizar Graphify y registrar la evidencia de publicación, manteniendo el cambio sin archivar hasta aprobación explícita. Verificación: `graphify update .`, `openspec validate --changes` y `git diff --check` pasan.
