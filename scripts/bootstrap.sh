#!/usr/bin/env bash
# Setup por maquina (ejecutar una sola vez en cada computador).
# Instala las herramientas globales: OpenSpec CLI y el skill Graphify.
set -euo pipefail

assert_command() {
  command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' no esta instalado. $2"; exit 1; }
}

echo "==> Verificando requisitos..."
assert_command node "Instala Node.js 18+ desde https://nodejs.org"
assert_command python3 "Instala Python 3.10+ desde https://python.org"
assert_command git "Instala Git desde https://git-scm.com"

OPEN_SPEC_VERSION="1.6.0"
GRAPHIFY_VERSION="0.10.0"
UV_VERSION="latest"

echo "==> Instalando OpenSpec CLI (global) v${OPEN_SPEC_VERSION}..."
npm install -g "@fission-ai/openspec@${OPEN_SPEC_VERSION}"

echo "==> Instalando Graphify v${GRAPHIFY_VERSION} (via pipx para manejar el PATH)..."
python3 -m pip install --user pipx || true
python3 -m pipx ensurepath
python3 -m pipx install "graphifyy==${GRAPHIFY_VERSION}"

echo "==> Instalando el skill de Graphify para los agentes..."
graphify install

echo "==> Instalando uv (necesario para el servidor MCP de Graphify)..."
if ! command -v uv >/dev/null 2>&1; then
  if [ "$UV_VERSION" = "latest" ]; then
    python3 -m pipx install uv
  else
    python3 -m pipx install "uv==${UV_VERSION}"
  fi
fi

echo "==> Configurando el servidor MCP de Graphify en Antigravity..."
python3 - <<'EOF'
import json
import os

path = os.path.expanduser("~/.gemini/antigravity/mcp_config.json")
os.makedirs(os.path.dirname(path), exist_ok=True)

config = {}
if os.path.exists(path):
    with open(path) as f:
        config = json.load(f)

servers = config.setdefault("mcpServers", {})
if "graphify" in servers:
    print("El servidor MCP 'graphify' ya estaba configurado. Sin cambios.")
else:
    servers["graphify"] = {
        "command": "uv",
        "args": [
            "run", "--with", "graphifyy", "--with", "mcp",
            "-m", "graphify.serve",
            "${workspace.path}/graphify-out/graph.json",
        ],
    }
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Servidor MCP 'graphify' agregado a {path}")
EOF

echo ""
echo "Listo. Verifica con: 'openspec --version' y 'graphify --help'"
