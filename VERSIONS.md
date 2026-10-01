# Versiones fijadas del harness

Estas son las versiones mínimas y fijadas que usa el arnés. No usar `@latest` en producción.

| Herramienta | Versión mínima | Notas |
|-------------|----------------|-------|
| Node.js | `20.19.0` | Requerido por OpenSpec. |
| Python | `3.10` | Para Graphify y uv. |
| Git | `2.40` | Para worktrees y hooks. |
| `@fission-ai/openspec` | `1.6.0` | Instalación global vía `npm install -g @fission-ai/openspec@1.6.0`. |
| `graphifyy` | `0.10.0` | Instalación vía `pipx install graphifyy==0.10.0`. |
| `uv` | `0.11.25` | Para MCP server de Graphify; versión validada en Windows. |

Todas las instalaciones automatizadas deben usar estas versiones fijadas.
