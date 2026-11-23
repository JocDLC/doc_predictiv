# Delta: cobertura del monitor vs apertura no laboral

## MODIFIED Requirements

### Requirement: REQ-817: Cobertura de la toma evaluada a la hora de ingreso del lead

El monitor SHALL decidir si toma cada lead evaluando la franja vigente a la
**hora de ingreso del lead a la cola** (`fecha_creacion` del reporte, con la
hora convertida a la zona de la PC mediante el `tz_offset` de la bandeja), no
solo a la hora del ciclo. Un lead con fecha de creación parseable se toma
cuando su hora de ingreso cae dentro de una franja que cubre su bandeja
(propia o del equipo), aunque el ciclo corra después del cierre y aunque el
lead sea de un día anterior — la franja se evalúa por hora, sin día de
semana. Un lead cuya hora de ingreso cae fuera de toda franja de la bandeja
NO se toma: es un lead no laboral que corresponde a la recogida de apertura
(REQ-830+), no al turno vigente. Un lead sin `fecha_creacion` parseable NO
se toma: queda listado para revisión — la hora del ciclo ya no sirve de
fallback porque no prueba qué franja cubre al lead.

#### Scenario: Lead ingresado en franja se toma aunque el ciclo llegue tarde
- **WHEN** un lead CO ingresó a las 10:58 con franja 09:40–11:00 y el ciclo
  lo procesa a las 11:01
- **THEN** el lead se toma igual y la asignación usa la encargada vigente a
  las 10:58 (ej. José)

#### Scenario: Lead ingresado antes de la franja no se toma
- **WHEN** un lead AR ingresó a las 10:30 sin franja que cubra las 10:30 y
  el ciclo corre a las 12:01 con la franja 12:00–13:59 activa
- **THEN** el lead no se toma en ese ciclo (su cobertura era de otra franja
  o de nadie)

#### Scenario: Lead nocturno no se toma aunque el ciclo corra en franja
- **WHEN** un lead AR ingresó a las 23:30 sin franja que cubra las 23:30 y
  el ciclo corre a las 12:01 del día siguiente con franja activa
- **THEN** el lead no se toma (corresponde a la apertura no laboral)

#### Scenario: Lead de ayer en-franja se toma con su franja
- **WHEN** un lead AR ingresó ayer a las 15:00 con franja 12:00–17:59 y el
  ciclo corre hoy con esa franja activa
- **THEN** el lead se toma y se asigna según la franja que cubre las 15:00

#### Scenario: Lead sin fecha de creación usable va a revisión
- **WHEN** un lead no tiene `fecha_creacion` parseable y el ciclo corre en
  franja vigente
- **THEN** el lead no se toma: se lista para revisión (ya no se usa la hora
  del ciclo como fallback)
