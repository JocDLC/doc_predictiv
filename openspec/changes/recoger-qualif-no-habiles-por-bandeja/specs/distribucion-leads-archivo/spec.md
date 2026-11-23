# Delta: fuente de apertura mezclada por Lead ID

## ADDED Requirements

### Requirement: Candidatos de apertura en la vista de distribución

La vista Distribuir leads SHALL ofrecer los leads tomados por la apertura
(REQ-834) como fuente opcional de filas, mezclable con el archivo Excel/CSV
actual. La identidad de cada lead es su `Lead ID`: un mismo ID presente en
archivo y en apertura produce UNA sola fila que conserva el destino del
archivo; IDs distintos nunca se fusionan aunque el nombre coincida. La
importación por archivo y el reparto existente MUST seguir funcionando sin
candidatos de apertura.

#### Scenario: Duplicado archivo + apertura
- **WHEN** un Lead ID aparece en el Excel con persona X y también fue tomado
  en apertura
- **THEN** la vista muestra una sola fila con destino X

#### Scenario: Mismo nombre, IDs distintos
- **WHEN** dos leads comparten nombre pero tienen Lead IDs distintos
- **THEN** la vista los trata como dos leads independientes

#### Scenario: Agregar no ejecuta
- **WHEN** el operador agrega candidatos de apertura a la vista
- **THEN** ningún lead se reasigna ni consume hasta la confirmación normal
  de la corrida (prueba o real)
