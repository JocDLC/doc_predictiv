## 1. Fuente y pruebas

- [x] 1.1 Localizar las fuentes de los tres HTML publicados, definir tres favicons SVG y añadir un publicador determinístico que los inserte solo en el `<head>` de las copias Archify servidas. Verificación: las copias publicadas y la presentación contienen un `rel="icon"` local, y el cuerpo Archify permanece intacto.
- [x] 1.2 Añadir pruebas unitarias y smoke que exijan el tipo SVG, las tres firmas visuales y la ausencia de dependencias externas. Verificación: casos válidos, favicon repetido y mutación del cuerpo comprobados.

## 2. Generación y publicación

- [x] 2.1 Regenerar y finalizar el workflow de negocio con Archify. Verificación: `validate`, `deliver`, `check` y `browser-check` pasan en recibos nuevos.
- [x] 2.2 Regenerar y finalizar el diagrama de arquitectura con Archify sin modificar su contenido de arquitectura. Verificación: los cuatro gates pasan antes de que el publicador agregue su favicon a la copia servida.
- [x] 2.3 Publicar las dos salidas Archify y la presentación de productividad con sus favicons. Verificación: las tres URLs locales responden 200 y sirven el icono esperado.

## 3. Harness y cierre

- [x] 3.1 Ejecutar formato, lint, pruebas, smoke y validación OpenSpec. Verificación: harness completo aprobado (166 + 32 pruebas), tres pruebas de favicons, smoke y las tres URLs locales 200. La comprobación visual final queda para la revisión del usuario en su navegador.
- [x] 3.2 Actualizar Graphify y registrar la evidencia de publicación, manteniendo el cambio sin archivar hasta aprobación explícita. Verificación: `graphify update .`, `openspec validate --changes` y `git diff --check` pasan.
