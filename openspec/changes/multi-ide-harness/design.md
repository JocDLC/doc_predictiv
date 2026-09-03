# Design: Multi-IDE Agent Harness Template

## Principios de diseño

1. **Agnóstico de IDE**: el arnés vive en archivos, no en un plugin propietario.
2. **Specs antes que código**: cada cambio pasa por `proposal.md` → `specs/` → `tasks.md`.
3. **Verificación determinística**: tests, lint, typecheck y `verify-setup` son el feedback del loop.
4. **Contexto local y actualizable**: Graphify mantiene un grafo del codebase para queries baratas.
5. **Instalación reproducible**: una máquina nueva corre `bootstrap` una vez; un proyecto corre `setup-project` una vez.

## Capas

```
┌─────────────────────────────────────────────────────────────┐
│  IDEs: Antigravity | Devin/Windsurf | Cursor | Codex | CLI  │
└──────────────────────────────┬──────────────────────────────┘
│  Universal: AGENTS.md (fases + loop + constraints)        │
├─────────────────────────────────────────────────────────────┤
│  Per-IDE rules/workflows: .cursor/ .windsurf/ .codex/      │
├─────────────────────────────────────────────────────────────┤
│  Specs: openspec/ (proposal, specs, design, tasks)         │
├─────────────────────────────────────────────────────────────┤
│  Context: graphify-out/ (graph.json + GRAPH_REPORT.md)     │
├─────────────────────────────────────────────────────────────┤
│  Automation: scripts/ (bootstrap, verify, setup-project)   │
├─────────────────────────────────────────────────────────────┤
│  Memory: MEMORY.md / project-state.md (decisions, non-goals)│
├─────────────────────────────────────────────────────────────┤
│  CI: .github/workflows/ci.yml (audit harness on push)       │
└─────────────────────────────────────────────────────────────┘
```

## Loop Engineering en el workflow

Cada `/nuevo-cambio` ejecuta un loop con los 5 componentes de Addy Osmani:

1. **Automations**: slash commands `/opsx:*` y workflows del IDE.
2. **Worktrees**: para tareas largas, usar una rama git o worktree de Git.
3. **Skills**: procedimientos reutilizables (`SKILL.md`, `.windsurf/workflows`).
4. **Connectors**: MCP servers (Graphify) y herramientas CLI (`openspec`, `graphify`).
5. **Sub-agents**: roles (explorador, planner, implementador, reviewer) en `AGENTS.md`.
6. **External state**: `openspec/specs/`, `MEMORY.md`, `graphify-out/`.

El loop tiene:

- **Goal**: la propuesta en `openspec/changes/<cambio>/proposal.md`.
- **Tools**: terminal, tests, linter, `graphify query`, `openspec validate --changes`.
- **Context**: `AGENTS.md` + `graphify-out/GRAPH_REPORT.md` + `MEMORY.md`.
- **Termination**: `tasks.md` completado + tests pasan + `openspec validate --changes` OK.
- **Verification**: determinístico (tests/lint) antes de aceptar un paso.
- **Error handling**: no-progress detection, step cap, human escalation.

## Estructura de archivos

```
dev-harness-template/
├── AGENTS.md                       # Reglas universales + 7 fases + loop
├── README.md                       # Instalación + uso
├── MEMORY.md                       # Decisiones, non-goals, state
├── VERSIONS.md                     # Versiones fijadas de herramientas
├── .github/workflows/ci.yml        # Verifica harness en cada push
├── openspec/
│   ├── specs/
│   │   └── harness-engineering.md  # Spec base del arnés
│   └── changes/
│       └── multi-ide-harness/
│           ├── proposal.md
│           ├── design.md
│           └── tasks.md
├── .windsurf/
│   ├── workflows/
│   │   ├── nuevo-cambio.md
│   │   └── verificar-harness.md
│   └── rules/
│       └── harness.md
├── .cursor/
│   └── rules/
│       └── harness.md
├── .codex/
│   └── AGENTS.md
├── .claude/
│   └── CLAUDE.md
├── .agents/
│   └── rules/
│       └── harness.md
├── graphify-out/
│   ├── graph.json
│   └── GRAPH_REPORT.md
└── scripts/
    ├── bootstrap.ps1
    ├── bootstrap.sh
    ├── setup-project.ps1
    ├── setup-project.sh
    ├── verify-setup.ps1
    └── verify-setup.sh
```

## Per-IDE config

| IDE | Archivo(s) | Formato |
|-----|------------|---------|
| Antigravity | `.agents/rules/`, `.agents/workflows/`, `~/.gemini/antigravity/mcp_config.json` | Markdown + JSON MCP |
| Devin/Windsurf | `.windsurf/workflows/*.md`, `.windsurf/rules/*.md` | Markdown frontmatter |
| Cursor | `.cursor/rules/*.md` o `.cursor/rules/*.mdc` | Markdown frontmatter |
| Codex | `.codex/AGENTS.md` | Markdown |
| Claude Code | `.claude/CLAUDE.md` | Markdown |
| VS Code | `.github/copilot-instructions.md` | Markdown |

## Versionamiento fijo

`VERSIONS.md` registra:

- Node.js mínima: `20.19.0` (requerido por OpenSpec).
- Python: `3.10+`.
- `@fission-ai/openspec`: versión fija.
- `graphifyy`: versión fija.
- `uv`: versión fija.

`bootstrap.ps1`/`bootstrap.sh` usan estas versiones en lugar de `@latest`.

## CI

GitHub Actions ejecuta:

1. `npm install -g @fission-ai/openspec@<version>`
2. `pipx install graphifyy==<version>`
3. `graphify update .`
4. `openspec validate --changes` (si aplica)
5. `verify-setup` (modo no-interactivo)

## Seguridad

- `bootstrap` no instala nada fuera de `pipx`/`npm global`.
- `verify-setup` no muta; solo audita.
- `openspec` no ejecuta código del usuario; solo genera archivos.
- `AGENTS.md` exige confirmación del usuario antes de pasos de riesgo.
