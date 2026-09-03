# Tareas: preparar-predictivo

> Convención: `[ ]` pendiente, `[x]` hecha, `[BLOQUEADA:Pn]` requiere respuesta
> a la pregunta Pn de proposal.md. Ejecutar en orden; cada fase termina con su
> verificación. El archivo objetivo es `documentador_predictivo.html` salvo indicación.

## Fase A — Selector de inicio y branding (no bloqueada)

- [x] A1. Incrustar los assets corporativos dentro del HTML, sin referencias a
      archivos externos: favicon Renault como data-URI SVG y rombo Renault SVG
      inline en el header.
- [x] A2. Agregar favicon y marca Renault en el header junto al título, sobre
      el fondo `--accent`.
- [x] A3. Crear vista HOME: dos tarjetas grandes (título, descripción e ícono),
      hover con elevación y accesibles por teclado (button nativo).
      - Tarjeta 1 → vista PREPARAR: "Preparar campaña predictiva".
      - Tarjeta 2 → "Documentar predictivo" → vista DOCUMENTAR.
- [x] A4. Envolver la UI existente en `#viewDocumentar`; crear `#viewHome` y
      `#viewPrepare`. Función `showView(id)` que oculta las demás.
- [x] A5. Botón "Inicio" en la toolbar Documentar y botón de regreso desde
      Preparar para volver al selector.
- [x] A6. Si existe sesión de recuperación (`dp_activeSession`), `loadCSVContent()`
      abre DOCUMENTAR directamente (comportamiento actual conservado).
- [ ] A7. Verificar manualmente: el flujo DOCUMENTAR completo sigue funcionando
      igual (carga CSV, atajos, progreso, pop-up) y las dos tarjetas navegan.

## Fase B — Parser de entrada (desbloqueada por P1)

- [ ] B1. Incrustar SheetJS minificado en el HTML como script inline
      (sin CDN; versión publicada hace más de 7 días). Verificar tamaño final.
- [ ] B2. Implementar `readInputFile(file)`: CSV con detección de separador
      (`;` o `,`) y encoding (UTF-8 con BOM / cp1252); XLSX → primera hoja
      vía SheetJS.
- [ ] B3. Implementar `parseInput(text|workbook)` → array de objetos fila.
- [ ] B4. Implementar mapeo de columnas: autodetección por cabecera
      (sinónimos: "Lead ID"/"ID", "Email"/"E-mail"/"Correo", "Vehículo"/"Modelo",
      "Concesionario"/"Dealer", "Teléfono"/"Celular"/"Móvil"/"Fijo") +
      selectores manuales visibles para corregir. Columnas requeridas:
      Lead ID y al menos un teléfono; el resto opcional.
- [ ] B5. Input de texto "Identificador de campaña" (obligatorio) que se
      escribe en TIPOID de todas las filas.
- [ ] B6. Si el usuario asigna columnas de fijo y celular, preferir celular
      para TEL1 (fallback: fijo).

## Fase C — Normalización de teléfonos (desbloqueada por P3, P4)

- [ ] C1. Implementar `normalizePhone(raw, country)` con la regla confirmada:
      1. Eliminar todo lo no numérico (espacios, guiones, paréntesis, `+`).
      2. Tomar los **últimos 10 dígitos**.
      3. Si quedan menos de 10 dígitos → retornar `null` (excluido).
      4. Anteponer el prefijo Wolkvox: AR `91549` / CO `957` / MX `9352`.
- [ ] C2. Tabla de casos de prueba:
      | entrada | país | esperado |
      |---|---|---|
      | `5491122774364` | AR | `915491122774364` |
      | `54 9 11 2277 4364` | AR | `915491122774364` |
      | `1122774364` | AR | `915491122774364` |
      | `054 9 11 2277-4364` | AR | `915491122774364` |
      | `+54 9 11 2277-4364` | AR | `915491122774364` |
      | `12345` | AR | `null` (excluido) |
      | `3001234567` | CO | `9573001234567` |
      | `55 1234 5678` | MX | `93525512345678` |
- [ ] C3. Script Python espejo de la lógica para verificar los casos
      (verificación determinística, luego se borra).
- [ ] C4. Solo se puebla TEL1 (decisión P4). TEL2-TEL10 quedan vacíos (`'`).

## Fase D — Mapeo y generación del CSV Wolkvox (desbloqueada por P2, P5, P7)

- [ ] D1. Constante `WOLKVOX_HEADERS` con las 51 columnas exactas del template.
- [ ] D2. Implementar `mapRowToTemplate(row)` con la convención confirmada:
      NOMBRE, APELLIDO, ID=Lead ID, TIPOID=identificador de campaña,
      SEXO=vehículo, ZONA=concesionario, DIRECCION=email, TEL1=teléfono
      normalizado. Campos sin dato → cadena vacía. Nunca inventar valores.
- [ ] D3. Implementar `validateBatch(rows)`:
      - `ID` vacío → excluir con motivo "sin Lead ID".
      - `ID` duplicado → conservar la primera aparición, excluir el resto
        ("Lead ID duplicado con fila N / lead X").
      - `TEL1` nulo → excluir ("teléfono inválido: menos de 10 dígitos").
      - `TEL1` duplicado entre leads → conservar el primero, excluir el resto
        ("teléfono duplicado con lead X"); el reporte debe identificar
        claramente ambos leads (decisión P5).
- [ ] D4. Implementar `buildWolkvoxCSV(validRows)`: `;`, CRLF, cp1252
      (usar `TextEncoder` no sirve para cp1252: construir bytes con tabla de
      mapeo o escapar a Latin-1; verificar acentos como "Buzón"/"Hernán").
- [ ] D5. Descarga con `Blob` + `<a download>`; nombre confirmado (P7):
      `predictivo_{PAIS}_{YYYYMMDD}.csv` (PAIS = ARG/COL/MEX).
- [ ] D6. Reporte de excluidos: tabla en pantalla (fila original, lead ID,
      motivo, dato conflictivo, lead conservado si es duplicado)
      + botón "Descargar reporte" (CSV `excluidos_{PAIS}_{YYYYMMDD}.csv`).

## Fase E — UI del módulo PREPARAR (desbloqueada por P6)

- [ ] E1. Dropzone propia (mismo patrón visual del módulo DOCUMENTAR).
- [ ] E2. Selector de país **visible** (decisión P6): Argentina `91549`,
      Colombia `957`, México `9352`. Argentina preseleccionada.
- [ ] E3. Pantalla de resumen antes de descargar:
      total filas leídas / válidas / excluidas, país, prefijo aplicado,
      vista previa de las primeras 5 filas generadas.
- [ ] E4. Botones: "Descargar archivo Wolkvox", "Descargar reporte de excluidos",
      "Preparar otro archivo".
- [ ] E5. Actualizar el pop-up Atajos/Características con el nuevo módulo.
- [ ] E6. Actualizar `diagrama_flujo_documentador.svg` con el nuevo flujo (o crear
      un segundo diagrama del módulo PREPARAR).

## Fase F — Verificación integral

- [ ] F1. Golden file: procesar la BD de ejemplo (P1) y comparar contra un
      archivo preparado a mano validado por el usuario (diff exacto por bytes,
      script Python temporal).
- [ ] F2. Round-trip: cargar el CSV generado en el módulo DOCUMENTAR
      (como si volviera de Wolkvox) → no debe fallar el parser.
- [ ] F3. Smoke HTML: parser Python OK.
- [ ] F4. Prueba manual guiada con el usuario y registro del tiempo en
      `RESULTADOS_DE_PRUEBA.md` (comparar contra el proceso Excel manual).
- [ ] F5. Actualizar `graphify update .` y archivar el cambio en openspec.

## Registro de decisiones tomadas durante la ejecución

- 2026-09-02: P1-P7 respondidas por el usuario (ver proposal.md). Fases B-E
  desbloqueadas.
- 2026-09-02: P8 confirmada: el módulo 1 se llama "Preparar campaña predictiva".
- 2026-09-02: agregados delta specs en `specs/preparar-campana/spec.md`
  (REQ-101 a REQ-105) para pasar `openspec validate`.
- 2026-09-02: F1 (golden file) queda condicionada a que el usuario provea una
  BD de entrada real de ejemplo; mientras tanto se usará un dataset sintético.
