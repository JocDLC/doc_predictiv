#!/usr/bin/env bash
# One-liner install: clona el template y corre bootstrap
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/JocDLC/dev-harness-template/main/scripts/install.sh | bash

set -euo pipefail

TARGET_DIR="${1:-$HOME/dev-harness-template}"
REPO="https://github.com/JocDLC/dev-harness-template.git"

if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: Git no esta instalado. Instalalo desde https://git-scm.com"
    exit 1
fi

if [ -d "$TARGET_DIR" ]; then
    echo "ERROR: El directorio $TARGET_DIR ya existe. Borralo o elige otro."
    exit 1
fi

echo "==> Clonando template..."
git clone "$REPO" "$TARGET_DIR"

echo "==> Corriendo bootstrap..."
"$TARGET_DIR/scripts/bootstrap.sh"

echo "==> Corriendo setup-project..."
"$TARGET_DIR/scripts/setup-project.sh"

echo "Listo. Entra en $TARGET_DIR y abrelo en tu IDE."
