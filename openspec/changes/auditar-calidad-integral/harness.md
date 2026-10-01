# Harness de auditoría

## Gates automáticos obligatorios

1. Formato/compilación: `python -m compileall` sobre código y tests.
2. Lint: Ruff con configuración versionada y alcance completo del módulo.
3. Unit y propiedades: lógica pura, límites y generación de entradas sintéticas.
4. Contratos: UI/colas/resultados/snapshots/correcciones/métricas.
5. Integración local: HTTP real en puerto efímero, archivos temporales y subprocess controlado.
6. Seguridad/privacidad: token, rutas, tamaño, comandos permitidos y canarios de fuga.
7. Navegador local: HTML y servidor con datos sintéticos, sin Salesforce.
8. Cobertura: líneas y ramas con gates globales y críticos.
9. Mutación selectiva: composición, validación, deduplicación, conflictos y métricas.
10. Especificación: `openspec validate --changes`.

## Gates supervisados

- Smoke de autenticación manual y adjunción a Edge persistente.
- Lectura real sin escritura.
- Lote mínimo autorizado con guardado y relectura.
- Duplicado sin edición.
- Corrección autorizada y conflicto controlado.
- Interrupción, reanudación y restauración.
- Revisión de privacidad de los artefactos locales.

## Criterios mecánicos

- Todos los comandos automáticos devuelven código 0.
- Cobertura global: líneas >= 85%, ramas >= 75%.
- Componentes críticos: líneas >= 90%, ramas >= 80%.
- Cero requisitos críticos sin evidencia.
- Cero hallazgos bloqueantes o altos abiertos para declarar `lista`.
- Cero datos reales en Git o artefactos compartidos.
- Ningún test automático no supervisado puede acceder a Salesforce.

## Evidencia mínima por ejecución

- Commit o versión, fecha, Python, navegador y sistema operativo.
- Comando exacto y clasificación de la suite.
- Passed/failed/skipped y duración.
- Resumen de cobertura y mutation score selectivo.
- En E2E: conteos y estados sanitizados, confirmación de relectura y restauración.

## Manejo de fallos

- Preservar el primer fallo reproducible y reducirlo al caso mínimo.
- Identificar causa raíz antes de modificar código productivo.
- Añadir un test de regresión por defecto confirmado.
- No eliminar ni debilitar tests existentes sin autorización explícita.
- Escalar tras tres iteraciones sin avance sobre el mismo bloqueo.
