# Spec: toma-selectiva-leads

## ADDED Requirements

### Requirement: REQ-901: Lectura bajo demanda de la bandeja (scan)

El servidor MUST exponer `POST /api/monitor/scan` que lanza una lectura
solo-listar de todas las bandejas habilitadas, registrando cada lead con
propietario igual al configurado (`*_LEAD_QUALIF`) y estado esperado como
`detectado`. MUST NOT abrir registros ni ejecutar Pick Up durante un scan.
El scan MUST correr bajo el mismo candado que los ciclos del monitor y la
misma exclusión mutua con los bots de documentación/cierre, y MUST usar la
ventana dedicada del monitor.

#### Scenario: scan lista los leads acumulados

**Given** la bandeja AR con leads QUALIF/`Nuevo` llegados fuera de horario.
**When** se invoca `POST /api/monitor/scan`.
**Then** la tabla muestra todos esos leads como `detectado` sin que se abra
ningún registro ni se toque Salesforce más allá de la lectura.

#### Scenario: scan durante un ciclo o un run

**Given** un ciclo del monitor o un run de documentación en curso.
**When** se invoca `POST /api/monitor/scan`.
**Then** responde `409` sin lanzar una segunda operación sobre el navegador.

### Requirement: REQ-902: Toma selectiva de leads

El servidor MUST exponer `POST /api/monitor/take` con body
`{"lead_ids": [...]}` que tome SOLO los leads indicados: por cada uno abre
el registro, re-verifica que el propietario siga siendo la cola
configurada, pulsa `Pick Up` y verifica el cambio de propietario. MUST
validar que `lead_ids` sea una lista no vacía de IDs Salesforce válidos
(`400` en caso contrario) y MUST respetar el candado de ciclo y la
exclusión mutua (`409` si el navegador está ocupado).

#### Scenario: toma de un lead seleccionado

**Given** un lead `detectado` cuyo propietario sigue siendo `AR_LEAD_QUALIF`.
**When** se invoca `POST /api/monitor/take` con su `lead_id`.
**Then** el bot abre el registro, ejecuta Pick Up, verifica el propietario
nuevo y el estado queda `tomado`.

#### Scenario: el lead ya fue tomado por otro

**Given** un lead seleccionado que otro auxiliar tomó entre la lista y el
clic.
**When** corre la toma.
**Then** la re-verificación detecta el propietario distinto, el estado
queda `tomado_por_otro` y MUST NOT pulsarse Pick Up.

#### Scenario: body inválido

**Given** un body sin `lead_ids` o con IDs que no cumplen el patrón.
**When** se invoca `POST /api/monitor/take`.
**Then** responde `400` sin tocar el navegador.

### Requirement: REQ-903: Selección en la tabla del monitor

La tabla del Monitor de Bandeja MUST ofrecer, en cada lead con estado
reprocesable (`detectado`, `error`), un botón "Tomar" y un checkbox de
selección con su botón "Tomar seleccionados", ambos invocando
`POST /api/monitor/take`. La columna `Preferred mean of contact` MUST
resaltarse cuando indique un canal, para guiar el contacto posterior.
MUST NOT ofrecerse toma sobre leads en estado terminal (`tomado`,
`tomado_por_otro`).

#### Scenario: tomar desde la tabla

**Given** la tabla con tres leads `detectado`.
**When** la persona marca dos y pulsa "Tomar seleccionados".
**Then** la UI invoca `take` con exactamente esos dos `lead_ids` y las
filas quedan a la espera del `cycle_end` que refresca sus estados.

#### Scenario: preferencia de contacto visible

**Given** un lead con `Preferred mean of contact` = "WhatsApp".
**When** la tabla lo muestra.
**Then** esa celda aparece resaltada indicando el canal.
### Requirement: REQ-904: Limpieza segura de la lista del monitor

La vista del Monitor de Bandeja MUST ofrecer un botón "Limpiar lista" que,
tras confirmación explícita, elimine únicamente los elementos de `results`
persistidos localmente. La operación MUST conservar habilitación, modo prueba,
bandejas, horarios y demás configuración; MUST NOT navegar ni modificar
Salesforce. El servidor MUST rechazarla con `409` si un ciclo del monitor está
en curso y la UI MUST advertir que, si el monitor sigue activo, los QUALIF
presentes pueden volver a aparecer en una revisión posterior.

#### Scenario: limpiar resultados existentes

**Given** el monitor con resultados anteriores y sin ciclo en curso.
**When** la persona confirma "Limpiar lista".
**Then** `results` queda vacío, la tabla muestra que no hay leads detectados y
la configuración del monitor permanece idéntica.

#### Scenario: limpieza durante una revisión

**Given** un ciclo del monitor en curso.
**When** la persona intenta limpiar la lista.
**Then** el servidor responde `409`, no cambia el estado persistido y la UI
muestra un mensaje claro para reintentar al finalizar.

#### Scenario: QUALIF todavía presente

**Given** que la lista fue limpiada y el monitor continúa activo.
**When** una revisión posterior encuentra un QUALIF todavía presente.
**Then** el lead puede aparecer de nuevo como un resultado nuevo, sin recuperar
el historial borrado.
