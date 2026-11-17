# Metodología de desarrollo (obligatoria para todos los agentes)

Eres un agente que **guía al usuario paso a paso**. Nunca saltes fases. Al inicio de
cada tarea indica en qué fase estás y qué falta para completarla. Pide confirmación
al usuario antes de pasar a la siguiente fase.

Aplica la metodología **Clean Code** en todo el código: legible, mantenible y fácil
de entender (nombres descriptivos, funciones pequeñas, sin duplicación).

## Fase 0 — Contexto (Graphify)

- Si no existe `graphify-out/` o el grafo está desactualizado, ejecuta `graphify update .`.
- Si estás en un agente que soporta slash commands, usa `/graphify .`.
- Usa `/graphify query "..."` para entender el codebase antes de proponer cambios.

## Fase 0.5 — Clasificación (TDD vs SDD)

Todo cambio se clasifica antes de planificar. Va por **TDD** solo si TODAS se
cumplen:

1. Es un bugfix, un ajuste de regla o validación puntual, o un refactor con el
   comportamiento cubierto por tests.
2. Toca como máximo 3 archivos productivos, en un solo módulo o capa.
3. No agrega endpoints, vistas de UI, formatos de cola/resultado/snapshot ni
   contratos nuevos.
4. No cambia la mecánica de Salesforce (selectores, flujo de pickup o
   reasignación), seguridad ni privacidad.
5. El comportamiento esperado se puede escribir en una sola frase sin ambigüedad.
6. Se puede verificar con un test determinístico (sin navegador ni Salesforce
   en vivo).

Si alguna falla → **SDD** (Fases 1–7). El agente propone la vía y el usuario la
confirma. El flujo TDD es T1–T5, detallado en el skill `tdd`
(`.devin/skills/tdd/`): clasificar → `tdd-red` → `tdd-green` → refactor →
cierre en CHANGELOG + Gantt. Si durante TDD aparece alcance nuevo, se escala a
SDD con `/opsx:propose`.

## Fase 1 — Análisis de la propuesta

Esta fase y las siguientes aplican a la vía **SDD**. La vía TDD va directo al
flujo T1–T5 del skill `tdd` tras la confirmación de la Fase 0.5.

- Usa `/opsx:explore` para analizar la idea con el usuario: objetivos, alcance,
  alternativas, riesgos y qué partes del sistema se ven afectadas (consulta el grafo).
- No avances hasta que el usuario confirme el enfoque.

## Fase 2 — Plan (Spec)

- Usa `/opsx:propose <nombre-del-cambio>` para generar `proposal.md`, `design.md`,
  `tasks.md` y los delta specs en `openspec/changes/<cambio>/`.
- Presenta el plan al usuario, ajusta según su feedback y valida con `openspec validate --changes`.

## Fase 3 — Harness bien configurado

Antes de escribir código de features, verifica que el proyecto tenga:

- [ ] Gestor de dependencias con versiones fijadas (package.json, requirements.txt, etc.).
- [ ] Framework de tests instalado y un test de humo que pasa.
- [ ] Linter y formateador configurados.
- [ ] Scripts estándar: `test`, `lint`, `build` (o equivalentes).
- [ ] CI en GitHub Actions que ejecute tests y lint en cada push.

Si falta algo, configúralo **antes** de continuar y guía al usuario en el proceso.

## Fase 4 — Desarrollo de cada feature

- Usa `/opsx:apply` y trabaja **una tarea de `tasks.md` a la vez**, marcándolas al completar.
- Escribe o actualiza los tests de cada feature **antes o junto con** la implementación.
- Nunca elimines ni debilites tests existentes sin autorización explícita del usuario.

## Fase 5 — Testing de cada funcionalidad

- Después de cada feature: ejecuta la suite completa de tests y el linter.
- Verifica manualmente los escenarios given/when/then definidos en los specs.
- Reporta al usuario los resultados (qué pasó, qué falló).

## Fase 6 — Corrección

- Si algo falla: identifica la **causa raíz** (no el síntoma) antes de tocar código.
- Aplica la corrección mínima necesaria y agrega un test de regresión.
- Repite Fase 5 hasta que todo pase.

## Fase 7 — Cierre

- Usa `/opsx:sync` si hubo cambios manuales y `/opsx:archive` para archivar el cambio
  y fusionar los delta specs en `openspec/specs/`.
- Ejecuta `graphify update .` para actualizar el grafo de conocimiento.
- Confirma con el usuario que puede commitear y pushear.

## Loop Engineering

Cada tarea debe ejecutarse como un loop con verificación determinística:

1. **Goal**: la propuesta en `openspec/changes/<cambio>/`.
2. **Tools**: terminal, tests, linter, `graphify query`, `openspec validate --changes`.
3. **Context**: `AGENTS.md` + `MEMORY.md` + `graphify-out/GRAPH_REPORT.md`.
4. **Termination**: SDD → `tasks.md` completado + tests/lint pasan + `openspec validate --changes` OK. TDD → `tdd-green` OK + entrada en CHANGELOG `[Sin publicar]` + `log` en Gantt.
5. **Verification**: preferir verificadores determinísticos (tests, types, lint) sobre juicio del LLM.
6. **Error handling**: si 3 iteraciones no avanzan, escalar al usuario. No repetir el mismo error.

## Context Engineering

Siguiendo a Andrej Karpathy y Anthropic: la ventana de contexto es la memoria de trabajo del agente. Mantenla limpia:

- Usa `graphify query` para responder "cómo se relaciona X con Y" sin escanear archivos.
- Lee `graphify-out/GRAPH_REPORT.md` antes de preguntar de arquitectura.
- Externaliza estado a `MEMORY.md`, `openspec/` y `graphify-out/`.
- No arrastres conversaciones largas; resume al final de cada fase.

## Harness Engineering

El arnés son constraints mecánicas, no convenciones:

- `AGENTS.md` y `VERSIONS.md` son la fuente de verdad.
- `verify-setup.ps1`/`verify-setup.sh` audita la máquina.
- Cada proyecto debe pasar el checklist de Fase 3 antes de escribir features.
- Las reglas por IDE (`/.cursor/`, `/.windsurf/`, `/.codex/`, `/.agents/`) son el mismo harness con formatos distintos.

## Control de tokens

Para ahorrar dinero y evitar "context rot":

- Confirma el scope con el usuario antes de implementar.
- Usa `graphify query` en lugar de `grep` masivo.
- Trabaja una tarea de `tasks.md` a la vez.
- No re-leas archivos que no cambiaron.
- Cierra `/opsx:archive` y actualiza `graphify` al finalizar.

## Estilo de respuesta

- Primera línea: la respuesta o la acción. Sin introducción ni cierre de cortesía.
- Frases cortas (máx. 20 palabras), voz activa, una idea por frase.
- Pasos numerados si hay más de uno. Máximo 5 ítems por lista.
- Termina con UNA acción concreta si queda algo pendiente.
- Sin resúmenes de lo que ya hiciste. Explica en detalle solo si te lo piden.

## Memoria

- `MEMORY.md`: non-goals, decisiones arquitectónicas, failure patterns, estado del proyecto.
- `openspec/specs/`: requisitos y escenarios aprobados.
- `openspec/changes/archive/`: cambios históricos con contexto.
- `graphify-out/`: conocimiento del código actual.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## Tracker Gantt

Este proyecto está traqueado en el tablero Gantt del usuario
(`C:\Users\ax24611\Downloads\_dev\Grantt`). Al empezar/terminar trabajo
traqueable, reportar con:

```
node C:\Users\ax24611\Downloads\_dev\Grantt\scripts\update-tracker.mjs <comando>
```

Comandos: `list` | `start <id>` | `stop <id> --progress N` | `status <id> <estado>` |
`blocker <id> "motivo"` | `unblock <id>` | `release <projectId> "vX.Y — nombre" [--date D]` |
`add <projectId> "Nombre" --start D --end D [--deps ids] [--est N]` |
`log <id> "avance"` | `marker "texto" --date D` | `unmarker <id>`

- Este repo corresponde al proyecto `wolkvox` del tracker.
- **`release` ≠ `marker`**: las versiones del repo (v1.x, tags git) van con
  `release` → pill 🚀 en la banda del proyecto. `marker` es SOLO para
  stoppers/cortes externos (línea roja), nunca para versiones.
- `start`/`stop` documentan las horas automáticamente; `--push` publica al link
  compartido (usar solo si el usuario lo pide).
- Ver skill `gantt-tracker` para detalles.
