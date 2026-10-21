## Why

El harness actual define bien el proceso SDD, el contexto y las verificaciones, pero todavía no ofrece expertos reutilizables ni garantiza que todos sus controles validen el estado real. Se propone incorporar selectivamente capacidades de ECC y aprendizaje continuo gobernado, conservando OpenSpec, Graphify y `AGENTS.md` como fuentes de verdad.

## What Changes

- Corregir primero los controles del harness que pueden reportar éxito sin comprobar versiones, terminación OpenSpec o ejecución completa en CI.
- Evaluar ECC en un worktree y un `CODEX_HOME` aislados, con versión fijada y sin modificar inicialmente el entorno global ni el repositorio de trabajo.
- Incorporar únicamente expertos y prácticas que superen una evaluación A/B: exploración, revisión de código, seguridad y pruebas.
- Añadir routing explícito, handoffs verificables y revisión independiente para los expertos adoptados.
- Incorporar continuous learning en modo observación: los aprendizajes serán candidatos trazables y no reglas activas hasta su revisión humana.
- Excluir Ruflo de este cambio.
- No reemplazar OpenSpec, Graphify, `MEMORY.md`, las siete fases ni el harness determinístico existente.

## Capabilities

### New Capabilities

- `expert-agent-workflows`: selección, aislamiento, evaluación, routing y revisión independiente de expertos inspirados en ECC.
- `governed-continuous-learning`: captura, revisión, promoción, rechazo y reversión segura de aprendizajes del sistema.

### Modified Capabilities

- `harness-engineering`: reforzar los verificadores, CI, versionado y criterios de terminación para evitar resultados falsamente exitosos antes de integrar expertos.

## Impact

- Configuración local de agentes y skills bajo directorios controlados por el proyecto.
- Scripts de verificación, CI, documentación del harness y pruebas de humo/regresión.
- `AGENTS.md`, `MEMORY.md` y Graphify conservan su autoridad; los aprendizajes promovidos deberán sincronizarse explícitamente con estas fuentes.
- No se instalarán hooks, MCP, memoria ni configuración global de ECC durante el piloto inicial.
- La implementación requerirá un entorno de prueba separado y métricas de calidad, tiempo, tokens y defectos detectados.
