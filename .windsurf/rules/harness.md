---
description: Reglas del harness para cualquier proyecto con este template
---

# Reglas del harness

Aplica la metodología de `AGENTS.md` en cada tarea:

1. Fase 0: verifica `graphify-out/` y `AGENTS.md`.
2. Fase 0.5: clasifica el cambio con la checklist de `AGENTS.md` (TDD vs SDD) y confirma la vía con el usuario.
   - TDD: `python harness.py tdd-red <test_id>` → `tdd-green <test_id>` desde `automation_salesforce/`; cierre en `CHANGELOG.md` `[Sin publicar]` + log en Gantt. Ver skill `tdd`.
   - SDD: fases 1–7 siguientes.
3. Fase 1: usa `/opsx:explore` y confirma con el usuario antes de continuar.
4. Fase 2: crea `openspec/changes/<cambio>/proposal.md`, `design.md`, `tasks.md`.
5. Fase 3: verifica el harness (dependencias, tests, lint, scripts, CI).
6. Fase 4: implementa una tarea a la vez con tests.
7. Fase 5: ejecuta tests y linter.
8. Fase 6: corrige la causa raíz.
9. Fase 7: usa `/opsx:archive` y `graphify update .`.

Restricciones:
- No modifiques `AGENTS.md` sin reflejar el cambio en otras reglas por IDE.
- No uses `grep` masivo; usa `graphify query`.
- No instales `@latest` sin anotarlo en `VERSIONS.md`.
- Verifica determinísticamente antes de reportar "listo".
