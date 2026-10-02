## ADDED Requirements

### Requirement: Artefacto de negocio generado con Archify
El sistema SHALL proporcionar un gráfico de negocio generado mediante el flujo nativo **Archify Workflow v2**, en un artefacto HTML y una URL distintos del diagrama técnico existente. La creación, publicación y actualización del nuevo gráfico MUST NOT sobrescribir ni modificar `documentador-architecture.html`.

#### Scenario: Apertura de ambas vistas
- **WHEN** una persona abre el gráfico técnico y el gráfico de contratos de negocio
- **THEN** ambas vistas están disponibles de forma independiente y conservan sus propios nodos, textos, interacciones y URL

#### Scenario: Verificación del origen Archify
- **WHEN** se inspeccionan los artefactos del gráfico de negocio
- **THEN** existen un candidato válido de tipo `workflow`, los recibos de finalización Archify y el HTML generado por esa herramienta

### Requirement: Dos caminos de información claramente separados
El gráfico SHALL representar dos recorridos de negocio independientes pero relacionados y MUST indicar el origen, las transformaciones y el destino de la información en cada uno.

El primer camino SHALL mostrar: CSV exportado desde Salesforce, preparación y control de los Leads, generación del CSV correcto para Wolkvox y carga externa en Wolkvox.

El segundo camino SHALL mostrar: CSV descargado desde Wolkvox con los intentos de llamada, organización de los resultados, preparación de la documentación y registro en Salesforce por una ruta manual o una ruta automática mediante el bot.

#### Scenario: Explicación del camino Salesforce a Wolkvox
- **WHEN** una persona observa el primer camino sin abrir detalles
- **THEN** puede explicar que la aplicación transforma un CSV de Salesforce en un CSV preparado para cargar en Wolkvox y evita ajustes manuales repetitivos

#### Scenario: Explicación del camino Wolkvox a Salesforce
- **WHEN** una persona observa el segundo camino sin abrir detalles
- **THEN** puede explicar que la aplicación organiza los intentos descargados de Wolkvox y prepara su registro en Salesforce, manualmente o mediante el bot

#### Scenario: Selección de la forma de documentación
- **WHEN** la información de Wolkvox ya está organizada
- **THEN** el gráfico presenta claramente una bifurcación entre documentación manual y documentación automática mediante el bot, y ambas terminan en Salesforce

### Requirement: La visualización refleja la capacidad operativa vigente
Toda afirmación de disponibilidad MUST estar respaldada por implementación y prueba vigentes. Los cambios OpenSpec activos o planificados MAY aportar contexto, pero MUST NOT presentarse como capacidades ya disponibles si todavía no están implementados.

La entrada de archivos SHALL describirse como CSV mientras la aplicación use lectura de texto y no exista soporte XLSX implementado y verificado.

#### Scenario: Formato actualmente aceptado
- **WHEN** una persona consulta el contrato de entrada desde Salesforce o Wolkvox
- **THEN** el gráfico identifica el archivo como CSV y no anuncia XLSX como formato disponible

#### Scenario: Capacidad planificada pero no implementada
- **WHEN** un delta spec menciona una capacidad futura sin evidencia de implementación y prueba
- **THEN** el verificador impide etiquetarla como disponible y la vista ejecutiva no la incluye como comportamiento vigente

### Requirement: Contrato funcional por macrofunción
Cada macrofunción MUST exponer un contrato breve con nombre, propósito, entrada, resultado, regla principal y comportamiento ante fallos. El contrato SHALL usar frases breves en español y MUST NOT exigir conocimientos de programación para comprenderlo.

Los contratos SHALL mostrarse mediante recursos nativos del artefacto Archify, manteniendo la vista inicial simple y dejando la evidencia normativa o técnica para una consulta secundaria.

#### Scenario: Contrato para preparar la campaña
- **WHEN** la persona consulta `Preparar archivo para Wolkvox`
- **THEN** ve que recibe Leads provenientes del CSV de Salesforce, entrega un CSV listo para Wolkvox, aplica las reglas de organización acordadas y separa los registros que no pueden procesarse

#### Scenario: Contrato para organizar intentos
- **WHEN** la persona consulta `Organizar intentos de llamada`
- **THEN** ve que recibe el CSV descargado desde Wolkvox, ordena los intentos por Lead y entrega información preparada para documentar

#### Scenario: Contrato para documentar con el bot
- **WHEN** la persona consulta `Documentar automáticamente en Salesforce`
- **THEN** ve qué información recibe, qué resultado debe dejar en Salesforce, qué comprobación confirma el guardado y qué ocurre si la automatización no puede continuar

### Requirement: Flujo principal simple y excepciones secundarias
La vista inicial SHALL priorizar los dos caminos principales y SHALL representar correcciones, duplicados y fallos recuperables como rutas secundarias. Los archivos, funciones, puertos, protocolos y nombres internos MUST NOT ser etiquetas principales.

#### Scenario: Presentación a una persona no técnica
- **WHEN** una persona observa la vista inicial
- **THEN** reconoce los dos recorridos, sus archivos de entrada y salida y la bifurcación manual/bot sin necesitar explicación técnica

#### Scenario: Corrección segura
- **WHEN** se consulta la ruta secundaria de correcciones
- **THEN** el gráfico indica que se relee el valor, se comprueba que la base sigue vigente y solo entonces se aplica la corrección

### Requirement: Trazabilidad verificable con OpenSpec
Cada contrato MUST referenciar uno o más requisitos o escenarios OpenSpec existentes mediante identificadores y rutas resolubles. La vista SHALL permitir consultar esta trazabilidad separadamente del resumen de negocio. La generación MUST fallar si una referencia requerida no existe o si una macrofunción carece de fuente OpenSpec.

#### Scenario: Consulta de la fuente contractual
- **WHEN** una persona abre la evidencia de una macrofunción
- **THEN** ve los requisitos y escenarios que sustentan el contrato, con referencias locales válidas y separados de la explicación ejecutiva

#### Scenario: Referencia obsoleta
- **WHEN** una fuente apunta a un requisito eliminado, renombrado o ambiguo
- **THEN** el verificador identifica la macrofunción y la referencia inválida y no publica el artefacto como vigente

### Requirement: Evidencia técnica progresiva
El gráfico SHALL mantener ocultos inicialmente los archivos, funciones y tests, pero SHALL permitir consultarlos como evidencia opcional. La ausencia de evidencia técnica o de una prueba aprobatoria MUST indicarse como pendiente y MUST NOT presentarse como verificación superada.

#### Scenario: Usuario ejecutivo
- **WHEN** la persona no abre la evidencia
- **THEN** solo ve el recorrido, el contrato y las relaciones de negocio

#### Scenario: Auditor abre evidencia
- **WHEN** una persona consulta la evidencia técnica
- **THEN** puede localizar implementación, pruebas y estado de verificación sin confundirlos con el texto normativo OpenSpec

### Requirement: Accesibilidad y uso en presentación
El artefacto MUST ser navegable con teclado, SHALL mantener contraste legible en temas claro y oscuro y MUST adaptar el contenido a pantallas habituales sin ocultar información esencial. Cada nodo y relación MUST tener un nombre accesible equivalente al contenido visible.

#### Scenario: Navegación sin ratón
- **WHEN** una persona recorre el gráfico con teclado y activa una macrofunción
- **THEN** el foco es visible, el contrato puede consultarse y la persona puede continuar sin perder la posición de navegación

### Requirement: Privacidad y contenido seguro
El gráfico, su candidato, sus pruebas y sus exportaciones MUST contener solo ejemplos sintéticos y MUST NOT incluir IDs, nombres, teléfonos, correos, comentarios, credenciales, cookies o códigos 2FA reales.

#### Scenario: Verificación previa a publicación
- **WHEN** se genera o actualiza el gráfico
- **THEN** un control automático inspecciona los artefactos y bloquea la publicación si detecta un canario sensible o un patrón de dato real prohibido
