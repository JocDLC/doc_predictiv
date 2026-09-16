# Capability: Lectura segura de Salesforce con Selenium

## ADDED Requirements

### Requirement: REQ-201: Navegador visible con perfil dedicado

El runner MUST detectar Microsoft Edge y abrirlo en modo visible con un perfil
dedicado y configurable. El piloto MAY ofrecer Chrome posteriormente, pero Edge
MUST ser el navegador predeterminado inicial.

#### Scenario: primera ejecución con 2FA

**Given** un perfil dedicado sin sesión de Salesforce.
**When** el usuario ejecuta el runner.
**Then** Edge se abre visiblemente, el usuario puede completar login y 2FA de forma manual, y el runner no solicita, guarda ni registra credenciales o códigos.

### Requirement: REQ-202: Lectura de bandeja de Leads sin gestión

El runner MUST abrir el reporte configurado, leer sus filas visibles y marcar como
sin gestión los Leads cuyo valor exacto de "Propietario del candidato" sea
`AR_LEAD_QUALIF`. La extracción del ID MUST usar el objeto Salesforce configurado
y el formato estándar de 15 o 18 caracteres, sin depender de un prefijo fijo.

#### Scenario: Lead nuevo sin propietario asignado

**Given** una fila visible del reporte cuyo propietario es `AR_LEAD_QUALIF`.
**When** el runner procesa la grilla.
**Then** incluye el Lead ID, la fecha de creación, la posición visible en la
grilla y el estado `SIN_GESTION` en un reporte JSON local, sin modificar
Salesforce.

### Requirement: REQ-203: Lectura de Otra información y cálculo del próximo INT

El runner MUST abrir un Lead solicitado por el usuario, leer el campo "Otra
información" sin activar edición y calcular el siguiente número de intento como
el máximo patrón `N INT` encontrado más uno.

#### Scenario: historial con tres intentos

**Given** que "Otra información" contiene `1 INT`, `2 INT` y `3 INT`.
**When** el runner analiza el campo.
**Then** informa `4` como próximo número de intento.

#### Scenario: historial sin intentos

**Given** que "Otra información" no contiene el patrón `N INT`.
**When** el runner analiza el campo.
**Then** informa `1` como próximo número de intento.

### Requirement: REQ-204: Piloto estrictamente de solo lectura

El piloto MUST ejecutarse sin escribir, guardar, cerrar, reasignar ni cambiar
ningún dato dentro de Salesforce.

#### Scenario: lectura exitosa

**Given** un usuario autenticado y un Lead válido.
**When** el runner encuentra "Otra información".
**Then** solo lee y muestra la información; no utiliza acciones de edición, escritura o guardado.

### Requirement: REQ-205: Auditoría local y manejo seguro de errores

El runner MUST guardar logs locales con resultado y timestamp y tomar una captura
local ante errores. MAY mostrar los Lead IDs completos exclusivamente en la
consola local; si un Lead ID se incluye en un log, MUST quedar enmascarado. No
MUST guardar contenido completo de comentarios, teléfonos, emails, cookies,
credenciales o códigos 2FA.

#### Scenario: campo no localizado

**Given** un Lead donde la etiqueta "Otra información" no puede localizarse.
**When** vence el tiempo de espera.
**Then** el runner registra el fallo, toma una captura local y termina sin modificar Salesforce.
