# Spec: documentacion-por-intento

## ADDED Requirements

### Requirement: REQ-701: Estado documentado por llamada

El estado documentado de un Lead MUST derivarse de la cobertura de sus
`call_id` actuales, no de un booleano por Lead. Un Lead MUST ser elegible
para la cola si al menos uno de sus intentos actuales no está confirmado.

#### Scenario: historial no cubre intentos nuevos

**Given** un Lead con resultado `guardado` y snapshot de una ejecución
anterior cuyos `call_id` son A y B.
**When** se carga un CSV nuevo que trae los intentos C y D del mismo Lead.
**Then** el Lead aparece pendiente, es elegible para la cola y solo C y D
se exportan.

#### Scenario: historial cubre intentos actuales

**Given** el mismo Lead y CSV con solo los intentos A y B.
**When** se aplica el snapshot/resultado previo.
**Then** el Lead figura como documentado solo si A y B aparecen en la
evidencia.

### Requirement: REQ-702: Resultados y snapshots legados no confirman

Un `*.resultado.json` o `*.snapshots.json` sin `run_id`/`call_ids` MUST
tratarse como histórico: se muestra en la cola con etiqueta "histórico" y
MUST NOT marcar `done`, `botDone` ni `documentedCallIds` para intentos que
no puede identificar.

#### Scenario: resultado legado aplicado

**Given** un resultado `{lead_id, status:"guardado"}` sin `call_ids`.
**When** la UI lo procesa con `applyBotResult` o el polling.
**Then** el Lead no se marca documentado y conserva sus intentos pendientes.

### Requirement: REQ-703: Runner idempotente por `call_id`

El runner MUST leer `Otra información` antes de componer y MUST comparar los
`call_id` solicitados contra los presentes. MUST solo agregar los ausentes,
numerando desde el último `N INT` real. Si todos están presentes MUST
registrar `ya_documentado` sin abrir el editor ni pulsar Guardar.

#### Scenario: todos presentes

**Given** `Otra información` ya contiene los `call_id` A y B del intento.
**When** el runner procesa el Lead.
**Then** el estado es `ya_documentado`, no se abre el editor y el snapshot se
renueva con la lectura vigente.

#### Scenario: un subconjunto presente

**Given** el campo tiene A pero falta B.
**When** el runner procesa el Lead.
**Then** compone y guarda solo B con el siguiente INT, el estado es `guardado`
y `added_call_ids` = [B].

#### Scenario: intento sin identidad verificable

**Given** un intento sin `call_id` y un campo no vacío.
**When** el runner evalúa el Lead.
**Then** registra `revision` y MUST NOT escribir en Salesforce.

### Requirement: REQ-704: Tanda inmutable identificada por `run_id`

`POST /run` MUST crear una copia inmutable de la cola (`run_<run_id>.json`)
bajo exclusión mutua y el runner MUST procesar esa copia. Resultados,
snapshots y métricas MUST llevar el `run_id` de su ejecución.

#### Scenario: PUT durante ejecución

**Given** un `run_id` en curso.
**When** la UI envía `PUT /api/queue` con una selección distinta.
**Then** la ejecución activa termina sobre su copia sin mezcla silenciosa; la
nueva selección queda como borrador para la próxima tanda.

### Requirement: REQ-705: Polling no reescribe la cola en curso

El polling de la UI MUST aplicar resultados/snapshots al estado local, pero
MUST NOT reescribir `cola_activa.json` mientras el bot está corriendo.

#### Scenario: progreso durante la tanda

**Given** el bot corriendo.
**When** el polling recibe un `guardado` parcial.
**Then** el estado se refleja en la UI sin reescribir la cola; la cola se
actualiza recién cuando la tanda finaliza.

### Requirement: REQ-706: Marca manual asociada a los intentos visibles

Cuando el operador marca "Documentado" a mano, la UI MUST registrar los
`call_id` de los intentos visibles en ese momento y la procedencia `manual`.
Esa marca MUST NOT heredarse a intentos futuros del mismo Lead.

#### Scenario: nuevo intento tras marca manual

**Given** un Lead marcado manual con intentos A y B.
**When** llega un CSV nuevo con A, B y C.
**Then** C queda pendiente y el Lead vuelve a ser elegible.

### Requirement: REQ-707: Métricas distinguen escrituras nuevas de verificaciones

El resumen de métricas MUST separar `guardado`, `ya_documentado`, `parcial`,
`revision`, `duplicado` y `error`; los tiempos verdes MUST pertenecer solo a
la ejecución que los produjo.

#### Scenario: tanda con solo verificaciones

**Given** 10 Leads ya documentados.
**When** el bot corre en `--auto`.
**Then** las métricas reportan 10 `ya_documentado`, 0 guardados y
`saved_elapsed_seconds` nulo.
