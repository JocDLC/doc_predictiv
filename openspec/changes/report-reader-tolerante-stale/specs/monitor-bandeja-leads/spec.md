# monitor-bandeja-leads Specification (delta)

## ADDED Requirements

### Requirement: REQ-1033: Scan de bandeja resistente a re-render de Lightning

Una falla de lectura del reporte por re-render (elemento/frame muerto)
SHALL reintentarse de forma acotada y, al agotarse, registrar
`bandeja_error` con contexto — sin abortar el ciclo ni silenciar el fallo.

#### Scenario: Error de lectura no tumba el ciclo
- **WHEN** el scan de una bandeja agota sus reintentos por
  `StaleElementReferenceException`
- **THEN** el estado del monitor registra `bandeja_error` con bandeja,
  excepción e intentos, y el ciclo sigue con la siguiente bandeja o termina
  limpio

#### Scenario: Recuperación transitoria en el mismo ciclo
- **WHEN** el primer intento de scan falla por una fila stale y el
  reintento lee bien
- **THEN** el monitor procesa los leads de la bandeja sin registrar
  `bandeja_error`
