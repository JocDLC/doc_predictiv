---
description: Guiar un cambio completo con OpenSpec + Graphify (análisis → spec → harness → desarrollo → tests → cierre)
---

Sigue la metodología definida en `AGENTS.md`, fase por fase, pidiendo confirmación al usuario entre fases. Cada tarea es un Loop: **Goal → Tools → Context → Verification → Termination**.

1. **Goal**: lee `AGENTS.md` + `MEMORY.md` + `graphify-out/GRAPH_REPORT.md`.
2. **Context**: verifica que el grafo exista y esté actualizado: `graphify update .`.
3. **Explore**: analiza la propuesta con `/opsx:explore` y consulta el grafo para entender el impacto.
4. **Plan**: crea el plan con `/opsx:propose <nombre-del-cambio>` y valida con `openspec validate --changes`.
5. **Harness**: revisa el checklist de Fase 3 de `AGENTS.md`. Si falta algo, configúralo primero.
6. **Apply**: implementa con `/opsx:apply`, una tarea de `tasks.md` a la vez, con tests por cada feature.
7. **Verify**: ejecuta tests + lint + typecheck + `verify-setup`.
8. **Fix**: si falla, identifica la causa raíz, corrige mínimamente y agrega un test de regresión.
9. **Archive**: cierra con `/opsx:archive` y actualiza el grafo con `graphify update .`.
