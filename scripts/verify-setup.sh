#!/usr/bin/env bash
# Verifica que la maquina tenga todo el harness instalado y configurado.
# Se puede ejecutar en cualquier momento: ./scripts/verify-setup.sh
# Sale con codigo 1 si falta algo, indicando exactamente que hacer.
set -euo pipefail

failures=0

test_requirement() {
    local name=$1
    local check=$2
    local fix=$3
    if eval "$check"; then
        echo "[OK]    $name"
    else
        echo "[FALTA] $name"
        echo "        Solucion: $fix"
        failures=$((failures + 1))
    fi
}

echo ""
echo "=== Verificacion del harness de desarrollo ==="
echo ""

test_requirement "Node.js 20.19.0+" "command -v node >/dev/null && printf '%s\n' '20.19.0' $(node -v | sed 's/v//') | sort -V -C" "Instala Node.js 20.19.0+ desde https://nodejs.org"
test_requirement "Python 3.10+" "command -v python3 >/dev/null || command -v python >/dev/null" "Instala Python 3.10+ desde https://python.org"
test_requirement "Git" "command -v git >/dev/null" "Instala Git desde https://git-scm.com"
test_requirement "OpenSpec CLI 1.6.0" "command -v openspec >/dev/null" "npm install -g @fission-ai/openspec@1.6.0"
test_requirement "Graphify CLI 0.10.0" "command -v graphify >/dev/null" "pipx install graphifyy==0.10.0"
test_requirement "Skill de Graphify para agentes" "test -f ~/.agents/skills/graphify/SKILL.md" "graphify install"
test_requirement "uv" "command -v uv >/dev/null" "pipx install uv"
test_requirement "Servidor MCP graphify en Antigravity" "test -f ~/.gemini/antigravity/mcp_config.json && python3 -c 'import json; print(\"graphify\" in json.load(open(\"~/.gemini/antigravity/mcp_config.json\")).get(\"mcpServers\", {}))'" "./scripts/bootstrap.sh"

echo ""
if [ "$failures" -eq 0 ]; then
    echo "Todo listo. Esta maquina tiene el harness completo."
    exit 0
else
    echo "Faltan $failures requisito(s). Aplica las soluciones indicadas y vuelve a correr este script."
    exit 1
fi
