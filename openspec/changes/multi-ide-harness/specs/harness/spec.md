# Capability: Multi-IDE Agent Harness

## ADDED Requirements

### Requirement: REQ-001: Fuentes de verdad centralizadas

El arnés MUST tener archivos centrales que todo agente lea antes de actuar.

#### Scenario: un agente abre el proyecto por primera vez

**Given** un repositorio con el template aplicado.
**When** el agente inicia una tarea.
**Then** lee `AGENTS.md`, `MEMORY.md` y `graphify-out/GRAPH_REPORT.md` antes de proponer cambios.

### Requirement: REQ-002: Spec-Driven Development con OpenSpec

Cada cambio MUST pasar por `proposal` → `design` → `tasks` → `validate` → `archive`.

#### Scenario: nueva funcionalidad

**Given** un usuario que pide una nueva feature.
**When** el agente ejecuta `/opsx:explore` y `/opsx:propose <cambio>`.
**Then** se generan `openspec/changes/<cambio>/proposal.md`, `design.md`, `tasks.md` y delta specs.

### Requirement: REQ-003: Loop Engineering

Cada tarea MUST ejecutarse como un loop con goal, tools, context, verification y termination.

#### Scenario: desarrollo de una tarea

**Given** un cambio con `tasks.md`.
**When** el agente trabaja una tarea.
**Then** verifica `tasks.md`, tests, lint y `openspec validate --changes` antes de cerrar.

### Requirement: REQ-004: Context Engineering con Graphify

El agente MUST usar el grafo de conocimiento para evitar escanear archivos innecesarios.

#### Scenario: preguntar sobre relaciones del codebase

**Given** un codebase con `graphify-out/` actualizado.
**When** el agente necesita saber cómo X se relaciona con Y.
**Then** usa `graphify query` en lugar de `grep` masivo.

### Requirement: REQ-005: Configuración multi-IDE

El arnés MUST proveer reglas derivadas de `AGENTS.md` para cada IDE soportado.

#### Scenario: abrir el proyecto en Cursor

**Given** un proyecto con `.cursor/rules/harness.md`.
**When** se abre en Cursor.
**Then** Cursor aplica las mismas restricciones que `AGENTS.md`.

### Requirement: REQ-006: Versiones fijadas

Las herramientas del harness MUST tener versiones exactas en `VERSIONS.md`.

#### Scenario: instalar en una máquina nueva

**Given** una máquina nueva.
**When** se ejecuta `scripts/bootstrap.ps1`.
**Then** instala `@fission-ai/openspec@1.6.0` y `graphifyy==0.10.0`.

### Requirement: REQ-007: Verificación determinística

Antes de reportar una tarea como lista, se MUST ejecutar `verify-setup` y tests/lint.

#### Scenario: cierre de una tarea

**Given** una tarea implementada.
**When** el agente llega a Fase 5.
**Then** ejecuta tests, lint y `./scripts/verify-setup.ps1`.

## MODIFIED Requirements

### Requirement: REQ-008: Comando de graphify

El comando correcto para actualizar el grafo MUST ser `graphify update .`.

#### Scenario: mantener grafo actualizado

**Given** un grafo desactualizado.
**When** el agente necesita contexto fresco.
**Then** ejecuta `graphify update .` y no `graphify . --update`.

## REMOVED Requirements

Ninguno.
