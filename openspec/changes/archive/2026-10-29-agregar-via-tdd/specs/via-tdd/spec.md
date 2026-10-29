# Spec delta: via-tdd

## ADDED Requirements

### Requirement: REQ-001: Clasificación del cambio (TDD vs SDD)

Antes de planificar, el agente MUST clasificar el cambio con la checklist
de la Fase 0.5 de `AGENTS.md`. Va por **TDD** solo si TODAS se cumplen:

1. Es un bugfix, un ajuste de regla o validación puntual, o un refactor
   con el comportamiento cubierto por tests.
2. Toca como máximo 3 archivos productivos, en un solo módulo o capa.
3. No agrega endpoints, vistas de UI, formatos de cola/resultado/snapshot
   ni contratos nuevos.
4. No cambia la mecánica de Salesforce (selectores, flujo de pickup o
   reasignación), seguridad ni privacidad.
5. El comportamiento esperado se puede escribir en una sola frase sin
   ambigüedad.
6. Se puede verificar con un test determinístico (sin navegador ni
   Salesforce en vivo).

Si alguna falla, el cambio MUST ir por **SDD** (Fases 1–7). El agente
MUST proponer la vía y el usuario MUST confirmarla antes de continuar.
Si durante TDD aparece alcance nuevo, el cambio MUST escalarse a SDD con
`/opsx:propose`.

#### Scenario: bugfix puntual clasificado TDD

**Given** un pedido de corrección de una validación puntual que toca un
solo módulo y puede verificarse con un test determinístico.
**When** el agente aplica la checklist de la Fase 0.5.
**Then** propone la vía TDD y, tras la confirmación del usuario, sigue el
flujo T1–T5 sin crear artefactos OpenSpec.

#### Scenario: feature con contrato nuevo clasificada SDD

**Given** un pedido que agrega un endpoint y una vista de UI.
**When** el agente aplica la checklist.
**Then** el criterio 3 falla, la vía es SDD y el cambio sigue las
Fases 1–7 con sus artefactos OpenSpec.

### Requirement: REQ-002: Verificación mecánica de RED (`tdd-red`)

`harness.py` MUST exponer `python harness.py tdd-red <test_id>`, que
corre `python -m unittest <test_id> -v` capturando la salida. Si el test
**pasa** (returncode 0), el comando MUST terminar en error con un mensaje
que indique que el test no prueba comportamiento nuevo. Si el resumen de
unittest muestra `errors=` sin `failures=`, el comando MUST terminar en
OK imprimiendo un aviso de que el test falla por error
(import/nombre/sintaxis) y no por aserción. Si muestra `failures=`, MUST
imprimir que el test falla como se esperaba. Si `test_id` falta, el
parser MUST rechazar la invocación.

#### Scenario: test que pasa es rechazado

**Given** un `test_id` cuyo test pasa.
**When** se corre `python harness.py tdd-red <test_id>`.
**Then** el comando termina con exit code distinto de 0 y un mensaje que
pide ajustar el test antes de implementar.

#### Scenario: test que falla por aserción

**Given** un `test_id` que falla con `FAILED (failures=1)`.
**When** se corre `tdd-red`.
**Then** el comando termina OK indicando que se puede pasar a GREEN.

#### Scenario: test que falla por error

**Given** un `test_id` que falla con `FAILED (errors=1)` sin failures.
**When** se corre `tdd-red`.
**Then** el comando termina OK pero imprime el aviso de "falso rojo"
posible.

#### Scenario: test_id faltante

**Given** la invocación `python harness.py tdd-red` sin argumento.
**When** se parsean los argumentos.
**Then** el parser rechaza la invocación con error de uso.

### Requirement: REQ-003: Verificación mecánica de GREEN (`tdd-green`)

`harness.py` MUST exponer `python harness.py tdd-green <test_id>`, que
MUST ejecutar en orden: `python -m unittest <test_id> -v`, luego la capa
`unit` (suite completa) y luego `ruff check .`. Si el test objetivo
falla, el comando MUST cortar ahí sin correr la suite ni el lint. Solo
con los tres pasos en verde MUST imprimir el OK de `[tdd-green]`.

#### Scenario: test objetivo fallando corta el pipeline

**Given** un `test_id` cuyo test falla.
**When** se corre `tdd-green`.
**Then** el comando termina en error sin ejecutar la suite `unit` ni
`ruff check`.

#### Scenario: todo en verde

**Given** un `test_id` que pasa con suite y lint limpios.
**When** se corre `tdd-green`.
**Then** se ejecutan test objetivo, `unittest discover -s tests` y
`ruff check .` en ese orden, y se imprime el OK.

### Requirement: REQ-004: Trazabilidad de cambios TDD

Todo cambio hecho por la vía TDD MUST registrarse en `CHANGELOG.md` bajo
`[Sin publicar]` (sección `Corregido` o `Cambiado`) nombrando el test que
queda como regla permanente, y MUST dejar un `log` en el tablero Gantt.
El test-regla MUST NOT borrarse ni debilitarse sin autorización explícita
del usuario. Los cambios TDD MUST NOT generar `proposal.md`, `design.md`
ni delta specs en `openspec/changes/`.

#### Scenario: cierre de un cambio TDD

**Given** un cambio que completó `tdd-green`.
**When** se llega a T5.
**Then** existe una entrada en `[Sin publicar]` que nombra el test-regla
y un log del trabajo en el Gantt, sin artefactos OpenSpec nuevos.
