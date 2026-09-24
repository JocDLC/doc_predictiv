## MODIFIED Requirements

### Requirement: REQ-402: Datos por secciones y disponibilidad de columna

La UI MUST mostrar una tabla de una fila por Lead. Cada columna y valor MUST
provenir de una columna visible identificada por etiqueta o alias configurado. La
UI MUST ocultar los campos que no estén presentes en la bandeja y MUST NOT realizar
una consulta adicional para completar valores. La UI MUST permitir seleccionar
Leads para un lote de documentación confirmado y mostrar su estado local sin
cerrarse.

#### Scenario: columna ausente en el reporte

**Given** un reporte visible sin la columna "Número de matrícula".
**When** se genera la UI local.
**Then** cada tarjeta muestra "No disponible en bandeja" para ese campo y no se
abre ni edita otro registro para completarlo.

#### Scenario: selección de Leads para documentación

**Given** una lista local de Leads filtrados.
**When** el operador selecciona uno o más Leads y solicita documentación.
**Then** la UI mantiene la lista abierta y envía exclusivamente esos Leads al lote
  confirmado.

### Requirement: REQ-405: Apertura de Lead sin mutación

Cada tarjeta con un Lead ID Salesforce válido MUST conservar una acción manual
para abrir la vista del registro sin cambios. Tras una confirmación explícita de
un lote, el sistema MAY abrir una pestaña de trabajo y modificar exclusivamente
`Otra información` según la capability de documentación automática.

#### Scenario: abrir manualmente desde la UI local

**Given** una tarjeta con un Lead ID válido, incluso si su estado local es `error`.
**When** el operador elige la acción manual.
**Then** el navegador abre la vista del registro sin ejecutar acciones de negocio.
