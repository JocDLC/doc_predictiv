# Versiones fijadas del harness

Estas son las versiones mínimas y fijadas que usa el arnés. No usar `@latest` en producción.

| Herramienta | Versión mínima | Notas |
|-------------|----------------|-------|
| Node.js | `20.19.0` | Requerido por OpenSpec. |
| Python | `3.10` | Para Graphify y uv. |
| Git | `2.40` | Para worktrees y hooks. |
| `@fission-ai/openspec` | `1.6.0` | Instalación global vía `npm install -g @fission-ai/openspec@1.6.0`. |
| `graphifyy` | `0.10.0` | Instalación vía `pipx install graphifyy==0.10.0`. |
| `uv` | `latest` | Para MCP server de Graphify. Se fijará tras validar una versión estable. |

> Nota: el bootstrap actual usa `@latest` porque OpenSpec y Graphify aún no tienen versiones LTS estables. La primera versión fija se escribe en `VERSIONS.md` después de que `verify-setup` pase en al menos una máquina de producción.
