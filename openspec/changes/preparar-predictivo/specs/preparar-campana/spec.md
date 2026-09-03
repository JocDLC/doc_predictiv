# Capability: Preparar campaña predictiva

## ADDED Requirements

### Requirement: REQ-101: Selector de inicio con dos módulos

La aplicación MUST mostrar una pantalla de inicio con branding Renault que permita
elegir entre "Preparar campaña predictiva" y "Documentar predictivo".

#### Scenario: usuario abre la aplicación sin sesión previa

**Given** el archivo `documentador_predictivo.html` abierto en el navegador sin sesión de recuperación.
**When** termina de cargar la página.
**Then** ve la pantalla de inicio con las dos tarjetas y puede entrar a cualquiera de los dos módulos con clic o teclado.

#### Scenario: usuario con sesión de documentación en curso

**Given** un CSV cargado previamente con recuperación local activa (`dp_activeSession`).
**When** el usuario actualiza o reabre la página.
**Then** la aplicación abre directamente el módulo "Documentar predictivo" con su progreso restaurado.

### Requirement: REQ-102: Carga de base de entrada en CSV o XLSX

El módulo Preparar MUST aceptar archivos CSV (separador `;` o `,`; UTF-8 o cp1252)
y XLSX (primera hoja) procesados 100% localmente, sin enviar datos a servidores.

#### Scenario: carga de un export con muchas columnas

**Given** un export de leads con columnas variadas.
**When** el usuario lo arrastra al módulo Preparar.
**Then** la app detecta las columnas de Lead ID, nombre, apellido, e-mail, vehículo, concesionario y teléfono, y muestra selectores para corregir el mapeo manualmente.

### Requirement: REQ-103: Normalización de teléfonos por país

El módulo MUST normalizar cada teléfono así: eliminar caracteres no numéricos,
tomar los últimos 10 dígitos y anteponer el prefijo del país seleccionado
(Argentina `91549`, Colombia `957`, México `9352`). Números con menos de
10 dígitos MUST quedar excluidos.

#### Scenario: teléfono argentino con prefijo internacional y espacios

**Given** el valor `+54 9 11 2277-4364` y país Argentina.
**When** se normaliza.
**Then** el resultado es `915491122774364`.

#### Scenario: teléfono inválido

**Given** el valor `12345`.
**When** se normaliza.
**Then** el registro se excluye con motivo "teléfono inválido: menos de 10 dígitos".

### Requirement: REQ-104: Generación del archivo Wolkvox sin duplicados

El módulo MUST generar un CSV con las 51 columnas exactas del template Wolkvox
(`;`, CRLF, cp1252), con `ID` y `TEL1` obligatorios y únicos, nombre
`predictivo_{PAIS}_{YYYYMMDD}.csv`, y TIPOID igual al identificador de campaña
ingresado por el usuario.

#### Scenario: dos leads comparten el mismo teléfono

**Given** dos leads válidos cuyo TEL1 normalizado es idéntico.
**When** se genera el archivo.
**Then** solo el primero se incluye y el segundo aparece en el reporte de excluidos indicando con qué lead quedó duplicado.

### Requirement: REQ-105: Reporte de excluidos

El módulo MUST mostrar en pantalla y permitir descargar un reporte CSV con cada
registro excluido: fila original, Lead ID, motivo y, si aplica, el lead conservado.

#### Scenario: preparación con exclusiones

**Given** una base con registros sin ID, con teléfonos inválidos y con duplicados.
**When** el usuario prepara el archivo.
**Then** ve el resumen (leídas / válidas / excluidas), la tabla de excluidos con motivos y puede descargar `excluidos_{PAIS}_{YYYYMMDD}.csv`.
