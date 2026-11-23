# laboratorio-timeout-watchdog Specification

## Purpose
El laboratorio no puede quedar colgado: cada lead tiene presupuesto de
tiempo, el worker expone progreso, y el flag de corrida se libera aunque
el worker muera.

## ADDED Requirements

### Requirement: REQ-1020: Timeout por lead

Cada lead del laboratorio SHALL tener un presupuesto de tiempo máximo por
etapa (navegar, leer, documentar/enviar). Al excederlo, el lead SHALL
quedar en `error` con el motivo `timeout:<etapa>` y la corrida SHALL
continuar con el siguiente lead.

#### Scenario: Lead que excede el presupuesto queda en error
- **WHEN** un lead con motor `agent_browser` supera el timeout de la etapa
  `leer` (sin respuesta del daemon)
- **THEN** su resultado queda `error` con motivo `timeout:leer`, se
  persiste, y la corrida procesa el lead siguiente

#### Scenario: Timeout no duplica acciones
- **WHEN** la documentación de un lead corta por timeout con estado
  desconocido
- **THEN** el lead queda `error` y NO se reenvía WhatsApp ni se reintenta
  la escritura a ciegas (fail-safe, no duplicar)

### Requirement: REQ-1021: Progreso observable del worker

El worker SHALL actualizar un indicador de progreso (resultado parcial por
lead o archivo de heartbeat) al terminar cada lead, de modo que la UI o un
operador pueda distinguir "procesando" de "colgado".

#### Scenario: Se detecta una corrida sin progreso
- **WHEN** el flag `laboratorio_running` está en true pero no hay
  actualización de resultados/heartbeat por más de N segundos (p.ej. 120)
- **THEN** el estado expuesto indica que el worker está sin progreso
  (staleness), no solo "corriendo"

### Requirement: REQ-1022: Liberación del flag de corrida

Si el worker termina (normal, error o kill) sin completar la escritura
final, el flag de corrida SHALL liberarse para permitir una nueva corrida.

#### Scenario: Worker muerto libera el flag
- **WHEN** el proceso worker desaparece sin escribir el resultado final
- **THEN** una nueva corrida puede iniciar sin el error "ya está
  corriendo" (el flag se detecta obsoleto o se limpia)

### Requirement: REQ-1023: Diagnóstico del hang de agent-browser

La causa raíz del cuelgue del motor `agent_browser` SHALL quedar
identificada y documentada (punto exacto: handshake CDP, navegación,
espera de selector o lectura), con el remedio aplicado o la decisión de
retirar el motor.

#### Scenario: Hang reproducido y clasificado
- **WHEN** se reproduce el hang con la corrida real o una sonda mínima
- **THEN** el diagnóstico indica la etapa y llamada exactas donde el
  daemon deja de responder
