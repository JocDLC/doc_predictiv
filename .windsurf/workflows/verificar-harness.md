---
description: Verificar que la máquina y el proyecto cumplen el harness
---

1. Lee `VERSIONS.md` y `AGENTS.md`.
2. Ejecuta `scripts/verify-setup.ps1` (Windows) o `scripts/verify-setup.sh` (macOS/Linux).
3. Si `openspec` no está instalado, muestra el comando exacto del bootstrap.
4. Si `graphify-out/` no existe, ejecuta `graphify update .`.
5. Reporta qué requisitos faltan y cómo corregirlos.
6. No continues con features hasta que el harness pase.
