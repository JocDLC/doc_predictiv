# Propuesta: Marco de trabajo replicable para desarrollo con agentes de IA

## Problema

Usas varios IDEs (Antigravity, Devin/Windsurf, Codex CLI/extensión, VS Code/Cursor) y varios computadores. Necesitas un solo arnés que:

1. Haga que cualquier agente escriba el código correcto a la primera (o lo corriga con verificación determinística).
2. Use la menor cantidad de tokens posible.
3. Sea instalable en cualquier máquina y compatible con todos los IDEs.
4. No dependa de memoria de chat: las decisiones, specs y contexto del proyecto deben vivir en archivos.

## Objetivo

Evolver `JocDLC/dev-harness-template` en un **template de GitHub** con:

- **Spec-Driven Development** con OpenSpec (`/opsx:*`).
- **Harness Engineering** constraints mecánicas (`AGENTS.md`, reglas por IDE, `verify-setup`).
- **Loop Engineering** bien definido en el workflow (goal → tools → context → verify → terminate).
- **Context Engineering** con Graphify (grafo del codebase + queries). Inspirado en Andrej Karpathy y Anthropic.
- **Instalación one-command** por máquina + GitHub Template por proyecto.

## Alcance

### Dentro del alcance

- Configuración multi-IDE: Antigravity, Devin/Windsurf, Cursor, Codex (CLI/IDE) y Claude Code.
- Scripts `bootstrap`/`verify`/`setup-project` para Windows, macOS y Linux.
- `AGENTS.md` con las 7 fases + anatomía de Loop Engineering.
- Workflow universal `/nuevo-cambio` y `/verificar-harness`.
- Estructura `openspec/` estándar.
- `graphify` integrado y MCP server para Antiogravity.
- CI mínima en GitHub Actions que audite el harness.

### Fuera del alcance

- Crear un instalador `.exe` o `.pkg`. Usaremos scripts + GitHub Template.
- Reemplazar el agente nativo de Devin/Windsurf (Cascade). El harness es agnóstico del modelo.
- Resolver falta de espacio en disco (`C:` llena). Eso es un problema del equipo, no del arnés.

## Referentes

| Referente | Aporte clave |
|-----------|--------------|
| **Andrej Karpathy** | Context engineering: llenar la ventana de contexto con la información justa. |
| **Addy Osmani** | Loop Engineering: diseñar ciclos think/act/observe/verify con automations, worktrees, skills, connectors, sub-agents y external state. |
| **Anthropic** | Evaluator-Optimizer, context engineering y agentes efectivos. |
| **OpenAI / Codex** | Codex CLI y extensión VS Code/Cursor/Windsurf; agente con worktree y verificación. |
| **Intense-Visions/harness-engineering** | Harness engineering como mechanical constraints: reglas, entropy, feedback loops, KPIs. |
| **Fission-AI/OpenSpec** | Spec-Driven Development portable: `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`. |

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| `openspec` o `graphify` cambian de versión | Fijar versiones en `bootstrap` y `versions.json`; auditar con `verify-setup`. |
| Cada IDE lee reglas en formato distinto | Generar per-IDE configs desde un `AGENTS.md` universal y actualizar scripts. |
| El usuario no libera espacio en `C:` | Instalación de plugins (Codex) seguirá fallando. Documentar workaround en `TROUBLESHOOTING.md`. |
| Over-engineering | Empezar con 7 fases + 1 workflow. No agregar herramientas que no se usen. |

## Cambios afectados

- `README.md`
- `AGENTS.md`
- `.windsurf/workflows/`
- `.cursor/`, `.codex/`, `.claude/`, `.agents/`
- `scripts/`
- `openspec/` (inicializado)
- `.github/workflows/ci.yml`
- `graphify-out/` (actualizado)

## Definición de terminado

- `verify-setup.ps1` pasa en una máquina nueva.
- `git clone` + `bootstrap.ps1` + `setup-project.ps1` deja un proyecto listo para usarse con `/opsx:explore`.
- `AGENTS.md` está sincronizado con todos los IDE-specific configs.
- La estructura del repo es un GitHub Template funcional.
