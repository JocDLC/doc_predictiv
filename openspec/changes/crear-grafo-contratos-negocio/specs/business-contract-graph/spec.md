## ADDED Requirements

### Requirement: Gráfico de macrofunciones independiente
El sistema SHALL proporcionar un gráfico de macrofunciones de negocio en un artefacto HTML y una URL distintos del diagrama técnico existente. La creación, publicación y actualización del nuevo gráfico MUST NOT sobrescribir ni modificar `documentador-architecture.html`.

#### Scenario: Apertura de ambas vistas
- **WHEN** una persona abre el gráfico técnico y el gráfico de contratos de negocio
- **THEN** ambas vistas están disponibles de forma independiente y conservan sus propios nodos, textos, interacciones y URL

### Requirement: Recorrido comprensible de negocio
El gráfico SHALL representar un recorrido de extremo a extremo mediante macrofunciones expresadas en lenguaje de negocio. SHALL incluir como mínimo carga de base, validación y normalización, preparación para Wolkvox, lectura de Leads, selección del lote, documentación, verificación del guardado, resultados/productividad y correcciones.

#### Scenario: Presentación a una persona no técnica
- **WHEN** una persona observa la vista inicial sin abrir detalles
- **THEN** puede reconocer el orden general del proceso sin encontrar nombres de archivos, funciones Python, puertos o protocolos como etiquetas principales

#### Scenario: Flujo alternativo de corrección
- **WHEN** la persona sigue la relación desde resultados hacia correcciones
- **THEN** el gráfico muestra que una corrección relee el valor, detecta conflictos y solo actualiza un dato cuya base continúa vigente

### Requirement: Contrato funcional por macrofunción
Cada macrofunción MUST exponer un contrato con nombre, propósito, entradas, resultado esperado, reglas de negocio y comportamiento ante fallos. El contrato SHALL usar frases breves en español y MUST NOT exigir conocimientos de programación para comprenderlo.

#### Scenario: Consulta del contrato de carga
- **WHEN** la persona selecciona `Cargar base de Leads`
- **THEN** ve que recibe CSV o XLSX, incorpora los registros utilizables, conserva las columnas requeridas y deriva los registros excluidos sin mostrar detalles de implementación por defecto

#### Scenario: Consulta del contrato de guardado
- **WHEN** la persona selecciona `Guardar y verificar documentación`
- **THEN** ve que el resultado solo se considera guardado después de releer y confirmar el valor persistido, junto con el comportamiento cuando la confirmación falla

### Requirement: Trazabilidad verificable con OpenSpec
Cada contrato MUST referenciar uno o más requisitos o escenarios OpenSpec existentes mediante identificadores y rutas resolubles. La vista SHALL permitir desplegar esta trazabilidad separadamente del resumen de negocio. La generación MUST fallar si una referencia requerida no existe o si una macrofunción carece de fuente OpenSpec.

#### Scenario: Desplegar la fuente contractual
- **WHEN** la persona abre la trazabilidad de una macrofunción
- **THEN** ve los identificadores y títulos de los requisitos y escenarios que sustentan su contrato, con enlaces locales válidos

#### Scenario: Referencia obsoleta
- **WHEN** una fuente estructurada apunta a un requisito eliminado o renombrado
- **THEN** el verificador devuelve un error que identifica la macrofunción y la referencia inválida, y no publica el artefacto como vigente

### Requirement: Trazabilidad técnica progresiva
El gráfico SHALL mantener ocultos inicialmente los archivos, funciones y tests, pero SHALL permitir consultarlos como evidencia opcional. La ausencia de evidencia técnica para una macrofunción MUST quedar indicada y no presentarse como verificación aprobada.

#### Scenario: Usuario ejecutivo
- **WHEN** la persona no abre la sección de evidencia
- **THEN** solo ve el contrato y las relaciones de negocio

#### Scenario: Auditor abre evidencia
- **WHEN** una persona despliega la evidencia técnica
- **THEN** puede localizar implementación, tests y estado de verificación sin confundirlos con el texto normativo OpenSpec

### Requirement: Accesibilidad y uso en presentación
El artefacto MUST ser navegable con teclado, SHALL mantener contraste legible en temas claro y oscuro y MUST adaptar el contrato a pantallas habituales sin ocultar contenido esencial. Cada nodo y relación MUST tener un nombre accesible equivalente al contenido visible.

#### Scenario: Navegación sin ratón
- **WHEN** una persona recorre el gráfico con teclado y activa una macrofunción
- **THEN** el foco es visible, el contrato se abre y puede cerrarse sin perder la posición de navegación

### Requirement: Privacidad y contenido seguro
El gráfico, su fuente estructurada, sus pruebas y sus exportaciones MUST contener solo ejemplos sintéticos y MUST NOT incluir IDs, nombres, teléfonos, correos, comentarios, credenciales, cookies o códigos 2FA reales.

#### Scenario: Verificación previa a publicación
- **WHEN** se genera o actualiza el gráfico
- **THEN** un control automático inspecciona los artefactos y bloquea la publicación si detecta un canario sensible o un patrón de dato real prohibido

