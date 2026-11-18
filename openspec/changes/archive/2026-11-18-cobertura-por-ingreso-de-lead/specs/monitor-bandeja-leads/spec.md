# Delta: cobertura de la toma por hora de ingreso del lead

## ADDED Requirements

### Requirement: REQ-817: Cobertura de la toma evaluada a la hora de ingreso del lead

El monitor SHALL decidir si toma cada lead evaluando la franja vigente a la
**hora de ingreso del lead a la cola** (`fecha_creacion` del reporte), no
solo a la hora del ciclo. Un lead con fecha de creación usable se toma
cuando su hora de ingreso cae dentro de una franja que cubre su bandeja
(propia o del equipo), aunque el ciclo corra después del cierre — y NO se
toma cuando su ingreso cae fuera de toda franja, aunque el ciclo corra
durante una franja activa. Los leads sin fecha de creación usable conservan
la evaluación actual (hora del ciclo).

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

#### Scenario: Lead sin fecha de creación usable cae al comportamiento actual
- **WHEN** un lead no tiene `fecha_creacion` parseable y el ciclo corre en
  franja vigente
- **THEN** la cobertura se evalúa a la hora del ciclo, igual que antes

### Requirement: REQ-818: Ventana de gracia post-cierre para rezagados

El monitor SHALL seguir corriendo ciclos durante una ventana de gracia tras
el cierre de una franja que estuvo activa — suficiente para re-verificar la
bandeja una vez (~`MONITOR_INTERVAL_SECONDS`). Durante la gracia se toman
solo leads ingresados en-franja o dentro de la gracia por tolerancia de
reloj; leads ingresados después del cierre no se toman.

#### Scenario: Rezagado del último minuto se recupera en gracia
- **WHEN** un lead ingresó 09:59 en una franja que cerró 10:00, no apareció
  en la lectura previa al cierre, y un ciclo corre a las 10:02 dentro de la
  gracia
- **THEN** el lead se re-verifica y se toma

#### Scenario: Lead ingresado post-cierre no se toma en gracia
- **WHEN** un lead ingresó 10:03 (franja cerrada 10:00) y el ciclo de
  gracia corre a las 10:02
- **THEN** el lead no se toma

#### Scenario: La gracia no reabre el día
- **WHEN** pasó la ventana de gracia sin ninguna franja activa
- **THEN** el monitor pausa los ciclos igual que hoy

### Requirement: REQ-819: Notificaciones Windows con bandeja identificada

Las notificaciones Windows del monitor SHALL identificar la bandeja en cada
línea de resultado —tomado, error, no verificado, otro propietario y
detectado— con el código de cola y su bandera de país (AR 🇦🇷, CO 🇨🇴,
MX 🇲🇽), manteniendo el emoji de estado existente.

#### Scenario: Toma en Colombia nombra la bandeja
- **WHEN** el monitor toma un lead de la bandeja CO
- **THEN** el toast muestra la línea con ✅, la bandera 🇨🇴 y el código
  de la bandeja

#### Scenario: Error en México nombra la bandeja
- **WHEN** la toma de un lead MX falla
- **THEN** el toast muestra la línea con ❌, la bandera 🇲🇽 y el código
  de la bandeja

### Requirement: REQ-820: Propietario de cola correcto en reportes sin columna mapeada

El lector de reportes SHALL detectar la cola de ingreso (`unassigned_owner`)
de cada bandeja al alinear columnas, usando el owner configurado para ESA
bandeja — no siempre `AR_LEAD_QUALIF`. Cuando el reporte no trae la columna
mapeada, el detalle del lead muestra la cola de su propia bandeja.

#### Scenario: Detalle de lead CO muestra CO_LEAD_QUALIF
- **WHEN** el reporte de la bandeja CO no trae la columna de propietario
  mapeada
- **THEN** el detalle del lead usa `CO_LEAD_QUALIF`, no `AR_LEAD_QUALIF`
