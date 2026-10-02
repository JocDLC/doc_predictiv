## Context

`documentador-architecture.html` es un diagrama Archify autocontenido útil para arquitectura y auditoría técnica. Debe conservarse intacto.

El primer gráfico de contratos de negocio se generó con una plantilla HTML propia. La revisión de usuario no fue aprobatoria por tres causas: no tenía la calidad visual del artefacto Archify, mezclaba en un único recorrido actividades que pertenecen a dos procesos y afirmaba que XLSX era una entrada disponible. La inspección de la aplicación confirma que ambos selectores aceptan `.csv,.txt`, usan lectura de texto y esperan un identificador de Lead; el soporte XLSX figura como trabajo pendiente en otro cambio OpenSpec.

El dominio se entiende mejor como dos intercambios de información:

1. Salesforce entrega una base; el Documentador la prepara; Wolkvox recibe el archivo de campaña.
2. Wolkvox entrega resultados con intentos; el Documentador los organiza; Salesforce recibe la documentación, manualmente o por medio del bot.

## Goals / Non-Goals

**Goals:**

- Crear una visualización Archify de calidad `showcase` para una audiencia no técnica.
- Separar inequívocamente los caminos Salesforce → Wolkvox y Wolkvox → Salesforce.
- Mostrar el origen, la transformación y el destino de cada conjunto de información.
- Dar a cada macrofunción un contrato breve y trazable a OpenSpec.
- Diferenciar capacidad vigente, actividad externa/manual y funcionalidad futura.
- Detectar mecánicamente referencias rotas, contratos incompletos, afirmaciones de formato incorrectas y contenido sensible.
- Conservar intacto el gráfico técnico y mantener el prototipo rechazado solo como antecedente.

**Non-Goals:**

- Modificar la importación de archivos o implementar XLSX.
- Cambiar la integración con Salesforce, Wolkvox o el comportamiento del bot.
- Reemplazar Graphify o el diagrama técnico.
- Mostrar todas las funciones, clases, selectores o pruebas del repositorio.
- Convertir pasos manuales o externos en automatizaciones aparentes.
- Incorporar datos reales como ejemplos o evidencia.

## Decisions

### 1. Archify Workflow v2 será el único formato de publicación vigente

La nueva vista se autorará como un candidato Archify de tipo `workflow`, versión de esquema 2, y se finalizará con perfil de calidad `showcase`. Se usará el estilo visual clásico y estático para mantener coherencia con el gráfico técnico y evitar movimiento innecesario durante una presentación.

El candidato, el HTML, los recibos y la evidencia de revisión del navegador se guardarán en un nuevo directorio `.archify/workflow-<slug>-<fecha>/`. El HTML técnico existente y su directorio no se tocarán. La plantilla HTML propia ya creada no se publicará como la vista vigente.

### 2. Dos caminos separados, unidos por el contexto del negocio

El workflow usará grupos o fases claramente rotulados y carriles que distingan responsabilidades. La composición inicial será:

**Camino 1 — Preparar campaña para Wolkvox**

1. `CSV exportado de Salesforce` — archivo de entrada externo.
2. `Preparar base de campaña` — validar, normalizar, organizar y excluir registros no utilizables.
3. `Generar CSV para Wolkvox` — archivo de salida del sistema.
4. `Cargar campaña en Wolkvox` — acción externa/manual claramente identificada.

**Camino 2 — Documentar resultados en Salesforce**

1. `CSV de intentos descargado de Wolkvox` — archivo de entrada externo.
2. `Organizar intentos de llamada` — agrupar y preparar la información por Lead.
3. `Elegir información a documentar` — conformar el lote de trabajo.
4. Bifurcación visible:
   - `Documentar manualmente en Salesforce`.
   - `Documentar automáticamente con el bot`.
5. `Confirmar documentación en Salesforce` — resultado y verificación.
6. `Consultar resultados y productividad` — seguimiento posterior.

La corrección segura será una ruta secundaria asociada al seguimiento, no un paso obligatorio del flujo principal.

### 3. El movimiento de información domina la composición

Los nodos de archivo indicarán origen y formato. Los nodos de actividad expresarán un verbo de negocio. Las aristas describirán qué información pasa al siguiente paso, no detalles de llamadas técnicas. Las acciones fuera de la aplicación se rotularán como `Externo` o `Manual` para no atribuir automatización inexistente.

La vista inicial no mostrará nombres de archivos internos, funciones, puertos, Selenium, selectores ni protocolos.

### 4. Contratos compactos mediante recursos nativos de Archify

Cada macrofunción tendrá:

- una etiqueta corta;
- un subtítulo `entrada → resultado`;
- una regla o estado breve cuando aporte comprensión;
- una tarjeta de contrato con `Qué recibe`, `Qué entrega`, `Regla principal` y `Si falla`;
- referencias OpenSpec en `sources` o en la evidencia asociada.

El recorrido debe poder entenderse sin abrir tarjetas. Las tarjetas agregan precisión sin transformar el gráfico en documentación técnica. Implementación y pruebas solo aparecerán como evidencia secundaria.

### 5. La verdad operativa se obtiene de evidencia implementada

La fuente normativa se resolverá contra `openspec/specs/` y delta specs funcionales seleccionados, pero una afirmación de disponibilidad requerirá también evidencia en la implementación y las pruebas.

Un delta spec activo no equivale a una capacidad desplegada. Por tanto:

- los archivos de entrada se describirán como CSV;
- XLSX no aparecerá como formato aceptado mientras siga pendiente;
- los pasos manuales o externos se identificarán como tales;
- una evidencia ausente se mostrará como pendiente, nunca como aprobada.

El nombre aprobado para el inicio del primer camino será `CSV exportado de Salesforce`; se descartan `Cargar BD` y `Cargar base de Leads` porque ocultan el origen y sugieren formatos no confirmados.

### 6. Fuente contractual y verificación determinística

La información contractual podrá mantenerse en una fuente estructurada separada si facilita las pruebas, pero el artefacto publicado siempre será el resultado nativo de Archify. El generador o adaptador deberá producir un candidato `workflow` válido, no una plantilla HTML alternativa.

Las verificaciones cubrirán:

- esquema Archify y referencias internas;
- existencia de los dos caminos y de la bifurcación manual/bot;
- contrato completo por macrofunción;
- referencias OpenSpec resolubles y no ambiguas;
- prohibición de anunciar XLSX como vigente;
- diferenciación entre pasos del sistema, manuales y externos;
- datos sensibles y canarios;
- accesibilidad, consola, tamaños habituales y comprensión visual;
- conservación del SHA-256 del gráfico técnico.

### 7. Revisión visual y de comprensión antes de publicar

Después de finalizar el workflow se realizará una inspección en navegador y una prueba guiada con audiencia no técnica. La revisión solo será aprobatoria si la persona puede:

1. explicar ambos caminos sin asistencia técnica;
2. identificar qué archivo entra y cuál sale en cada camino;
3. distinguir documentación manual de documentación con bot;
4. explicar al menos tres contratos.

Un harness verde no sustituye esta aceptación de comprensión.

## Risks / Trade-offs

- **Demasiado contenido puede volver a enredar el flujo** → limitar la vista inicial a macrofunciones y mover reglas detalladas a tarjetas.
- **Separar los caminos puede ocultar que pertenecen al mismo ciclo operativo** → conservarlos en un único workflow, con títulos paralelos y actores compartidos.
- **Archify puede restringir interacciones personalizadas del prototipo** → priorizar consistencia, legibilidad y recursos nativos sobre personalización visual.
- **Los requisitos futuros pueden confundirse con funciones disponibles** → exigir evidencia de implementación y prueba para toda etiqueta de disponibilidad.
- **La ruta manual y la del bot pueden sugerir resultados idénticos sin validación** → describir el resultado contractual y la verificación propia de cada ruta.
- **La terminología puede variar entre equipos** → usar Salesforce y Wolkvox como anclas de origen/destino y validar el vocabulario en la revisión final.

## Migration Plan

1. Conservar la evidencia del prototipo rechazado y registrar que no obtuvo aprobación de Fase 5.
2. Corregir el modelo contractual para dos caminos, CSV vigente y rutas manual/bot.
3. Generar un nuevo candidato Archify Workflow v2 en un directorio independiente.
4. Validar y finalizar el candidato con calidad `showcase` y raíz del repositorio.
5. Ejecutar pruebas, smoke de navegador, controles de privacidad y comparación del hash técnico.
6. Presentar el nuevo workflow junto al gráfico técnico y registrar la revisión de comprensión.
7. Publicar la nueva URL solo después de aprobación explícita.

Rollback: retirar el nuevo directorio y la URL del workflow corregido. El gráfico técnico, la aplicación y el prototipo histórico permanecen disponibles y sin cambios.

## Open Questions

No quedan decisiones funcionales abiertas para iniciar la corrección. La disposición exacta de carriles, tarjetas y saltos visuales se ajustará durante la inspección del candidato Archify sin alterar los dos caminos aprobados.
