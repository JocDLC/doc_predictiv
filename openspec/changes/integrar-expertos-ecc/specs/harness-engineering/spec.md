## ADDED Requirements

### Requirement: Fuente unica y verificable de versiones
El harness MUST mantener una unica fuente de datos legible por maquina para las versiones soportadas y fijadas. Los scripts de bootstrap, verificadores, CI y `VERSIONS.md` MUST derivar de esa fuente o comprobar mecanicamente su igualdad, sin duplicar valores independientes.

#### Scenario: Versiones sincronizadas
- **WHEN** se ejecuta la verificacion de consistencia de versiones
- **THEN** bootstrap, verificadores, CI y documentacion coinciden exactamente con la fuente canonica

#### Scenario: Version duplicada en drift
- **WHEN** un script o workflow declara una version diferente de la fuente canonica
- **THEN** el gate falla con el archivo, herramienta, version esperada y version encontrada

### Requirement: Verificacion exacta y sin falsos positivos
Cada requisito de entorno MUST validar el ejecutable realmente resuelto, obtener su version efectiva, compararla con la politica declarada y devolver un codigo distinto de cero ante ausencia, incompatibilidad o salida no interpretable. La suite del verificador MUST incluir dobles controlados para versiones correctas, incorrectas y comandos ausentes.

#### Scenario: Herramienta con version incorrecta
- **WHEN** el ejecutable resuelto existe pero reporta una version distinta de la requerida
- **THEN** `verify-setup` falla e informa la ruta resuelta, la version encontrada y la version esperada

#### Scenario: Etiqueta de version sin comprobacion
- **WHEN** un check afirma validar una version pero solo comprueba la presencia del comando
- **THEN** la prueba de regresion del verificador falla y el check no puede declararse aprobado

### Requirement: Comando canonico de verificacion completa
El proyecto MUST exponer un comando canonico no destructivo que ejecute, segun aplique, formato, lint, typecheck, compilacion o build, suites de pruebas por capa, cobertura, validacion OpenSpec, consistencia multi-IDE y vigencia de Graphify. El comando MUST propagar el primer codigo de fallo y MUST reportar cualquier gate omitido con una razon y riesgo residual.

#### Scenario: Verificacion completa exitosa
- **WHEN** todos los gates aplicables se ejecutan y devuelven exito
- **THEN** el comando canonico devuelve codigo cero y produce un resumen que identifica cada gate ejecutado

#### Scenario: Gate obligatorio omitido o fallido
- **WHEN** un gate obligatorio no se ejecuta o devuelve error
- **THEN** el comando canonico devuelve un codigo distinto de cero y no emite un estado global exitoso

### Requirement: Umbrales de calidad mecanicos
El harness MUST aplicar umbrales versionados de cobertura de lineas y ramas, tanto globales como para componentes criticos, y MUST fallar si un modulo productivo queda fuera del reporte. Todo cambio de umbral MUST realizarse mediante una decision SDD explicita y MUST NOT reducirse silenciosamente.

#### Scenario: Cobertura inferior al umbral
- **WHEN** la cobertura global o critica queda por debajo del umbral versionado
- **THEN** el gate de cobertura falla e identifica la metrica y los componentes afectados

#### Scenario: Modulo productivo omitido
- **WHEN** un modulo productivo no aparece en el reporte de cobertura
- **THEN** el harness falla aunque los porcentajes de los modulos restantes superen el umbral

### Requirement: CI deterministica y multiplataforma
CI MUST ejecutar el comando canonico en Linux y Windows con dependencias fijadas, permisos minimos y sin gates blandos como `continue-on-error` o `|| true` para controles obligatorios. Los scripts POSIX MUST conservar permiso de ejecucion y los scripts PowerShell y POSIX MUST tener pruebas de humo en entornos limpios.

#### Scenario: Pull request valido
- **WHEN** un pull request ejecuta CI en Linux y Windows
- **THEN** ambas plataformas instalan las versiones fijadas, ejecutan el mismo contrato de verificacion y todos los jobs obligatorios finalizan con exito

#### Scenario: Fallo exclusivo de una plataforma
- **WHEN** el verificador falla en Windows o Linux
- **THEN** CI bloquea el cambio y conserva la plataforma, comando y salida que produjeron el fallo

### Requirement: Vigencia verificable de Graphify
CI MUST regenerar Graphify de forma determinista y comparar los artefactos resultantes con los versionados. Una diferencia no declarada MUST considerarse grafo desactualizado y MUST fallar el gate.

#### Scenario: Grafo actualizado
- **WHEN** CI ejecuta `graphify update .` sobre un checkout limpio
- **THEN** los artefactos controlados no cambian y el gate finaliza con exito

#### Scenario: Grafo obsoleto
- **WHEN** la regeneracion produce una diferencia en un artefacto controlado
- **THEN** CI falla y enumera los artefactos que deben actualizarse

### Requirement: Sincronizacion mecanica de configuraciones multi-IDE
Las reglas derivadas para cada IDE soportado MUST generarse desde una fuente comun o compararse contra ella mediante un gate. La ausencia de una configuracion declarada como soportada o cualquier drift semantico MUST impedir el cierre.

#### Scenario: Configuraciones sincronizadas
- **WHEN** se ejecuta el gate multi-IDE sobre todas las configuraciones soportadas
- **THEN** cada archivo requerido existe y representa las mismas fases, restricciones y criterios de cierre de la fuente comun

#### Scenario: Regla derivada desactualizada
- **WHEN** una configuracion omite o contradice una regla obligatoria de la fuente comun
- **THEN** el gate falla e identifica el IDE, archivo y regla divergente

### Requirement: Terminacion real de cambios OpenSpec
Un cambio MUST considerarse terminado solamente cuando todas las tareas aplicables esten marcadas, cada criterio de aceptacion tenga evidencia, el comando canonico haya pasado sobre el commit evaluado, no existan bloqueos abiertos y los riesgos aceptados tengan aprobacion explicita. `openspec validate --changes` por si solo MUST NOT satisfacer el criterio de terminacion.

#### Scenario: Cambio completamente verificado
- **WHEN** tareas, criterios, evidencia, gates y aprobaciones requeridas estan completos para el mismo commit
- **THEN** el harness permite declarar el cambio terminado y avanzar a sincronizacion o archivo

#### Scenario: OpenSpec valido con trabajo pendiente
- **WHEN** `openspec validate --changes` pasa pero existe una tarea sin marcar, evidencia ausente, un gate fallido o un bloqueo abierto
- **THEN** el harness mantiene el cambio incompleto y enumera las condiciones pendientes

### Requirement: Evidencia de ejecucion auditable
Cada ejecucion del comando canonico y de CI MUST producir un manifiesto sanitizado con commit, fecha, plataforma, versiones efectivas, comandos, codigos de salida, duraciones, resultados, omisiones justificadas, cobertura y hashes de artefactos relevantes. El manifiesto MUST NOT contener secretos, PII ni contenido operativo de clientes.

#### Scenario: Evidencia completa
- **WHEN** finaliza una verificacion local o de CI
- **THEN** el manifiesto permite reproducir y auditar la decision de exito o fallo sin consultar el historial de chat

#### Scenario: Evidencia con dato sensible
- **WHEN** el sanitizador detecta un secreto, PII o contenido operativo antes de publicar el manifiesto
- **THEN** la publicacion se bloquea o el dato se redacta y el gate registra el incidente sin exponer su valor
