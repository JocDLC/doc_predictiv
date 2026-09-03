# Tareas: Multi-IDE Agent Harness Template

## 1. Fijar y auditar herramientas del harness

- [ ] Crear `VERSIONS.md` con versiones pinnadas de `node`, `openspec`, `graphifyy`, `uv`, `python`.
- [ ] Actualizar `scripts/bootstrap.ps1` y `scripts/bootstrap.sh` para usar versiones fijas.
- [ ] Actualizar `scripts/verify-setup.ps1` y `scripts/verify-setup.sh` para leer `VERSIONS.md` y verificar versiones exactas.
- [ ] Instalar `openspec` y `graphify` en la máquina actual y verificar `verify-setup`.

## 2. Mejorar `AGENTS.md` con Loop Engineering

- [ ] Añadir sección "Loop Engineering" con goal, tools, context, termination, verification, error handling.
- [ ] Añadir sección "Context Engineering" basada en Karpathy/Anthropic.
- [ ] Añadir sección "Harness Engineering" con constraints mecánicas.
- [ ] Referenciar referentes (Karpathy, Osmani, Anthropic, OpenAI, harness-engineering, OpenSpec).
- [ ] Definir reglas de no-progress detection, step cap y escalation.

## 3. Configuración multi-IDE

- [ ] Crear `.cursor/rules/harness.md` con el workflow de 7 fases.
- [ ] Crear `.windsurf/rules/harness.md` con el workflow de 7 fases.
- [ ] Crear `.codex/AGENTS.md` con el workflow de 7 fases.
- [ ] Crear `.claude/CLAUDE.md` con el workflow de 7 fases.
- [ ] Crear `.agents/rules/harness.md` y `.agents/workflows/harness.md` para Antigravity.
- [ ] Crear `.windsurf/workflows/verificar-harness.md`.
- [ ] Actualizar `.windsurf/workflows/nuevo-cambio.md` para reflejar Loop Engineering.

## 4. Estructura de especificaciones y memoria

- [ ] Crear `openspec/specs/harness-engineering.md` con la spec base del arnés.
- [ ] Crear `MEMORY.md` con non-goals, decisions, project-state.
- [ ] Actualizar `setup-project.ps1`/`setup-project.sh` para inicializar `openspec/` y `MEMORY.md` en proyectos nuevos.

## 5. Scripts y CI

- [ ] Crear `scripts/verify-setup.sh` (mirror de .ps1).
- [ ] Crear `scripts/setup-project.sh` (mirror de .ps1).
- [ ] Crear `.github/workflows/ci.yml` para auditar `verify-setup` y `graphify update` en cada push.
- [ ] Crear `install.ps1` para one-liner `git clone + bootstrap`.
- [ ] Crear `install.sh` para one-liner `git clone + bootstrap`.

## 6. README y documentación

- [ ] Actualizar `README.md` con instalación, uso, estructura y referentes.
- [ ] Crear `TROUBLESHOOTING.md` con issues comunes (espacio en disco, extensiones, paths).
- [ ] Convertir repo en GitHub Template (instrucciones en README).

## 7. Verificación y cierre

- [ ] Ejecutar `graphify update .` y asegurar que `graphify-out/` está actualizado.
- [ ] Ejecutar `verify-setup` en esta máquina.
- [ ] Ejecutar `openspec validate --changes` si aplica.
- [ ] Commit y push para tenerlo disponible en todos los computadores.
- [ ] Actualizar `todo_list` y archivar el cambio con `/opsx:archive`.
