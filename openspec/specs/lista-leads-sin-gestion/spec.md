# Capability: UI local de Leads sin gestión

## Purpose

Mostrar localmente los Leads visibles sin gestión, filtrados por propietario,
sin modificar Salesforce ni exponer datos personales en el repositorio.

## Requirements

### Requirement: REQ-401: Lectura visible y filtro exacto

El runner MUST abrir el reporte Salesforce configurado, leer solamente sus filas
visibles y seleccionar exclusivamente las filas cuyo valor de "Propietario del
candidato" sea exactamente `AR_LEAD_QUALIF` después de quitar espacios externos.
El runner MUST NOT modificar Salesforce.

#### Scenario: filas visibles con propietarios diferentes

**Given** una grilla visible que contiene varios propietarios.
**When** el runner genera la lista local.
**Then** incluye solo las filas con propietario exacto `AR_LEAD_QUALIF` y conserva
el orden visible del reporte.

### Requirement: REQ-402: Datos por secciones y disponibilidad de columna

La UI MUST mostrar una tabla de una fila por Lead. Cada columna y valor MUST
provenir de una columna visible identificada por etiqueta o alias configurado. La
UI MUST ocultar los campos que no estén presentes en la bandeja y MUST NOT
realizar una consulta adicional, abrir el detalle individual ni modificar
Salesforce.

#### Scenario: columna ausente en el reporte

**Given** un reporte visible sin la columna "Número de matrícula".
**When** se genera la UI local.
**Then** cada tarjeta muestra "No disponible en bandeja" para ese campo y no se
abre ni edita otro registro para completarlo.

### Requirement: REQ-403: Opciones dinámicas desde filas visibles

La UI MUST construir sus filtros de Estado de candidato, Vehículo de interés y
País a partir de los valores de las filas visibles filtradas. No MUST usar una
lista fija de opciones ni exponer valores de otras fuentes.

#### Scenario: estado visible no previsto

**Given** una fila filtrada cuyo Estado de candidato tiene un valor no esperado.
**When** la UI se genera.
**Then** el valor aparece en la tarjeta y queda disponible como filtro local.

### Requirement: REQ-404: Privacidad de datos personales

La UI e instantánea local MAY contener datos de clientes exclusivamente en el
equipo autorizado. Esos archivos MUST estar ignorados por Git. El runner MUST NOT
escribir nombres, correos, teléfonos, DNI/código fiscal, matrícula o contenido de
campos personales en consola, logs o capturas.

#### Scenario: ejecución exitosa

**Given** una lectura exitosa con información de clientes.
**When** el runner termina.
**Then** la consola y el log contienen solo conteos y Lead IDs enmascarados, y
`git status` no incluye los archivos locales de datos.

### Requirement: REQ-405: Apertura de Lead sin mutación

Cada tarjeta con un Lead ID Salesforce válido MAY mostrar una acción "Abrir Lead".
La acción MUST limitarse a navegar a la vista del registro y MUST NOT editar,
guardar, reasignar, cerrar ni cambiar datos de Salesforce.

#### Scenario: abrir desde la UI local

**Given** una tarjeta con un Lead ID válido.
**When** el usuario elige "Abrir Lead".
**Then** el navegador abre la vista del registro sin ejecutar acciones de negocio.
