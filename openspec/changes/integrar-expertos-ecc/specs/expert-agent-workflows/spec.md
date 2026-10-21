## ADDED Requirements

### Requirement: Piloto de expertos aislado y reproducible
El sistema MUST evaluar cualquier componente inspirado en ECC dentro de un worktree y un `CODEX_HOME` exclusivos del piloto, usando una version y una procedencia fijadas. El piloto MUST NOT instalar hooks, servidores MCP, memoria, reglas ni configuracion de forma global, y MUST demostrar que no modifico rutas externas a sus directorios autorizados.

#### Scenario: Ejecucion aislada del piloto
- **WHEN** se inicia el piloto de expertos desde una copia limpia del repositorio
- **THEN** el sistema registra la version y procedencia evaluadas, usa exclusivamente el worktree y el `CODEX_HOME` asignados y confirma que no hubo cambios fuera de esas rutas

#### Scenario: Intento de mutacion global
- **WHEN** un componente del piloto intenta escribir hooks, memoria, MCP o configuracion fuera de los directorios autorizados
- **THEN** el sistema bloquea la operacion, conserva evidencia del intento y marca la evaluacion como fallida

### Requirement: Contratos declarativos para expertos adoptables
Cada experto candidato MUST declarar un identificador estable, responsabilidad, disparadores, entradas requeridas, salida estructurada, herramientas permitidas, acciones prohibidas, presupuesto, verificaciones y estrategia de fallback. El catalogo inicial MUST cubrir exploracion, revision de codigo, revision de seguridad e ingenieria de pruebas sin sustituir las fases definidas en `AGENTS.md`.

#### Scenario: Validacion de un experto completo
- **WHEN** se registra un experto con todos los campos obligatorios y herramientas compatibles con su responsabilidad
- **THEN** el validador acepta el contrato y publica sus disparadores y limites para el router

#### Scenario: Experto sin limites verificables
- **WHEN** un contrato omite herramientas permitidas, acciones prohibidas, verificaciones o fallback
- **THEN** el validador lo rechaza y el experto no queda disponible para routing

### Requirement: Routing explicito y determinista
El sistema MUST seleccionar expertos mediante reglas versionadas que relacionen el tipo de trabajo y el riesgo con capacidades declaradas. Cada seleccion MUST registrar la regla aplicada y los expertos elegidos; si ninguna regla aplica, el sistema MUST continuar con el flujo nativo del harness sin invocar un experto arbitrario.

#### Scenario: Solicitud con regla aplicable
- **WHEN** una tarea coincide con una regla versionada de routing
- **THEN** el sistema selecciona solamente los expertos declarados por esa regla y registra una decision reproducible

#### Scenario: Solicitud sin regla aplicable
- **WHEN** ninguna regla de routing coincide con la tarea
- **THEN** el sistema usa el flujo nativo del harness y registra que no se delego a expertos

### Requirement: Handoffs completos y verificables
Todo handoff entre agentes MUST incluir el cambio y la tarea OpenSpec, objetivo, alcance, archivos relevantes, restricciones, supuestos, trabajo realizado, evidencia, verificaciones ejecutadas, hallazgos abiertos y riesgos residuales. El receptor MUST validar el handoff antes de continuar y MUST NOT inferir como completado un campo obligatorio ausente.

#### Scenario: Handoff valido
- **WHEN** un experto entrega un handoff con todos los campos obligatorios y referencias de evidencia resolubles
- **THEN** el receptor acepta la transferencia y vincula su trabajo posterior al mismo cambio y tarea

#### Scenario: Handoff incompleto
- **WHEN** falta evidencia, alcance, verificaciones o riesgos residuales en un handoff
- **THEN** el receptor rechaza la transferencia, mantiene la tarea incompleta y reporta los campos faltantes

### Requirement: Revision independiente antes del cierre
Los cambios de codigo producidos con ayuda de expertos MUST recibir una revision independiente ejecutada en un contexto distinto al de implementacion. El revisor MUST emitir hallazgos con severidad, ubicacion y evidencia, y cualquier hallazgo bloqueante abierto MUST impedir que la tarea se declare terminada.

#### Scenario: Revision independiente aprobada
- **WHEN** un experto distinto del implementador revisa el cambio y no deja hallazgos bloqueantes abiertos
- **THEN** el sistema registra la identidad de ambos roles, la evidencia revisada y permite continuar con los demas gates de cierre

#### Scenario: Hallazgo bloqueante abierto
- **WHEN** la revision independiente registra un hallazgo bloqueante sin resolver
- **THEN** el sistema mantiene la tarea abierta y el criterio de terminacion falla

### Requirement: Evaluacion A/B previa a la adopcion
Cada experto candidato MUST evaluarse contra el flujo nativo sobre un conjunto versionado de tareas equivalentes y bajo el mismo entorno. La evaluacion MUST registrar calidad, defectos detectados, tiempo, tokens, fallos de herramientas y cumplimiento de seguridad; los umbrales de aceptacion MUST fijarse antes de ejecutar la comparacion.

#### Scenario: Experto supera el gate de adopcion
- **WHEN** la evaluacion A/B satisface todos los umbrales predefinidos, no degrada la calidad y supera los gates de seguridad y terminacion
- **THEN** el sistema genera una recomendacion trazable de adopcion limitada al alcance evaluado

#### Scenario: Resultado inferior o incompleto
- **WHEN** el experto incumple un umbral, degrada la calidad o carece de una metrica obligatoria
- **THEN** el sistema rechaza su adopcion y conserva el flujo nativo como comportamiento activo

### Requirement: Fallo seguro y privilegio minimo
La invocacion de expertos MUST limitarse a las herramientas y rutas declaradas. Un timeout, error, salida invalida o intento de ampliar permisos MUST dejar la tarea incompleta, preservar la evidencia disponible y activar el fallback definido sin afirmar exito.

#### Scenario: Experto falla durante una tarea
- **WHEN** un experto termina con timeout, error o salida que no satisface su contrato
- **THEN** el sistema registra el fallo, no marca la tarea como completada y ejecuta el fallback autorizado

#### Scenario: Experto solicita privilegios no declarados
- **WHEN** un experto intenta usar una herramienta o ruta fuera de su contrato
- **THEN** el sistema deniega la accion y registra una violacion de politica que bloquea su adopcion
