# informes-tiempo-total Specification

## Purpose
Tiempo total del ciclo visible en todos los informes de fin de proceso:
UI (alert/tabla), JSON de métricas y resumen de consola, para Documentar,
Cierre, Distribución y Laboratorio.

## ADDED Requirements

### Requirement: REQ-1010: Tiempo total en el informe de Documentar

El alert final de "Documentar" SHALL mostrar el tiempo total del ciclo
(`cycle_elapsed_seconds` del archivo de métricas) además de los conteos y
el detalle por lead.

#### Scenario: Alert de Documentar muestra el total del ciclo
- **WHEN** la corrida de documentación termina con métricas que incluyen
  `cycle_elapsed_seconds: 754`
- **THEN** el alert incluye el tiempo total formateado (ej. `12m 34s` o
  `754 s`) junto a los conteos ya exhibidos

#### Scenario: Métricas sin campo no rompen el informe
- **WHEN** el archivo de métricas no existe o falta `cycle_elapsed_seconds`
- **THEN** el alert se renderiza igual que hoy, sin la línea de tiempo
  total y sin error de JS

### Requirement: REQ-1011: Tiempo total en el informe de Cierre

El alert final de "Cerrar leads" SHALL mostrar el tiempo total del ciclo
leído de las métricas de cierre (`cola_cierre_activa.metricas.json` o el
endpoint equivalente).

#### Scenario: Alert de cierre muestra el total
- **WHEN** la corrida de cierre termina con `cycle_elapsed_seconds` en sus
  métricas
- **THEN** el alert de cierre incluye el tiempo total junto a los conteos
  de cerrados/errores

### Requirement: REQ-1012: Tiempo total en el informe de Distribución

La UI SHALL mostrar el tiempo total del ciclo de distribución al terminar
la corrida, leído del artefacto de métricas de distribución.

#### Scenario: Informe de distribución muestra el total
- **WHEN** `run_distribucion_queue` escribe `cycle_elapsed_seconds` y la
  corrida termina
- **THEN** la vista de "Distribuir leads" expone el tiempo total del ciclo

### Requirement: REQ-1013: Tiempo total en el informe de Laboratorio

El informe final del laboratorio SHALL mostrar `cycle_elapsed_seconds`
de `laboratory_metrics` además del detalle por lead.

#### Scenario: Tarjeta de laboratorio muestra el total
- **WHEN** la corrida del laboratorio termina con métricas que incluyen
  `cycle_elapsed_seconds`
- **THEN** el informe muestra el tiempo total junto al resumen de estados

### Requirement: REQ-1014: Tiempo total en el resumen de consola

Los runners de Documentar, Cierre, Distribución y Laboratorio SHALL
imprimir el tiempo total del ciclo en su "Resumen" final de consola.

#### Scenario: Runner de distribución imprime el total
- **WHEN** `run_distribucion_queue.py` completa la cola
- **THEN** la salida final incluye una línea con el tiempo total del ciclo

#### Scenario: Runner de laboratorio imprime el total
- **WHEN** `run_laboratory_queue.py` completa la cola
- **THEN** la salida final incluye el tiempo total del ciclo
