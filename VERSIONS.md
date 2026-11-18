# Versiones fijadas del harness

Estas son las versiones mínimas y fijadas que usa el arnés. No usar `@latest` en producción.

| Herramienta | Versión mínima | Notas |
|-------------|----------------|-------|
| Node.js | `20.19.0` | Requerido por OpenSpec. |
| Python | `3.10` | Para Graphify y uv. |
| Git | `2.40` | Para worktrees y hooks. |
| `@fission-ai/openspec` | `1.6.0` | Instalación global vía `npm install -g @fission-ai/openspec@1.6.0`. |
| `graphifyy` | `0.9.105` | Instalación vía `pipx install graphifyy==0.9.105`. |
| `uv` | `0.11.25` | Para MCP server de Graphify; versión validada en Windows. |
| `agent-browser` | `0.43.0` | Laboratorio WhatsApp (motor CDP). Requiere Node `>=22` en la máquina que corre el bot (no el Node 20 del harness OpenSpec): `npm install -g --allow-scripts=agent-browser agent-browser@0.43.0`. |

Todas las instalaciones automatizadas deben usar estas versiones fijadas.
