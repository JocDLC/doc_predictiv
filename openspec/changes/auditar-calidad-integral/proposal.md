## Why

La suite actual ejecuta 118 pruebas y Ruff correctamente, pero la mayoría usa dobles de prueba y no existe evidencia cuantitativa de cobertura ni trazabilidad completa entre requisitos, riesgos y pruebas. La aplicación automatiza operaciones sensibles en Salesforce, por lo que su preparación no puede certificarse solo por el número de tests: se necesita una auditoría independiente, reproducible y separada de los datos reales.

## What Changes

- Incorporar un arnés de calidad que mida cobertura, ejecute pruebas unitarias, de contrato e integración local y produzca resultados determinísticos en local y CI.
- Añadir pruebas independientes para los contratos entre HTML, servidor local, colas, resultados, snapshots, correcciones y métricas.
- Cubrir fallos y recuperación: timeouts, archivos inválidos o parciales, procesos concurrentes, interrupciones, reanudación e idempotencia.
- Comprobar controles de seguridad y privacidad: token local, rutas permitidas, payloads, subprocess, logs, capturas, archivos operativos y exclusiones de Git.
- Definir pruebas supervisadas de extremo a extremo con Edge y Salesforce reales, separando las pruebas sin escritura de las que requieren Leads autorizados y confirmación humana.
- Crear una matriz requisito-riesgo-prueba-evidencia y un informe final que distinga resultados automáticos, manuales, omitidos y riesgos residuales.
- Mantener intacta la lógica productiva salvo que una prueba revele un defecto; cualquier corrección funcional se propondrá y trazará por separado.

## Capabilities

### New Capabilities

- `automated-quality-harness`: ejecución reproducible de cobertura, pruebas unitarias, contratos, integración local, robustez, seguridad y compatibilidad en local y CI.
- `quality-evidence-traceability`: trazabilidad auditable entre requisitos OpenSpec, riesgos, casos de prueba, comandos, evidencia y criterio de liberación.
- `supervised-salesforce-validation`: protocolo seguro y repetible para validar Edge y Salesforce reales con mínima escritura autorizada, restauración y revisión de privacidad.

### Modified Capabilities

Ninguna. Este cambio verifica los comportamientos existentes sin modificar sus requisitos funcionales.

## Impact

- Pruebas y configuración de `automation_salesforce/`, el HTML principal y `.github/workflows/ci.yml`.
- Dependencias de desarrollo fijadas para cobertura y herramientas de prueba que se aprueben durante la configuración del arnés.
- Nuevos fixtures sintéticos sin datos de clientes, scripts de verificación y reportes de auditoría versionables.
- Ejecuciones supervisadas contra Salesforce real únicamente con autorización explícita, una cola controlada y datos operativos fuera de Git.
- No se automatizan credenciales ni 2FA; no se amplían las acciones de negocio permitidas.
