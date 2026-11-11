## ADDED Requirements

### Requirement: Barrido horizontal de filas virtualizadas

El lector del Monitor MUST recorrer horizontalmente la grilla Lightning desde
el inicio hasta el extremo o hasta un máximo configurado de pasadas. MUST
capturar los fragmentos renderizados de cada fila en cada pasada y MUST NOT
requerir que propietario, estado, detalles y Lead ID coexistan en el mismo
viewport. El barrido del Monitor MUST NOT desplazar verticalmente el reporte.

#### Scenario: propietario e ID en viewports distintos
- **WHEN** una fila muestra el propietario QUALIF en la vista izquierda y su enlace o Lead ID únicamente después de desplazar la grilla a la derecha
- **THEN** el lector recorre ambas vistas y produce un único Lead cuando puede demostrar que ambos fragmentos pertenecen a la misma fila

#### Scenario: reporte angosto
- **WHEN** propietario, estado e identidad del Lead aparecen en el viewport inicial
- **THEN** el lector conserva el resultado vigente y finaliza sin pasadas horizontales innecesarias después de alcanzar el extremo

#### Scenario: límite de pasadas
- **WHEN** la grilla sigue informando movimiento horizontal más allá del máximo configurado
- **THEN** el lector detiene el barrido, marca como irresolubles los fragmentos incompletos y no prolonga indefinidamente el ciclo

### Requirement: Correlación segura de fragmentos

El lector MUST unir fragmentos solamente mediante una identidad estructural
estable de fila. MUST validar que las claves no sean ambiguas y que el conjunto
u orden usado para correlacionar permanezca estable durante el barrido. MUST
NOT correlacionar filas mediante nombre, correo, teléfono, campaña ni otro dato
personal. Si no puede demostrar la correlación, MUST omitir la fila y MUST NOT
abrir el registro ni ejecutar Pick Up.

#### Scenario: identidad estable compartida
- **WHEN** dos fragmentos horizontales exponen la misma clave estructural única y uno contiene el propietario QUALIF mientras el otro contiene el Lead ID
- **THEN** el lector los fusiona como una sola fila y conserva los detalles visibles de ambos

#### Scenario: fila sin identidad estable
- **WHEN** un fragmento contiene el propietario QUALIF pero no existe una clave estructural segura para vincularlo con el fragmento que contiene el ID
- **THEN** la fila se registra como irresoluble y no se convierte en candidato de toma

#### Scenario: orden cambia durante el barrido
- **WHEN** las claves o el orden verificable de las filas cambia entre dos pasadas horizontales
- **THEN** el lector invalida la correlación afectada y no mezcla información de filas distintas

#### Scenario: claves duplicadas
- **WHEN** dos filas visibles presentan la misma clave estructural no única
- **THEN** ambas quedan ambiguas y ninguna habilita una toma a partir de la fusión

### Requirement: Extracción robusta y validada de Lead ID

El lector MUST buscar el Lead ID en enlaces de registro descendientes, atributos
estructurales de la fila y sus descendientes, y la columna visible `Lead ID`.
MUST aceptar solamente identificadores Salesforce válidos de 15 o 18
caracteres y rutas correspondientes al objeto configurado. MUST conservar la
prioridad del enlace de registro cuando varias fuentes válidas coincidan.

#### Scenario: ID en enlace descendiente
- **WHEN** una celda renderizada contiene un enlace `/Lead/<id>/view`
- **THEN** el lector extrae y valida ese identificador

#### Scenario: ID en atributo de una celda interna
- **WHEN** la fila raíz no tiene ID pero un descendiente expone `data-recordid`, `data-record-id`, `data-row-key-value` o un atributo equivalente con un Lead ID válido
- **THEN** el lector recupera el ID desde ese descendiente

#### Scenario: ID en columna del reporte
- **WHEN** la fila no contiene enlace ni atributo válido pero la columna `Lead ID` está renderizada con un identificador válido
- **THEN** el lector usa el valor de la columna

#### Scenario: identificador de otro objeto o inválido
- **WHEN** una ruta pertenece a otro objeto o un atributo no contiene un ID Salesforce válido
- **THEN** esa fuente se ignora y no habilita una toma

### Requirement: Diagnóstico estructural sin datos personales

Cada lectura MUST informar mediante `bandeja_scan` y el log la cantidad de
pasadas horizontales, el ancho del viewport, las filas con propietario QUALIF
pero sin Lead ID y las filas inestables o ambiguas. Los diagnósticos MUST NOT
incluir nombres, correos, teléfonos, campañas, valores de celdas ni Lead IDs sin
enmascarar. El mensaje MUST distinguir una bandeja vacía de una fila omitida
por identidad irresoluble.

#### Scenario: QUALIF visible sin ID
- **WHEN** el lector encuentra el propietario configurado pero no logra resolver el Lead ID de forma segura
- **THEN** el evento y el log reportan un conteo `owner_without_id` mayor que cero sin incluir valores de la fila

#### Scenario: bandeja realmente vacía
- **WHEN** el reporte no contiene filas ni fragmentos QUALIF irresolubles
- **THEN** el diagnóstico informa cero filas candidatas sin atribuir el resultado a un ID faltante

#### Scenario: revisión de privacidad
- **WHEN** se inspeccionan logs, eventos de diagnóstico y errores del barrido
- **THEN** solo aparecen conteos, dimensiones, códigos de bandeja y, cuando sea imprescindible, Lead IDs enmascarados

### Requirement: Compatibilidad multibandeja y rendimiento acotado

La lectura virtualizada MUST preservar el orden de procesamiento y las reglas
vigentes de propietario y estado para AR, CO y MX. Un fallo o ambigüedad en una
bandeja MUST NOT impedir que el ciclo procese las otras. El ajuste de ancho de
la ventana MAY reducir la cantidad de pasadas, pero el funcionamiento correcto
MUST NOT depender de un tamaño de pantalla específico.

#### Scenario: CO y MX caben en una vista
- **WHEN** las bandejas CO o MX exponen identidad, propietario y estado en el viewport inicial
- **THEN** sus Leads se detectan igual que antes del cambio y no se altera Pick Up ni la reasignación

#### Scenario: AR ancha falla sin afectar CO
- **WHEN** AR contiene una fila irresoluble y CO contiene una fila válida en el mismo ciclo
- **THEN** AR queda diagnosticada de forma segura y CO continúa hasta su resultado normal

#### Scenario: viewport reducido
- **WHEN** el Monitor corre en un notebook con viewport efectivo menor que el ancho total del reporte
- **THEN** aplica el barrido horizontal y no depende de maximizar la ventana para detectar una fila correlacionable

#### Scenario: ajuste de ventana no disponible
- **WHEN** WebDriver o el sistema operativo rechaza ampliar la ventana dedicada
- **THEN** el Monitor conserva la ventana existente y el lector sigue funcionando mediante el barrido seguro

