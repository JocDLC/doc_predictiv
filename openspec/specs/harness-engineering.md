# Spec: Multi-IDE Agent Harness Template

## Objetivo

Un arnés de desarrollo replicable entre computadoras e IDEs que combine:

- **Spec-Driven Development (SSD)** con OpenSpec.
- **Harness Engineering** como constraints mecánicas.
- **Context Engineering** con Graphify.
- **Loop Engineering** con ciclos de verificación determinística.

## Requisitos

- El arnés debe ser agnóstico del IDE.
- La fuente de verdad metodológica es `AGENTS.md`.
- Las reglas específicas por IDE son derivadas y deben mantenerse sincronizadas.
- Las versiones de herramientas deben estar fijadas en `VERSIONS.md`.
- La instalación debe ser reproducible: `git clone` + `bootstrap` + `setup-project`.
- Cada cambio debe pasar por `proposal` → `design` → `tasks` → `verify` → `archive`.

## Escenarios

### Escenario 1: nuevo proyecto desde el template

**Given** un desarrollador en una máquina nueva.
**When** ejecuta `git clone` y `bootstrap` + `setup-project`.
**Then** el proyecto tiene `AGENTS.md`, `openspec/`, `graphify-out/` y el harness pasa `verify-setup`.

### Escenario 2: cambio de feature

**Given** un proyecto con el harness.
**When** el agente ejecuta `/opsx:explore` → `/opsx:propose` → `/opsx:apply`.
**Then** se crean `openspec/changes/<cambio>/` y cada tarea se verifica con tests/lint antes de cerrar.

### Escenario 3: multi-IDE

**Given** un proyecto clonado en Cursor, Windsurf y Codex.
**When** se abre el proyecto.
**Then** cada IDE lee su regla (`/.cursor/rules/`, `/.windsurf/`, `/.codex/`) y aplica la misma metodología.

## Decisiones de diseño

- Ver [`MEMORY.md`](../MEMORY.md).

## Estado

- Spec aprobada.
- Ver `openspec/changes/multi-ide-harness/` para el delta actual.
