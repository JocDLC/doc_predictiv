# Delta: recoger QUALIF no laborales por bandeja

## ADDED Requirements

### Requirement: REQ-830: Clasificación del lead para apertura

El sistema SHALL clasificar cada lead listado en una bandeja comparando su
`fecha_creacion` (completa: día + hora) contra las franjas de ESA bandeja,
usando solo la hora — las franjas no tienen día de semana ni fecha. La fecha
del reporte se interpreta en la zona de la bandeja y se convierte a la hora de
la PC con el `tz_offset` configurado de la bandeja antes de comparar.

Clasificaciones: `turno_personal` (una franja propia o de equipo cubre esa
hora en esa bandeja), `no_habil_elegible` (ninguna franja cubre esa hora),
`fuera_de_rango` (fuera del período pedido), `revision` (fecha ilegible o dato
insuficiente para clasificar). La clasificación SHALL ser reproducible en el
servidor con las mismas entradas.

#### Scenario: Lead nocturno es elegible
- **WHEN** un lead CO fue creado un viernes 23:30 y ninguna franja cubre las
  23:30 en CO
- **THEN** se clasifica `no_habil_elegible`

#### Scenario: Lead de turno ajeno queda fuera de la apertura
- **WHEN** un lead CO fue creado un sábado 10:00 y una franja cubre las 10:00
  en CO
- **THEN** se clasifica `turno_personal` y la apertura no lo toma

#### Scenario: Fecha ilegible no se toma
- **WHEN** un lead no tiene `fecha_creacion` parseable
- **THEN** se clasifica `revision` y aparece listado, nunca se toma

### Requirement: REQ-831: Rango manual por bandeja

La acción de apertura SHALL pedir por cada uso: una bandeja habilitada con
reporte y un período `Desde`/`Hasta` con fecha y hora en la zona que la vista
indica. El período es `[desde, hasta)`: el instante `desde` entra y el `hasta`
queda fuera. El servidor SHALL validar `desde < hasta`, `hasta` no futuro y
la bandeja habilitada con URL; un rango inválido rechaza la operación.

#### Scenario: Fin de semana típico
- **WHEN** el operador pide viernes 18:00 a lunes 06:00 para CO
- **THEN** un lead del viernes 18:00 se evalúa y uno del lunes 06:00 queda
  fuera

#### Scenario: Rango inválido rechazado
- **WHEN** `desde` es posterior a `hasta` o `hasta` es futuro
- **THEN** el servidor rechaza la operación sin leer la bandeja

### Requirement: REQ-832: Vista previa de solo lectura

La vista previa de apertura SHALL listar los leads QUALIF de la bandeja con su
clasificación y motivo, sin ejecutar ninguna acción de toma: no Pick Up, no
diálogo de propietario, no WhatsApp, no cambios en colas ni en el estado del
monitor. Una lectura parcial o sesión caída MUST reportarse como fallo y
no puede presentarse como "cero pendientes".

#### Scenario: Preview sin efectos
- **WHEN** el operador abre la vista previa de un rango
- **THEN** ningún lead es abierto para toma y el estado de la cola activa no
  cambia

#### Scenario: Lectura fallida visible
- **WHEN** el reporte no se pudo leer completo
- **THEN** la vista muestra el error de lectura e impide confirmar

### Requirement: REQ-833: Confirmación exclusiva y toma verificada

La confirmación SHALL aceptar solo IDs elegibles de una vista previa válida,
seleccionados por `Lead ID`. Antes de cada toma el sistema MUST re-verificar
que el registro abierto sigue siendo el mismo lead y sigue en la cola QUALIF
de la bandeja; si cambió de dueño, no se toca. La toma queda a nombre del
usuario de la sesión (custodia), sin reasignación ni WhatsApp. Durante la
recogida el monitor, la revisión manual y los runners no pueden intercalarse;
una segunda solicitud concurrente MUST ser rechazada o devolver el resultado
del lote en curso.

#### Scenario: Toma de un seleccionado
- **WHEN** el operador confirma 5 IDs elegibles
- **THEN** el bot pulsa Pick Up solo en esos registros y cada uno queda del
  usuario de la sesión

#### Scenario: Dueño cambiado entre lectura y clic
- **WHEN** un lead seleccionado ya no pertenece a la cola QUALIF al momento de
  la toma
- **THEN** no se toca y se reporta como `tomado_por_otro`/omitido

#### Scenario: Recogida concurrente rechazada
- **WHEN** se confirma una segunda recogida con una en curso
- **THEN** se rechaza o devuelve el estado del lote activo, sin iniciar tomas

### Requirement: REQ-834: Persistencia del lote y disponibilidad

Cada toma de apertura SHALL persistirse de forma atómica por lead con: lote,
`Lead ID`, bandeja, rango, instante y resultado. Los lotes sobreviven al
vaciado del historial del monitor y al reinicio del servidor; ante estado
dudoso (clic sin registro persistido) el lead queda en `revisar`, no se
repite a ciegas. Solo los leads con resultado `tomado_confirmado` de apertura
quedan disponibles como candidatos en la vista Distribuir.

#### Scenario: Éxito parcial conservado
- **WHEN** de 10 seleccionados 7 se toman y 3 fallan
- **THEN** los 7 quedan registrados y disponibles; los 3 muestran su motivo

#### Scenario: Reinicio entre clic y registro
- **WHEN** el proceso se interrumpe tras una toma no persistida
- **THEN** el lead queda en `revisar` hasta comprobar su propietario en
  Salesforce, nunca se reintenta a ciegas
