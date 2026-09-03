# Memoria del proyecto

## Non-goals

- No reemplazar el agente nativo de cada IDE (Cascade, Claude, Codex, etc.). El arnés es agnóstico.
- No crear un instalador `.exe`/`.pkg` propietario. Usamos GitHub Template + scripts.
- No agregar dependencias complejas que no sean esenciales.

## Decisiones arquitectónicas

- **GitHub Template + scripts** como mecanismo de distribución multi-PC.
- **AGENTS.md** como fuente de verdad universal; configs específicas por IDE son derivadas.
- **OpenSpec** para Spec-Driven Development.
- **Graphify** para context engineering y reducción de tokens.
- **Loop Engineering** integrado en el workflow de 7 fases.

## Failure patterns

- `C:` sin espacio bloquea instalaciones de extensiones y `npm global`.
- Instalar `@latest` sin fijar versiones rompe reproducibilidad.
- Modificar `AGENTS.md` sin actualizar configs por IDE genera inconsistencias.
- No correr `graphify update` deja contexto obsoleto.

## Estado actual

- Plantilla base funcional.
- `graphify` instalado; `openspec` pendiente.
- `C:` llena; resolver antes de instalar extensiones o tools globales.
- Se está construyendo el cambio `openspec/changes/multi-ide-harness/`.
