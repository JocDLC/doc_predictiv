## Why

El diagrama técnico actual explica correctamente la arquitectura, pero no está orientado a una audiencia operativa. El primer prototipo del gráfico de contratos tampoco resolvió esa necesidad: usó una visualización propia, mezcló dos recorridos de negocio y presentó XLSX como disponible aunque la aplicación actual solo procesa archivos de texto CSV.

Se necesita una segunda visualización, generada nativamente con Archify, que permita entender de dónde sale la información, cómo se transforma y a dónde llega, sin confundir comportamiento implementado con funcionalidad planificada.

## What Changes

- Sustituir el prototipo de visualización propia por un artefacto nativo **Archify Workflow v2**, con perfil visual `showcase` y una URL independiente.
- Conservar sin modificaciones el gráfico técnico `documentador-architecture.html`.
- Separar el proceso en dos caminos de negocio relacionados:
  1. **Salesforce → Wolkvox:** partir de un CSV exportado desde Salesforce, validarlo, organizarlo y generar el CSV correcto para cargar en Wolkvox, reduciendo tareas manuales.
  2. **Wolkvox → Salesforce:** partir de un CSV descargado desde Wolkvox con los intentos de llamada, organizar la información y preparar la documentación de Salesforce por una ruta manual o mediante el bot.
- Mostrar el movimiento de la información con etiquetas de negocio, distinguiendo archivos, actividades del sistema y acciones externas o manuales.
- Exponer para cada macrofunción un contrato breve: qué recibe, qué entrega, regla principal y qué ocurre si falla; la trazabilidad OpenSpec y técnica quedará disponible como evidencia progresiva.
- Reflejar únicamente capacidades operativas comprobadas. En particular, la carga actual se describirá como **CSV**; XLSX no se anunciará hasta que exista implementación y prueba verificable.
- Verificar de forma determinística estructura, trazabilidad, privacidad, accesibilidad, generación Archify y coexistencia con el gráfico técnico.

## Capabilities

### New Capabilities

- `business-contract-graph`: visualización Archify independiente de los dos recorridos principales del Documentador Predictivo, con contratos de negocio trazables a OpenSpec.

### Modified Capabilities

Ninguna capacidad operativa de la aplicación cambia. Esta corrección modifica únicamente la forma de documentar capacidades ya implementadas y su estado real.

## Impact

- Nuevo candidato JSON de tipo `workflow` y nuevo HTML finalizado por Archify en un directorio `.archify/workflow-*` independiente.
- Revisión de la fuente contractual y sus validadores para representar dos caminos y evitar afirmar soporte XLSX inexistente.
- Actualización de pruebas de estructura, contenido, accesibilidad, privacidad y smoke visual.
- Conservación del gráfico técnico y del prototipo rechazado como evidencia histórica; ninguno se considerará la vista de negocio vigente.
- Sin cambios en Salesforce, Wolkvox, datos de clientes ni comportamiento del bot durante esta fase de documentación.
