## ADDED Requirements

### Requirement: Separación entre pruebas automáticas y Salesforce real
Las pruebas contra Salesforce real MUST estar fuera de CI y deshabilitadas por defecto. Su ejecución SHALL requerir una habilitación explícita, navegador visible, sesión autenticada manualmente y confirmación del operador.

#### Scenario: Ejecución accidental
- **WHEN** se ejecuta la suite estándar o faltan las habilitaciones E2E
- **THEN** ninguna prueba navega a Salesforce ni inicia una escritura y el E2E se reporta como no solicitado

#### Scenario: Sesión autorizada
- **WHEN** el operador habilita E2E y confirma que la sesión y el entorno son correctos
- **THEN** el protocolo permite continuar únicamente con los escenarios y registros autorizados

### Requirement: Allowlist y límite de impacto
Toda prueba E2E que pueda escribir SHALL usar una allowlist local de Leads autorizados, un máximo de registros por corrida y una copia previa del valor afectado. Los IDs y valores reales MUST permanecer fuera de Git y de los informes compartidos.

#### Scenario: Lead fuera de allowlist
- **WHEN** una cola contiene un Lead no autorizado
- **THEN** el protocolo lo rechaza antes de abrir el editor y no ejecuta ninguna escritura

#### Scenario: Límite excedido
- **WHEN** la cola autorizada supera el máximo configurado para la corrida
- **THEN** el protocolo se detiene antes de procesar el primer Lead y solicita una nueva aprobación

### Requirement: Validación E2E de lectura y guardado
El protocolo SHALL verificar autenticación manual, navegador persistente, lectura de bandeja, detección de duplicados, composición, edición, guardado único, relectura persistida, resultado, snapshot y visualización en UI. El estado `guardado` MUST requerir igualdad después de reabrir el registro.

#### Scenario: Guardado verificado
- **WHEN** un Lead autorizado sin conflicto completa el flujo automático
- **THEN** se pulsa únicamente Guardar, la relectura coincide con el valor esperado, el resultado es `guardado` y la UI refleja resultado, snapshot y métricas coherentes

#### Scenario: Persistencia no confirmada
- **WHEN** el guardado aparente no produce el valor esperado después de los reintentos permitidos
- **THEN** el resultado es `error`, no se publica un snapshot confirmado y el siguiente paso requiere revisión humana

### Requirement: Validación E2E de duplicado y conflicto
El protocolo SHALL incluir un Lead marcado como duplicado y una corrección cuyo hash base no coincida. En ambos casos MUST demostrar que no se abre o aplica una escritura indebida.

#### Scenario: Lead duplicado
- **WHEN** el campo Comentario normalizado es exactamente `Lead Duplicado`
- **THEN** el runner registra `duplicado`, no abre el editor de Otra información y no pulsa Guardar

#### Scenario: Conflicto controlado
- **WHEN** el valor actual de Otra información difiere del snapshot base autorizado
- **THEN** el runner registra `conflicto`, no reemplaza el campo y mantiene disponible la resolución manual

### Requirement: Recuperación y restauración supervisadas
Antes de una escritura E2E SHALL definirse cómo restaurar el valor original. El protocolo MUST verificar reanudación después de una interrupción controlada y MUST registrar si la restauración fue ejecutada, innecesaria o quedó pendiente.

#### Scenario: Interrupción controlada
- **WHEN** se detiene el proceso después de completar un Lead y antes del siguiente
- **THEN** una nueva ejecución conserva el Lead completado, no repite su escritura y continúa desde un estado coherente

#### Scenario: Restauración requerida
- **WHEN** una prueba modifica un valor temporal que no debe conservarse
- **THEN** el operador ejecuta la restauración definida y confirma mediante relectura que el valor original quedó persistido

### Requirement: Evidencia E2E sanitizada
El protocolo SHALL producir conteos, estados, duraciones, versiones y hashes necesarios para auditoría, pero MUST NOT copiar contenido de clientes ni credenciales a documentación versionada. Capturas locales MUST revisarse antes de conservarse o compartirse.

#### Scenario: Cierre de prueba real
- **WHEN** termina una corrida E2E
- **THEN** se revisan consola, logs, resultados y capturas, se registra el resultado sanitizado y se identifica cualquier evidencia local que requiera eliminación o protección

