## ADDED Requirements

### Requirement: Ejecución reproducible por capas
El proyecto SHALL ofrecer comandos documentados y determinísticos para ejecutar por separado las suites unitarias, de contrato, integración local, seguridad/privacidad y navegador local. Ninguna de estas suites MUST acceder a Salesforce ni realizar acciones de negocio reales.

#### Scenario: Ejecución completa no destructiva
- **WHEN** una persona o CI ejecuta el comando estándar de verificación
- **THEN** el sistema ejecuta lint, compilación, todas las suites no destructivas y validación OpenSpec, y devuelve un código distinto de cero ante cualquier fallo

#### Scenario: Selección de una capa
- **WHEN** una persona ejecuta una suite individual
- **THEN** solo se ejecutan las pruebas de esa capa y el resultado identifica inequívocamente la capa verificada

### Requirement: Cobertura medible y protegida
El arnés MUST medir cobertura de líneas y ramas sobre el código Python productivo. El gate SHALL exigir al menos 85% de líneas y 75% de ramas globales, y 90% de líneas y 80% de ramas en componentes críticos de escritura, correcciones, servidor, persistencia y privacidad.

#### Scenario: Cobertura suficiente
- **WHEN** termina la suite automática completa
- **THEN** se genera un resumen por archivo y el comando finaliza correctamente solo si se cumplen los umbrales globales y críticos

#### Scenario: Archivo crítico excluido
- **WHEN** la configuración omite un componente crítico para elevar artificialmente la cobertura
- **THEN** una verificación del arnés falla e identifica la exclusión no permitida

### Requirement: Contratos interoperables
El arnés SHALL comprobar con fixtures sintéticos los contratos entre el HTML, colas, servidor local, resultados, snapshots, correcciones y métricas, incluyendo casos válidos, inválidos, incompletos y de versiones incompatibles.

#### Scenario: Flujo contractual válido
- **WHEN** la UI produce una cola sintética válida y el flujo local produce resultados y snapshots válidos
- **THEN** todos los consumidores aceptan los archivos y conservan los estados, conteos y relaciones esperadas sin pérdida de campos requeridos

#### Scenario: Contrato inválido
- **WHEN** un archivo carece de un campo requerido, contiene tipos incorrectos o referencia una ruta no permitida
- **THEN** el consumidor lo rechaza con un error sanitizado y no modifica archivos operativos previos

### Requirement: Robustez, reanudación e idempotencia
Las pruebas SHALL cubrir timeouts, archivos corruptos o parcialmente escritos, procesos concurrentes, interrupción entre etapas, reintento y reanudación. Repetir una entrada ya finalizada MUST NOT duplicar resultados ni volver a ejecutar una escritura confirmada.

#### Scenario: Interrupción después de persistir resultado
- **WHEN** el proceso se interrumpe después de guardar el estado de un Lead y luego se reanuda con la misma cola
- **THEN** conserva el resultado previo y continúa sin duplicarlo ni reprocesar una escritura confirmada

#### Scenario: Archivo parcial
- **WHEN** un consumidor encuentra JSON truncado o una escritura temporal incompleta
- **THEN** informa el fallo sin reemplazar el último estado válido

### Requirement: Controles de servidor local y subprocess
El arnés MUST demostrar que el servidor escucha únicamente en loopback, exige el token de sesión, acepta solo endpoints, archivos y comandos permitidos, impide ejecuciones concurrentes incompatibles y rechaza payloads abusivos.

#### Scenario: Disparo autorizado del bot local
- **WHEN** la UI envía un POST válido con token correcto y una cola permitida
- **THEN** el servidor inicia exactamente el runner permitido con argumentos separados y devuelve un estado verificable

#### Scenario: Solicitud hostil
- **WHEN** se envía un token incorrecto, path traversal, endpoint desconocido, cuerpo excesivo o comando inyectado
- **THEN** el servidor rechaza la solicitud y no crea archivos ni procesos

### Requirement: Compatibilidad de entornos
Python 3.12 MUST ser un gate de CI. La compatibilidad con Python 3.14 SHALL ejecutarse inicialmente como señal informativa y MUST registrar cualquier diferencia antes de promoverse a gate.

#### Scenario: Matriz de compatibilidad
- **WHEN** CI verifica un cambio
- **THEN** Python 3.12 debe pasar y el resultado de Python 3.14 queda visible sin ocultar fallos de compatibilidad

