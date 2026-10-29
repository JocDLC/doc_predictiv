# Propuesta: agregar-via-tdd

## Why

La metodología SDD de 7 fases con artefactos OpenSpec es proporcional para
features, pero excesiva para cambios chicos (un bugfix puntual, un ajuste de
validación, un refactor cubierto). Hoy esos cambios o se hacen "por fuera"
sin trazabilidad, o arrastran un spec que no aporta. Falta una vía liviana
con enforcement mecánico: test que falla primero, test que pasa después,
suite y lint verdes.

## What Changes

- `AGENTS.md` gana la **Fase 0.5 — Clasificación (TDD vs SDD)**: checklist de
  6 criterios; el agente propone la vía y el usuario confirma. Si alguna
  falla → SDD (Fases 1–7). El flujo TDD es T1–T5 con comandos del harness.
- `automation_salesforce/harness.py` gana los comandos **`tdd-red <test_id>`**
  (exige que el test falle; avisa si falla por error y no por aserción) y
  **`tdd-green <test_id>`** (exige que el test pase, luego corre la suite
  `unit` y `ruff check`).
- Skill `tdd` nuevo (`.devin/skills/tdd/`, con copias en `.windsurf/skills/`
  y `.codex/skills/`, adaptado de obra/superpowers — MIT): Iron Law, ciclo
  RED/GREEN/REFACTOR, tabla de racionalizaciones y checklist final.
- Reglas por IDE (`.windsurf`, `.agents`, `.cursor`, `.codex`, `.claude`) y
  workflows `/tdd` (`.windsurf`, `.agents`) reflejan el paso 0.5.
- **Trazabilidad TDD**: sin artefactos OpenSpec. Alcanza con entrada en
  `CHANGELOG.md` `[Sin publicar]` que nombra el test-regla + `log`/`stop`
  en el Gantt. El test queda como regla permanente.

## Capabilities

### New Capabilities

- `via-tdd`: clasificación TDD vs SDD por checklist, verificación mecánica
  del ciclo rojo→verde en `harness.py` y trazabilidad liviana
  (CHANGELOG + Gantt) para cambios chicos.

### Modified Capabilities

(ninguna)

## Non-goals

- Sin `tdd-guard` ni Probity (requieren Node 22, pytest, modelo pago y no
  cubren Windsurf). Queda anotado en `MEMORY.md` como alternativa futura.
- Sin artefactos OpenSpec para cambios TDD: proposal/design/specs solo
  aplican a la vía SDD.
- No se tocan `dist/`, Salesforce ni runners productivos.

## Impact

- `AGENTS.md`, `.windsurf/rules/harness.md`, `.agents/rules/harness.md`,
  `.cursor/rules/harness.md`, `.codex/AGENTS.md`, `.claude/CLAUDE.md`.
- `automation_salesforce/harness.py` + `tests/test_harness_tdd.py` (nuevo).
- `.devin/skills/tdd/SKILL.md` + copias en `.windsurf/skills/tdd/` y
  `.codex/skills/tdd/`.
- `.windsurf/workflows/tdd.md`, `.agents/workflows/tdd.md` (nuevos).
- `CHANGELOG.md`, `MEMORY.md`.
