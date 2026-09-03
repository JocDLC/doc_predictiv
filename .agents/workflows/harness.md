---
description: Workflow /nuevo-cambio para Antigravity
---

# /nuevo-cambio

1. **Contexto**: `graphify update .` y leer `AGENTS.md` + `MEMORY.md` + `graphify-out/GRAPH_REPORT.md`.
2. **Análisis**: `/opsx:explore` — confirmar objetivo, alcance y riesgos con el usuario.
3. **Plan**: `/opsx:propose <cambio>` — generar `proposal.md`, `design.md`, `tasks.md`.
4. **Harness**: verificar `verify-setup` y checklist de Fase 3 antes de codear.
5. **Desarrollo**: `/opsx:apply` — una tarea a la vez, con tests.
6. **Testing**: tests + lint + escenarios dados en los specs.
7. **Corrección**: identificar causa raíz, aplicar fix mínimo, test de regresión.
8. **Cierre**: `/opsx:archive` + `graphify update .` y confirmar commit/push.
