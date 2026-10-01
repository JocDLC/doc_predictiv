## ADDED Requirements

### Requirement: Matriz requisito-riesgo-prueba
La auditoría SHALL mantener una matriz versionada que relacione cada requisito OpenSpec aplicable y cada riesgo crítico con identificador, nivel, casos de prueba, comando, entorno, resultado y evidencia sanitizada.

#### Scenario: Requisito cubierto
- **WHEN** se revisa un requisito incluido en el alcance
- **THEN** la matriz permite localizar al menos una prueba o verificación explícita y su resultado más reciente

#### Scenario: Requisito sin evidencia
- **WHEN** un requisito crítico no tiene una prueba ejecutada ni una justificación aprobada
- **THEN** el informe lo marca como bloqueante y no declara la aplicación lista

### Requirement: Evidencia reproducible y honesta
Cada ejecución SHALL distinguir pruebas pasadas, fallidas, omitidas y no aplicables. La evidencia MUST registrar fecha, versión o commit, entorno, comando y resultado, sin presentar una omisión como éxito.

#### Scenario: Prueba omitida
- **WHEN** una prueba no puede ejecutarse por falta de Salesforce, navegador, permiso o dato autorizado
- **THEN** el informe registra `omitida`, la causa y el riesgo residual, sin aumentar el conteo de pruebas aprobadas

#### Scenario: Reproducción independiente
- **WHEN** otra persona ejecuta los comandos documentados sobre la misma versión y entorno soportado
- **THEN** obtiene los mismos gates y puede rastrear cualquier diferencia hasta el entorno o evidencia registrada

### Requirement: Clasificación y gestión de hallazgos
Cada defecto o brecha SHALL clasificarse como bloqueante, alto, medio o bajo, con impacto, evidencia, causa raíz cuando se conozca y decisión de corrección. Los tests existentes MUST NOT eliminarse ni debilitarse para cerrar un hallazgo sin autorización explícita.

#### Scenario: Fallo funcional descubierto
- **WHEN** una prueba nueva demuestra un comportamiento contrario al requisito
- **THEN** se conserva un test de regresión fallido, se documenta la causa raíz y se propone o aplica la corrección mínima mediante una tarea trazable

#### Scenario: Tres intentos sin avance
- **WHEN** el mismo bloqueo impide progresar durante tres iteraciones verificables
- **THEN** se escala al usuario con los intentos, evidencia y decisión necesaria

### Requirement: Criterio explícito de liberación
El informe final MUST declarar uno de: `lista`, `lista con riesgos aceptados` o `no lista`. No SHALL declarar `lista` si hay gates automáticos fallidos, requisitos críticos sin evidencia, riesgos bloqueantes o altos abiertos, o validaciones E2E obligatorias omitidas.

#### Scenario: Aplicación no lista
- **WHEN** existe al menos una condición bloqueante del criterio de liberación
- **THEN** el informe declara `no lista` y enumera las acciones necesarias para reconsiderar la decisión

#### Scenario: Riesgo aceptado
- **WHEN** un riesgo no bloqueante permanece abierto y el usuario lo acepta explícitamente
- **THEN** el informe declara `lista con riesgos aceptados` y conserva la aceptación y mitigación asociadas

### Requirement: Privacidad de la evidencia
Los artefactos versionados MUST usar únicamente datos sintéticos y MUST NOT contener Lead IDs reales, comentarios, nombres, teléfonos, emails, credenciales, cookies ni códigos 2FA. La auditoría SHALL usar canarios sintéticos para detectar fugas en consola, logs, excepciones, resultados y capturas.

#### Scenario: Fuga de canario
- **WHEN** un canario sensible aparece en un canal no permitido
- **THEN** el test falla, identifica el canal y evita publicar ese artefacto como evidencia válida

