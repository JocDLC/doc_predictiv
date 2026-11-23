# distribucion-leads-archivo Specification (delta)

## ADDED Requirements

### Requirement: REQ-1015: Métricas de ciclo de la cola de distribución

Al terminar (o abortar) la corrida, `run_distribucion_queue` SHALL escribir
`cola_distribucion_activa.metricas.json` con `cycle_elapsed_seconds` (total
de la corrida), los conteos por estado y los segundos por lead ya
registrados. El archivo MUST ser compatible con el formato de métricas de
los otros procesos (`productivity_metrics`/`laboratory_metrics`).

#### Scenario: Corrida completa escribe las métricas
- **WHEN** la cola de distribución se procesa completa en 480 segundos
- **THEN** `cola_distribucion_activa.metricas.json` contiene
  `cycle_elapsed_seconds: 480` y los conteos de cada estado

#### Scenario: Corrida interrumpida también persiste lo acumulado
- **WHEN** la corrida muere o se detiene a la mitad
- **THEN** el archivo de métricas refleja lo procesado con el tiempo
  acumulado hasta el corte
