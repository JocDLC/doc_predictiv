# Verificación del workflow Archify — Fase 5

Fecha: 2026-10-01

## Harness completo

Comando: `python automation_salesforce/harness.py verify`

- Ruff format: PASS, 48 archivos conformes.
- Ruff lint: PASS.
- Compileall: PASS.
- Suite funcional: 166 tests PASS.
- Tests del gráfico de contratos: 31 PASS.
- Total observado: 197 tests PASS.
- Cobertura: reporte XML generado; 23 módulos productivos incluidos.
- OpenSpec: 11 cambios PASS, 0 FAIL.

El primer intento del harness encontró seis archivos productivos preexistentes
fuera del formato fijado por Ruff 0.16.6. Se aplicó únicamente formateo
mecánico y la repetición completa pasó.

## Archify y navegador

- Workflow v2 con calidad `showcase`.
- `validate`, `deliver`, `check` y `browser-check`: PASS.
- `visual-check`: PASS en 1440×900 y 2048×1320, claro y oscuro.
- Containment, legibilidad, controles, temas y capturas: PASS.
- Consola y diagnósticos Archify: sin errores.

## Escenarios Given/When/Then

1. Dado un CSV exportado de Salesforce, cuando se sigue el Camino 1, entonces
   se observa su preparación, el CSV Wolkvox resultante y la carga externa.
2. Dado un CSV de Wolkvox con intentos, cuando se sigue el Camino 2, entonces
   se observan la organización, selección y documentación en Salesforce.
3. Dado un lote confirmado, cuando se elige cómo documentar, entonces existen
   una ruta manual y una ruta con bot que convergen en la confirmación.
4. Dado un contrato de entrada, cuando se consulta su formato vigente, entonces
   aparece CSV y no se anuncia XLSX.
5. Dado cualquier macrofunción, cuando se consulta su tarjeta, entonces se
   muestran entrada, salida, regla principal y comportamiento de fallo.
6. Dado un resultado que requiere corrección, cuando se sigue la excepción,
   entonces el flujo vuelve a confirmar el valor después de corregir.

## Coexistencia

- URL técnica: HTTP 200.
- URL de negocio: HTTP 200.
- SHA-256 técnico conservado:
  `1024d1e1b547451dee11f758e17fa56122e59647c645bd378ee43db3d10d7f5b`.
- SHA-256 Archify y copia publicada coincidentes:
  `52d802665c06f74427476fff5b6498e68726ade20ad83e5dc7d11b17dd38b37f`.
- No se encontraron menciones de XLSX en el artefacto publicado.

## Riesgo residual

La aceptación de comprensión por parte del usuario sigue pendiente. Los tests
de `ui_server` emitieron advertencias de limpieza de objetos `HTTPError` en tres
casos negativos; no produjeron fallos y no están relacionados con el gráfico.
