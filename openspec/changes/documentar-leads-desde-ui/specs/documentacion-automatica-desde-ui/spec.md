## ADDED Requirements

### Requirement: Documentación automática de un lote confirmado

El sistema MUST aceptar únicamente los Leads seleccionados y confirmados desde la
UI local. Para cada Lead, MUST abrir el registro Salesforce, conservar el
contenido existente de `Otra información`, agregar los intentos de Wolkvox,
verificar el valor final y guardar solo ese campo. MUST procesar un Lead por vez.

#### Scenario: lote seleccionado correctamente

- **WHEN** el operador confirma un lote de Leads seleccionados.
- **THEN** el sistema documenta cada Lead de forma secuencial y solo modifica
  `Otra información` de los IDs confirmados.

### Requirement: Conservación de la UI y estados por Lead

La UI local MUST permanecer abierta durante el procesamiento y MUST reflejar por
Lead los estados `pendiente`, `procesando`, `documentado` o `error` sin mostrar el
texto de `Otra información`.

#### Scenario: Lead documentado

- **WHEN** la verificación y el guardado del Lead terminan correctamente.
- **THEN** la UI conserva la lista abierta y cambia ese Lead a `documentado`.

### Requirement: Errores recuperables y alternativa manual

Si el sistema no puede documentar un Lead, MUST marcarlo como `error`, registrar
solo métricas e ID enmascarado localmente y continuar con los demás. El Lead MUST
mantener disponible la opción de documentación manual.

#### Scenario: falla al guardar un Lead

- **WHEN** falla la localización, verificación o guardado de `Otra información`.
- **THEN** el sistema no reintenta automáticamente, marca el Lead como `error` y
  continúa con el siguiente Lead seleccionado.

### Requirement: Autorización y alcance de escritura

El sistema MUST requerir una confirmación explícita que indique la cantidad de
Leads antes de iniciar el lote. MUST NOT automatizar credenciales, 2FA,
reasignaciones, conversiones, cambios de estado ni campos diferentes de `Otra
información`.

#### Scenario: lote sin confirmar

- **WHEN** el operador no confirma el lote seleccionado.
- **THEN** el sistema no abre pestañas Salesforce ni realiza escrituras.
