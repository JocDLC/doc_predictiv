## Context

Las páginas locales de negocio y arquitectura son HTML generados por Archify y la página de productividad es un HTML autónomo. Ninguna declara un icono de pestaña, por lo que el navegador muestra el icono genérico. El esquema de Archify no admite campos de favicon ni HTML arbitrario en `<head>`, y sus recibos validan el HTML que genera.

## Goals / Non-Goals

**Goals:**

- Diferenciar visualmente las tres pestañas con favicons SVG pequeños y legibles.
- Mantener los recursos autocontenidos y sin solicitudes externas.
- Mantener la trazabilidad y las validaciones nativas de Archify para sus dos páginas.

**Non-Goals:**

- Rediseñar el contenido de las páginas o sus títulos.
- Crear una marca comercial nueva o usar logotipos de Salesforce, Wolkvox o Renault.
- Alterar las integraciones de negocio o el comportamiento de la aplicación.

## Decisions

1. Cada HTML declarará un favicon `data:image/svg+xml` embebido. Es compatible con las tres URLs locales, no exige servidor adicional y evita cachear archivos con el mismo nombre.
2. Los favicons serán geométricos y funcionales, no marcas de terceros: flujo turquesa para negocio, capas azules para arquitectura y gráfica violeta para productividad. Así se distinguen incluso en pestañas compactas.
3. Los diagramas se finalizarán nuevamente con `finalize` y un publicador del proyecto insertará de forma determinística un único `<link rel="icon">` inmediatamente antes de `</head>` en la copia servida. Verificará que el cuerpo y todos los demás bytes del HTML validado se conservan. La presentación autónoma se editará en su fuente.
4. Las pruebas inspeccionarán el `rel="icon"`, el tipo SVG en línea y una firma visual única por página, además de comprobar que las URLs locales responden.

## Risks / Trade-offs

- [Caché del navegador] → usar URL de datos embebida para que cada versión HTML transporte su icono.
- [Cambiar HTML Archify sin recibo] → regenerar y finalizar siempre desde el candidato; el decorador publicado solo inserta el favicon en `<head>` y verifica que el cuerpo coincide.
- [Iconos demasiado complejos] → limitar los SVG a formas básicas visibles a 16×16 píxeles.

## Migration Plan

1. Añadir metadatos de favicon a las fuentes de cada página.
2. Regenerar y finalizar los dos diagramas Archify en directorios de evidencia nuevos.
3. Decorar y publicar las copias verificadas, y ejecutar smoke, pruebas y revisión visual de pestañas.
4. Si hay una regresión, retirar los enlaces de favicon y republicar el último HTML Archify con recibo válido.

## Open Questions

No quedan decisiones abiertas: se usarán los tres iconos geométricos definidos en esta propuesta.
