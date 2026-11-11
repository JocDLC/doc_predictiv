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
test_requirement "Python 3.10+" "command -v python3 >/dev/null && python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'" "Instala Python 3.10+ desde https://python.org"
test_requirement "Git 2.40+" "command -v git >/dev/null && printf '%s\n' '2.40' \$(git --version | sed -E 's/^git version ([0-9]+\.[0-9]+).*/\1/') | sort -V -C" "Instala Git 2.40+ desde https://git-scm.com"
test_requirement "OpenSpec CLI 1.6.0" "command -v openspec >/dev/null && test \"\$(openspec --version | tail -n 1)\" = '1.6.0'" "npm install -g @fission-ai/openspec@1.6.0"
test_requirement "Graphify CLI 0.9.105" "command -v graphify >/dev/null && test \"\$(graphify --version 2>/dev/null | tail -n 1)\" = 'graphify 0.9.105'" "pipx install graphifyy==0.9.105"

if [ "${CI:-}" != "true" ]; then
test_requirement "Skill de Graphify para agentes" "test -f ~/.agents/skills/graphify/SKILL.md" "graphify install --platform agents"
fi
test_requirement "uv 0.11.25" "command -v uv >/dev/null && uv --version | grep -Eq '^uv 0\\.11\\.25\\b'" "pipx install uv==0.11.25"
if [ "${CI:-}" != "true" ]; then
test_requirement "Servidor MCP graphify en Antigravity" "test -f ~/.gemini/antigravity/mcp_config.json && python3 -c 'import json, pathlib; p=pathlib.Path.home()/\".gemini/antigravity/mcp_config.json\"; raise SystemExit(\"graphify\" not in json.loads(p.read_text()).get(\"mcpServers\", {}))'" "./scripts/bootstrap.sh"
fi

echo ""
if [ "$failures" -eq 0 ]; then
    echo "Todo listo. Esta maquina tiene el harness completo."
    exit 0
else
    echo "Faltan $failures requisito(s). Aplica las soluciones indicadas y vuelve a correr este script."
    exit 1
fi
