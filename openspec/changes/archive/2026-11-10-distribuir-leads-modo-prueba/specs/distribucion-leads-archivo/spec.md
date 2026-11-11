# Delta spec — distribución de leads desde archivo (modo prueba)

## ADDED Requirements

### Requirement: Modo prueba de la cola de distribución

La cola de distribución MUST aceptar un campo opcional `modo` con valores
`real` (por defecto) o `prueba`. Una cola con `modo` desconocido MUST ser
rechazada en validación.

#### Scenario: Cola sin modo

- **GIVEN** una cola válida sin campo `modo`
- **WHEN** se valida con `validate_distribucion_queue`
- **THEN** se acepta y `load_distribucion_queue` devuelve `modo == "real"`

#### Scenario: Cola en modo prueba

- **GIVEN** una cola válida con `modo == "prueba"`
- **WHEN** corre `run_distribucion_queue.py`
- **THEN** procesa cada lead en simulación y produce estados `prueba_*`

#### Scenario: Modo desconocido

- **GIVEN** una cola con `modo` distinto de `real`/`prueba`
- **WHEN** se valida
- **THEN** la cola se rechaza

### Requirement: Simulación sin escritura en Salesforce

En modo prueba el runner MUST abrir cada lead, leer el propietario y
clasificar la acción que haría la corrida real. Para leads que se
reasignarían MUST abrir el diálogo "Cambiar propietario", tipear el nombre
destino, verificar que el lookup encuentra al usuario y cancelar el diálogo.
El runner MUST NOT pulsar Pick Up, MUST NOT confirmar el modal y MUST NOT
escribir campos ni comentarios en Salesforce.

#### Scenario: Destino ya es propietario

- **GIVEN** el propietario del lead ya es la persona destino
- **THEN** el resultado es `prueba_ok:ya_asignado` sin abrir el modal

#### Scenario: Cola excluida

- **GIVEN** el propietario es `AR_LEAD_COLD`, `AR_LEAD_EXPORT_GETLEAD` o
  `AR_LEAD_LEADIT_EXPORT`
- **THEN** el resultado es `prueba_ok:cola_excluida` sin tocar nada

#### Scenario: Lead en cola de ingreso

- **GIVEN** el propietario es `AR_LEAD_QUALIF` (cola de ingreso)
- **THEN** el resultado es `prueba_ok:pickup_y_reasignar` si el nombre destino
  existe en el lookup del modal, que se cancela siempre

#### Scenario: Propietario de otra persona

- **GIVEN** el propietario es otra persona distinta del destino
- **THEN** el resultado es `prueba_ok:reasignar` si el nombre destino existe
  en el lookup del modal, que se cancela siempre

#### Scenario: Nombre destino inexistente

- **GIVEN** el nombre destino no aparece en el lookup del modal
- **THEN** el resultado es `prueba_nombre_no_encontrado` y el modal se cancela

#### Scenario: Lead ilegible o error

- **GIVEN** el propietario no se puede leer
- **THEN** el resultado es `prueba_inaccesible`; ante fallo del modal,
  `prueba_error:<paso>`

### Requirement: Visibilidad del modo prueba en la UI

El paso de vista previa MUST mostrar una casilla "Modo prueba" con un banner
destacado (mismo lenguaje visual que el modo prueba del Monitor de Bandeja).
Con la casilla activa el botón de ejecución MUST decir "Probar (sin guardar)"
y la tabla de resultados MUST mostrar los estados `prueba_*` con un banner
indicando que nada se guardó en Salesforce.

#### Scenario: Banner en vista previa

- **GIVEN** la casilla "Modo prueba" marcada
- **THEN** el banner "no se guarda nada en Salesforce" es visible y el botón
  dice "Probar (sin guardar)"

#### Scenario: Resultados de simulación

- **GIVEN** una corrida en modo prueba terminada
- **THEN** cada fila muestra su estado `prueba_*` traducido y un banner
  "Simulación — nada se guardó en Salesforce" permanece visible
