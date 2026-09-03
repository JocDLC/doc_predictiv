# Solución de problemas

## `ENOSPC: no space left on device` al instalar extensiones en Devin/Windsurf

**Causa raíz**: el disco `C:` está lleno. Devin guarda extensiones y configuración en `C:\Users\<usuario>\AppData\Roaming\.devin` (o `C:\Users\<usuario>\AppData\Roaming\.windsurf` en versiones anteriores).

**Solución**:

1. Libera espacio en `C:` (mínimo 2-3 GB).
2. O mueve el directorio de datos de Devin a otro disco:
   - Crea una carpeta en otro disco, por ejemplo `D:\devin-data`.
   - Copia `C:\Users\<usuario>\AppData\Roaming\.devin` a `D:\devin-data`.
   - Crea un symlink con `mklink /J C:\Users\<usuario>\AppData\Roaming\.devin D:\devin-data`.
3. O instala `npm` global en otro disco:
   ```powershell
   npm config set prefix D:\npm-global
   setx PATH "%PATH%;D:\npm-global"
   ```
4. Vuelve a intentar:
   ```powershell
   C:\Users\<usuario>\AppData\Local\Programs\Windsurf\bin\devin-desktop.cmd --install-extension openai.chatgpt --force
   ```

## `openspec` o `graphify` no están en el PATH

**Causa**: el script `bootstrap` no se corrió o la sesión de terminal no se reinició después de instalar pipx/nvm.

**Solución**:

- Corre `./scripts/bootstrap.ps1` (Windows) o `./scripts/bootstrap.sh` (macOS/Linux).
- Cierra y vuelve a abrir el terminal.
- Verifica con `./scripts/verify-setup.ps1` o `./scripts/verify-setup.sh`.

## `graphify . --update` no funciona

**Causa**: el comando correcto es `graphify update .` (el path es el argumento del subcomando).

**Solución**:

```powershell
graphify update .
```

## No se puede instalar extensiones en Devin/Windsurf

La documentación de Devin dice que no permite instalar extensiones de marketplaces externos, pero el OpenAI Codex extension **sí es compatible** según OpenAI. La causa más común es falta de espacio en `C:` (ver arriba).

Comando alternativo:

```powershell
# Windows
C:\Users\<usuario>\AppData\Local\Programs\Windsurf\bin\devin-desktop.cmd --install-extension openai.chatgpt --force
```

```bash
# macOS
/Applications/Devin.app/Contents/MacOS/Devin --install-extension openai.chatgpt --force
```

## `openspec validate --changes` falla

- Asegúrate de que `openspec` está instalado: `openspec --version`.
- Asegúrate de que `openspec init` se corrió en el proyecto.
- Revisa `openspec/specs/` y `openspec/changes/` para specs malformados.
