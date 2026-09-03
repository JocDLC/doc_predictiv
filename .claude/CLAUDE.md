# Claude Code Instructions

Proyecto: `JocDLC/dev-harness-template` — un arnés de desarrollo con agentes de IA.

## Metodología

Lee `AGENTS.md` primero. Aplica las 7 fases y Loop Engineering:

1. Goal: `openspec/changes/<cambio>/proposal.md`.
2. Tools: terminal, tests, linter, `graphify query`, `openspec validate --changes`.
3. Context: `AGENTS.md` + `MEMORY.md` + `graphify-out/GRAPH_REPORT.md`.
4. Termination: `tasks.md` completado + tests + lint + `openspec validate --changes` OK.
5. Verification: preferir determinístico (tests/types/lint) sobre juicio de LLM.
6. Error handling: si 3 iteraciones no avanzan, escalar al usuario.

## Comandos comunes

- Contexto: `graphify update .`
- Explorar: `openspec` o `/opsx:explore`
- Proponer: `/opsx:propose <cambio>`
- Aplicar: `/opsx:apply`
- Verificar: `./scripts/verify-setup.ps1` / `verify-setup.sh`
- Archivar: `/opsx:archive`

## Restricciones

- No modifiques `AGENTS.md` sin reflejar el cambio en `.cursor/`, `.windsurf/`, `.codex/`, `.agents/`.
- No uses `grep` masivo; usa `graphify query`.
- No instales `@latest` sin anotarlo en `VERSIONS.md`.
