## Context

El artefacto actual `documentador-architecture.html` es un diagrama Archify autocontenido con diez componentes, relaciones técnicas, pasaporte semántico y enlaces a fuentes verificadas. Sus etiquetas principales incluyen archivos, puertos, Selenium y detalles de persistencia. Es valioso para arquitectura y auditoría, pero no es la vista adecuada para explicar el producto a responsables operativos o de negocio.

OpenSpec ya describe la conducta esperada mediante requisitos y escenarios. Sin embargo, esos requisitos están distribuidos entre la especificación principal y varios cambios funcionales activos. La nueva vista debe sintetizarlos sin inventar comportamiento, mantener trazabilidad y permitir actualizaciones repetibles.

## Goals / Non-Goals

**Goals:**

- Crear una vista separada y comprensible del recorrido funcional completo.
- Dar a cada macrofunción un contrato uniforme derivado de OpenSpec.
- Mantener una separación visual entre explicación de negocio, norma OpenSpec y evidencia técnica.
- Detectar mecánicamente contratos incompletos, referencias rotas y contenido sensible.
- Conservar intacto el diagrama técnico existente.

**Non-Goals:**

- Reemplazar Graphify, Archify o el diagrama técnico.
- Mostrar todas las funciones, clases o tests del repositorio.
- Cambiar requisitos funcionales, automatización, Salesforce o archivos operativos.
- Generar descripciones de negocio directamente desde nombres de código sin revisión.
- Incorporar datos reales como ejemplos o evidencia.

## Decisions

### 1. Segundo artefacto, no modo adicional del gráfico actual

Se creará `documentador-business-contracts.html` junto al artefacto Archify existente. Tendrá URL, datos e interacciones propios. Esta separación evita regresiones sobre una visualización ya aceptada y permite que cada audiencia evolucione a distinto ritmo.

Se descarta añadir un interruptor “técnico/negocio” al HTML actual porque acoplaría dos modelos semánticos diferentes y haría más compleja su validación y presentación.

### 2. Fuente estructurada curada y HTML generado

Las macrofunciones y relaciones se mantendrán en una fuente JSON versionada. Cada contrato usará un esquema estable con `id`, `name`, `purpose`, `inputs`, `outputs`, `rules`, `failure_behavior`, `spec_refs`, `implementation_refs`, `test_refs` y `verification_status`. Un generador producirá el HTML autocontenido y determinístico.

Se descarta editar manualmente un HTML grande porque duplicaría contenido, dificultaría revisiones y permitiría que la vista divergiera de OpenSpec.

### 3. Allowlist de requisitos aplicables

La fuente mencionará explícitamente requisitos funcionales aplicables. El verificador resolverá cada referencia contra `openspec/specs/` y los delta specs funcionales activos seleccionados. No se escanearán automáticamente todos los cambios porque auditoría, harness y metodología no son macrofunciones del producto, y dos cambios activos pueden contener requisitos transitorios.

La jerarquía será: spec principal vigente; luego delta spec funcional seleccionado; nunca un archivo archivado salvo que su requisito también exista en la spec principal.

### 4. Nueve macrofunciones iniciales

La primera versión usará:

1. Cargar base de Leads.
2. Validar y normalizar datos.
3. Preparar archivo para Wolkvox.
4. Leer Leads pendientes.
5. Seleccionar y confirmar un lote.
6. Preparar la documentación.
7. Guardar y verificar la documentación.
8. Consultar resultados y productividad.
9. Revisar y aplicar correcciones seguras.

El flujo principal será lineal para facilitar la presentación. Duplicados, fallos recuperables y correcciones se representarán como rutas alternativas, no como detalles técnicos dentro del camino principal.

### 5. Divulgación progresiva del contrato

Cada nodo mostrará nombre y una frase de valor. Al activarlo abrirá un panel con el contrato completo. OpenSpec y evidencia técnica estarán en secciones desplegables separadas y etiquetadas; una prueba o archivo nunca se presentará como requisito normativo.

### 6. Verificación por estructura y por navegador

Las pruebas validarán el esquema JSON, IDs únicos, relaciones resolubles, campos obligatorios, referencias OpenSpec y ausencia de datos sensibles. Un smoke de navegador local comprobará carga, selección, teclado, temas, paneles y enlaces. El artefacto será autocontenido para que pueda presentarse sin depender de red externa.

## Risks / Trade-offs

- **Un resumen puede simplificar demasiado una regla** → conservar el enlace al requisito y mostrar reglas/fallos por separado.
- **Los delta specs activos pueden contradecir una spec principal** → usar allowlist y hacer fallar la validación ante identificadores duplicados o ambiguos.
- **La vista puede quedar desactualizada al cambiar OpenSpec** → resolver todas las referencias durante `verify` y registrar fecha/revisión de generación.
- **Nueve nodos pueden crecer hasta volverse ilegibles** → exigir que nuevas funciones justifiquen nivel macro y usar agrupación o rutas alternativas.
- **Reutilizar visualmente Archify puede inducir a pensar que ambos artefactos comparten datos** → usar título, subtítulo y nombre de archivo inequívocos.

## Migration Plan

1. Registrar el nombre, ubicación y hash del gráfico técnico antes de implementar.
2. Crear y validar la fuente estructurada de contratos.
3. Crear el generador y producir el nuevo HTML sin escribir sobre el artefacto existente.
4. Ejecutar validadores, tests y smoke de navegador local.
5. Presentar ambos gráficos al usuario y ajustar exclusivamente la nueva vista.
6. Publicar la segunda URL solo tras aprobación visual.

Rollback: retirar el nuevo HTML, su fuente y su generador. El diagrama técnico y la aplicación permanecen sin cambios.

## Open Questions

- La etiqueta final del primer nodo será `Cargar base de Leads`; durante la revisión visual el usuario podrá preferir `Cargar BD` como alias más corto.
- La ubicación definitiva dentro del directorio servido en el puerto local se confirmará al auditar el mecanismo que inicia el servidor de presentación.
