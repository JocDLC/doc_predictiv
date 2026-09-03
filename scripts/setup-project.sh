#!/usr/bin/env bash
# Setup por proyecto (ejecutar una vez en cada repositorio).
# Prepara el proyecto con OpenSpec y Graphify.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Inicializando OpenSpec para el proyecto..."
if command -v openspec >/dev/null 2>&1; then
    openspec init "$REPO_DIR" --tools antigravity,windsurf,codex
elif [ -x "$HOME/.npm-global/bin/openspec" ]; then
    "$HOME/.npm-global/bin/openspec" init "$REPO_DIR" --tools antigravity,windsurf,codex
else
    echo "OpenSpec no esta instalado. Corre primero ./scripts/bootstrap.sh"
    exit 1
fi

echo "==> Construyendo el grafo inicial con Graphify..."
if command -v graphify >/dev/null 2>&1; then
    (cd "$REPO_DIR" && graphify update .)
else
    echo "Graphify no esta instalado. Corre primero ./scripts/bootstrap.sh"
    exit 1
fi

echo ""
echo "Listo. Asegurate de commitear los archivos generados en openspec/ y graphify-out/."
