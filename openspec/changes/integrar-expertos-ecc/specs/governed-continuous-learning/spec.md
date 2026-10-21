## ADDED Requirements

### Requirement: Aprendizaje en modo observacion por defecto
El sistema MUST capturar aprendizajes solamente como candidatos inactivos. La generacion de un candidato MUST NOT cambiar prompts, reglas, skills, memoria, configuracion, permisos ni comportamiento de ejecucion hasta completar una promocion gobernada.

#### Scenario: Captura de una observacion
- **WHEN** un agente identifica un patron reutilizable durante una tarea
- **THEN** el sistema crea un candidato con estado pendiente y el comportamiento activo permanece sin cambios

#### Scenario: Intento de activacion automatica
- **WHEN** un agente intenta aplicar directamente un candidato pendiente
- **THEN** el sistema bloquea la activacion y conserva las fuentes de verdad sin modificaciones

### Requirement: Candidatos trazables y sanitizados
Cada candidato MUST contener identificador estable, fecha, cambio y tarea de origen, agente originador, observacion, evidencia resoluble, alcance propuesto, confianza, impacto potencial y estado. Antes de persistirlo, el sistema MUST detectar y excluir secretos, credenciales, PII, contenido operativo de clientes y datos no necesarios para reproducir la evidencia.

#### Scenario: Candidato valido y seguro
- **WHEN** una observacion incluye todos los metadatos obligatorios y supera la verificacion de datos sensibles
- **THEN** el sistema la persiste como candidato pendiente y conserva referencias sanitizadas a su evidencia

#### Scenario: Candidato con informacion sensible
- **WHEN** la verificacion detecta secretos, PII o contenido operativo no permitido
- **THEN** el sistema rechaza o redacta el candidato, registra el motivo sin copiar el dato sensible y no lo pone a disposicion para promocion

### Requirement: Decision humana explicita
Todo candidato MUST recibir una decision humana explicita de aprobar, rechazar o solicitar cambios. La decision MUST registrar responsable, fecha, justificacion, alcance autorizado y evidencias consideradas; la ausencia de decision MUST equivaler a no aprobado.

#### Scenario: Aprobacion humana acotada
- **WHEN** un revisor autorizado aprueba un candidato para un alcance concreto
- **THEN** el sistema registra la decision y habilita solamente el paso de promocion para ese alcance

#### Scenario: Candidato rechazado
- **WHEN** un revisor rechaza un candidato con una justificacion
- **THEN** el sistema conserva el registro como rechazado, impide su promocion y evita que reaparezca automaticamente como regla activa

### Requirement: Promocion mediante SDD y verificaciones
Un candidato aprobado MUST convertirse en comportamiento activo solamente mediante un cambio OpenSpec que identifique la fuente de verdad afectada, criterios de aceptacion, tareas, pruebas y rollback. La promocion MUST pasar el harness completo y MUST sincronizar explicitamente `AGENTS.md`, `MEMORY.md`, specs o configuraciones derivadas cuando corresponda.

#### Scenario: Promocion valida
- **WHEN** un candidato aprobado se implementa mediante un cambio OpenSpec y todas sus verificaciones pasan
- **THEN** el sistema activa una version identificable del aprendizaje y enlaza candidato, decision, cambio, pruebas y archivos resultantes

#### Scenario: Promocion sin gates completos
- **WHEN** faltan tareas, pruebas, sincronizacion o una verificacion obligatoria
- **THEN** el sistema mantiene el candidato sin activar y reporta exactamente los gates pendientes

### Requirement: Autoridad, conflictos y deduplicacion
Los candidatos y aprendizajes promovidos MUST respetar la precedencia de `AGENTS.md`, OpenSpec, `MEMORY.md` y las politicas de seguridad. El sistema MUST detectar duplicados y contradicciones antes de promover, y MUST NOT permitir que un aprendizaje amplie permisos o invalide una regla autoritativa de forma implicita.

#### Scenario: Candidato duplicado
- **WHEN** un candidato nuevo representa el mismo aprendizaje y alcance que otro existente
- **THEN** el sistema lo vincula al registro existente o lo marca como duplicado sin crear dos reglas activas

#### Scenario: Conflicto con una fuente de verdad
- **WHEN** un candidato contradice una regla autoritativa o propone ampliar permisos
- **THEN** el sistema bloquea su promocion hasta que un cambio SDD resuelva explicitamente el conflicto

### Requirement: Historial inmutable y reversion segura
Toda transicion de estado y toda version promovida MUST conservar un historial auditable. Cada aprendizaje activo MUST tener un procedimiento de rollback probado que restaure la version anterior sin borrar la evidencia ni las decisiones historicas.

#### Scenario: Reversion de un aprendizaje promovido
- **WHEN** una regresion obliga a revertir un aprendizaje activo
- **THEN** el sistema restaura la version anterior, ejecuta las verificaciones de rollback y registra actor, motivo, resultado y version revertida

#### Scenario: Auditoria de ciclo de vida
- **WHEN** un auditor consulta un candidato o aprendizaje activo
- **THEN** el sistema presenta su origen, decisiones, versiones, promociones, rechazos y reversiones sin alterar el historial
