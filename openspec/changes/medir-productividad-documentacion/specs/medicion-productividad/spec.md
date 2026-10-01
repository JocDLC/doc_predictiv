# Medición de productividad

## ADDED Requirements

### Requirement: Duración segura por Lead automático

El sistema SHALL registrar la duración de cada Lead procesado por el modo
automático, sin incluir contenido del campo ni datos de clientes.

#### Scenario: Guardado verificado medido

- **WHEN** el bot inicia y completa el procesamiento automático de un Lead con
  estado `guardado`
- **THEN** el resultado incluye `elapsed_seconds` positivo redondeado a una
  décima
- **AND** el resultado no contiene el comentario, teléfono, nombre ni snapshot.

#### Scenario: Error medido

- **WHEN** ocurre un error después de que el bot inició el procesamiento de un
  Lead
- **THEN** el resultado `error` incluye su duración transcurrida
- **AND** el runner continúa con la siguiente entrada de la cola cuando aplique.

### Requirement: Métricas agregadas locales

El sistema SHALL producir un resumen local del lote basado en resultados
medidos, separado de los datos de cliente.

#### Scenario: Lote con resultados guardados

- **WHEN** termina un lote con al menos un Lead `guardado`
- **THEN** el resumen informa tamaño de muestra, estados, promedio, mediana,
  mínimo y máximo de duraciones de Leads guardados
- **AND** informa la capacidad efectiva por hora basada en el ciclo completo del
  lote.

#### Scenario: Lote sin guardados

- **WHEN** termina un lote sin Leads `guardado`
- **THEN** el resumen conserva conteos y tasa de éxito
- **AND** no inventa promedio, mediana ni capacidad por hora.

### Requirement: Medición por etapas del flujo automático

El sistema SHALL registrar, por Lead procesado en modo automático, la duración
de cada etapa ejecutada usando solo números: navegación y espera de Lightning,
comprobación del campo `Comentario` para duplicados, lectura de `Otra
información`, preparación del editor, guardado con su espera de persistencia,
verificación del valor persistido y escritura del snapshot. El sistema SHALL
contar las recargas de respaldo usadas durante la verificación.

#### Scenario: Lead guardado con etapas medidas

- **WHEN** el bot completa un Lead `guardado` en modo automático
- **THEN** el resultado incluye `stage_seconds` con las etapas ejecutadas,
  redondeadas a una décima
- **AND** `verify_reloads` indica cuántas recargas usó la verificación
- **AND** el resultado no contiene contenido de campos ni datos de clientes.

#### Scenario: Lead duplicado con etapas parciales

- **WHEN** un Lead se clasifica `duplicado`
- **THEN** su `stage_seconds` solo contiene navegación y comprobación de
  duplicado
- **AND** no se registran etapas de escritura.

#### Scenario: Resumen con medias por etapa

- **WHEN** termina un lote con resultados instrumentados
- **THEN** el resumen informa la media por etapa sobre los resultados que
  ejecutaron cada etapa y el total de recargas de verificación
- **AND** el aviso de cierre de la UI muestra ese desglose por etapa.

### Requirement: Inspección visual del tiempo individual

La UI SHALL mostrar `elapsed_seconds` para cada Lead `guardado` tanto en la
lista general como en la cola del bot. La referencia SHALL ser el promedio de
los Leads guardados del lote terminado: verde si el tiempo es menor o igual al
promedio, naranja si lo supera hasta 20%, y rojo si supera ese límite. La
clasificación SHALL incluir texto y color. Los estados `error` y `duplicado`
MUST NOT recibir clasificación de rendimiento.

#### Scenario: Lead dentro del promedio

- **WHEN** un Lead guardado tarda igual o menos que el promedio del lote
- **THEN** ambas vistas muestran sus segundos y el texto `normal` en verde.

#### Scenario: Lead lento

- **WHEN** un Lead guardado supera el promedio en más de 20%
- **THEN** ambas vistas muestran sus segundos y el texto `alto` en rojo.

#### Scenario: Lead no guardado

- **WHEN** un Lead queda `error` o `duplicado`
- **THEN** la UI conserva ese estado sin asignarle color de productividad.

### Requirement: Presentación honesta de productividad

La presentación SHALL diferenciar las estimaciones operativas manuales de las
métricas instrumentadas del bot.

#### Scenario: Mostrar resultados

- **WHEN** se abre la presentación con métricas de prueba disponibles
- **THEN** identifica el tamaño y la fecha de la muestra del bot
- **AND** etiqueta 40–55 s y 23–29 s como rangos declarados
- **AND** no expone datos de clientes.