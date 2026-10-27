## ADDED Requirements

### Requirement: Nombre visible de la aplicación
La UI SHALL mostrar "Automatización Gestión de Leads" como título de la pestaña del navegador y como título principal del header. Ningún texto visible de la UI SHALL mencionar IA.

#### Scenario: Usuario abre la app
- **WHEN** el usuario abre la aplicación desde INICIAR.bat
- **THEN** la pestaña del navegador muestra "Automatización Gestión de Leads"
- **AND** el header muestra "Automatización Gestión de Leads" como título principal

#### Scenario: Nombre anterior eliminado de la UI
- **WHEN** se busca "Gestión de Campañas Predictivas" en el HTML de la UI
- **THEN** no aparece ninguna ocurrencia

### Requirement: Marca del header
El header SHALL mostrar la marca "RENAULT GROUP" junto con "LBS REC".

#### Scenario: Marca visible
- **WHEN** el usuario ve cualquier vista de la aplicación
- **THEN** el header muestra el logo de Renault, "RENAULT GROUP" y "LBS REC"

### Requirement: Visual moderna clara
La UI SHALL usar un estilo moderno claro: header con degradado azul a violeta, tarjetas de módulo en Home con número de orden e ícono de color propio por módulo, esquinas redondeadas y sombras suaves. El cambio SHALL ser solo de presentación: los IDs, las clases que usa el JS y el comportamiento de cada vista no cambian.

#### Scenario: Home con tarjetas numeradas
- **WHEN** el usuario está en la pantalla de inicio
- **THEN** ve las 4 tarjetas (Preparar, Documentar, Monitor, Distribuir) numeradas del 1 al 4, cada una con su color de acento

#### Scenario: Funcionalidad intacta
- **WHEN** se ejecuta la suite de tests de UI existente
- **THEN** todos los tests pasan sin haberlos modificado

### Requirement: Estilo sin carga de procesamiento
Los estilos SHALL ser livianos para no demorar el monitor: sin fuentes ni recursos externos, sin `backdrop-filter` ni `filter: blur`, sin animaciones infinitas y sin transiciones aplicadas a filas o celdas de tablas. Las transiciones SHALL limitarse a `transform`, `opacity`, `box-shadow` y colores en elementos interactivos, y SHALL desactivarse con `prefers-reduced-motion`.

#### Scenario: Sin recursos de red ni efectos costosos
- **WHEN** se inspecciona el bloque de estilos del HTML
- **THEN** no hay `@import`, `url(http`, `backdrop-filter`, `blur(` ni `animation: ... infinite`

#### Scenario: Movimiento reducido
- **WHEN** el sistema operativo pide movimiento reducido
- **THEN** la UI no aplica transiciones ni animaciones decorativas
