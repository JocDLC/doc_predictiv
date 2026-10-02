## ADDED Requirements

### Requirement: Favicons locales diferenciados
El sistema SHALL declarar un favicon SVG embebido y distinguible en cada una de las páginas locales de negocio, arquitectura y productividad. Cada favicon MUST ser autocontenido, MUST NOT descargar recursos externos y MUST diferenciar visualmente la finalidad de su página.

#### Scenario: Pestañas identificables
- **WHEN** una persona abre simultáneamente las tres URLs locales
- **THEN** el navegador recibe un favicon propio en cada pestaña y no utiliza el icono genérico

#### Scenario: Sin dependencia externa
- **WHEN** se inspecciona cualquiera de los tres HTML publicados
- **THEN** el favicon usa una URL `data:image/svg+xml` y no existe una solicitud HTTP externa para obtenerlo

### Requirement: Preservación de artefactos Archify
Los favicons de los diagramas de negocio y arquitectura SHALL originarse en sus candidatos Archify y MUST publicarse solo después de una finalización válida con calidad `showcase`.

#### Scenario: Regeneración verificable
- **WHEN** se actualiza un favicon de un diagrama Archify
- **THEN** los gates `validate`, `deliver`, `check` y `browser-check` pasan antes de publicar el HTML actualizado

### Requirement: Verificación de publicación local
El harness SHALL comprobar el favicon esperado y la respuesta satisfactoria de las tres URLs locales.

#### Scenario: Smoke de las páginas diferenciadas
- **WHEN** se ejecuta la comprobación de publicación local
- **THEN** cada URL responde con estado 200 y contiene el favicon SVG que le corresponde
