# Tasks: agregar-via-tdd

## Implementación

- [x] `openspec/changes/agregar-via-tdd/`: proposal + tasks + delta spec.
- [x] `automation_salesforce/tests/test_harness_tdd.py` (TDD, primero los
      tests): `tdd-red` con test pasando → SystemExit; con `failures=1` →
      OK; con `errors=1` → OK + aviso impreso; `tdd-green` con test
      fallando → corta antes de suite/lint; `tdd-green` OK → orden
      target → `unit` → ruff; `parse_args` acepta `tdd-red x` y `test`;
      `parse_args` error en `tdd-red` sin id.
- [x] `automation_salesforce/harness.py`: `tdd-red`/`tdd-green` en
      `choices`, posicional `test_id` (`nargs="?"`), `parser.error` si
      falta, `run_named_command(command, test_id=None)`, funciones
      `run_tdd_red` / `run_tdd_green`.
- [x] `.devin/skills/tdd/SKILL.md` + copias idénticas en
      `.windsurf/skills/tdd/` y `.codex/skills/tdd/`.
- [x] `AGENTS.md`: Fase 0.5 con checklist de 6 criterios + flujo T1–T5;
      nota en Fase 1 (aplica a SDD); Termination con variante TDD.
- [x] Reglas por IDE: `.windsurf/rules/harness.md`,
      `.agents/rules/harness.md`, `.cursor/rules/harness.md`,
      `.codex/AGENTS.md`, `.claude/CLAUDE.md`. Workflows
      `.windsurf/workflows/tdd.md` y `.agents/workflows/tdd.md`.
- [x] `CHANGELOG.md`: `[Sin publicar]` con la vía TDD + nota del formato
      para entradas TDD (test-regla nombrado).
- [x] `MEMORY.md`: decisión "SDD + TDD por clasificación (Fase 0.5)",
      `.devin/skills/tdd` como fuente de las copias, tdd-guard/Probity
      descartado por ahora.

## Tests y verificación

- [x] `python harness.py test` (suite completa OK).
- [x] `python -m ruff check .` OK.
- [x] Manual: `python harness.py tdd-red tests.test_harness_tdd` falla
      (los tests pasan) y `python harness.py tdd-red` sin id da error.
- [x] `openspec validate --changes` OK.
- [x] `graphify update .`.
