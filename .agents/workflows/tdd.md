---
description: Workflow /tdd para Antigravity — vía TDD (rojo → verde → refactor) para cambios chicos
---

# /tdd

1. **Clasificar (T1)**: checklist de la Fase 0.5 de `AGENTS.md` + confirmación del usuario. `gantt start <id>` (o `add`).
2. **RED (T2)**: test mínimo → `python harness.py tdd-red <test_id>` desde `automation_salesforce/` (debe fallar; ojo con el AVISO de falso rojo por error).
3. **GREEN (T3)**: código mínimo → `python harness.py tdd-green <test_id>` (test + suite `unit` + `ruff check .`).
4. **REFACTOR (T4)**: limpieza opcional, siempre volviendo a `tdd-green`.
5. **Cierre (T5)**: `CHANGELOG.md` `[Sin publicar]` nombrando el test-regla, `gantt log` + `stop`, `graphify update .`, confirmar commit.
6. Alcance nuevo → escalar a SDD con `/opsx:propose`. Test-regla intocable sin autorización.
