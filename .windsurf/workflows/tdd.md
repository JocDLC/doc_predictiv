---
description: Ejecutar un cambio chico por la vía TDD (rojo → verde → refactor) tras clasificarlo en la Fase 0.5
---

1. **Clasificar (T1)**: aplica la checklist de la Fase 0.5 de `AGENTS.md` y confirma la vía TDD con el usuario. Después `gantt start <id>` (o `add` si no existe).
2. **RED (T2)**: escribe el test mínimo y corre `python harness.py tdd-red <test_id>` desde `automation_salesforce/`. Solo avanza si el test falla (verificá el AVISO si falla por error y no por aserción).
3. **GREEN (T3)**: escribe el código mínimo y corre `python harness.py tdd-green <test_id>` (exige test + suite `unit` + `ruff check .` en verde).
4. **REFACTOR (T4)**: limpieza opcional, volviendo a correr `tdd-green`.
5. **Cierre (T5)**: entrada en `CHANGELOG.md` `[Sin publicar]` nombrando el test-regla, `gantt log` + `stop`, `graphify update .` y confirmación para commitear.
6. Si aparece alcance nuevo, escala a SDD con `/opsx:propose`. El test-regla no se borra ni se debilita sin autorización del usuario.
