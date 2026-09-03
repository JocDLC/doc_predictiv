# Metodología para Codex (CLI/IDE)

Este proyecto usa `AGENTS.md` como fuente de verdad. Lee siempre:

1. `AGENTS.md` antes de cualquier cambio.
2. `graphify-out/GRAPH_REPORT.md` para contexto.
3. `MEMORY.md` para decisiones y non-goals.

Flujo de trabajo:

- Fase 0: `graphify update .` si el grafo está desactualizado.
- Fase 1: `openspec` explore o discute con el usuario.
- Fase 2: `openspec propose <cambio>` para plan.
- Fase 3: verifica `verify-setup` y checklist del harness.
- Fase 4: implementa una tarea a la vez.
- Fase 5: ejecuta tests y linter.
- Fase 6: corrige la causa raíz.
- Fase 7: `openspec archive` y `graphify update .`.

Restricciones:
- No modifiques `AGENTS.md` sin reflejar el cambio en otras reglas por IDE.
- No uses `grep` masivo; usa `graphify query`.
- Verifica determinísticamente antes de reportar "listo".
