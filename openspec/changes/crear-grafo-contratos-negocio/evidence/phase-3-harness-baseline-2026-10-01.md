# Evidencia de Fase 3 — harness y protección

## Artefacto técnico protegido

- Ruta absoluta: `C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\.archify\architecture-documentador-20260928-090859\documentador-architecture.html`
- Ruta relativa: `.archify/architecture-documentador-20260928-090859/documentador-architecture.html`
- Tamaño: 774090 bytes
- Última modificación UTC: `2026-09-28T14:12:25.1147779Z`
- SHA-256: `1024D1E1B547451DEE11F758E17FA56122E59647C645BD378EE43DB3D10D7F5B`
- Recibo independiente: `documentador-architecture.delivery.json` declara el mismo tamaño y hash.

La inspección fue de solo lectura. El puerto `127.0.0.1:8791` no tenía listener
durante esta verificación, por lo que la URL no se contabiliza como aprobada. Por la
ruta solicitada (`/documentador-architecture.html`) y la ubicación del artefacto, la
raíz canónica de presentación se fija en:

`.archify/architecture-documentador-20260928-090859/`

La disponibilidad HTTP se comprobará al implementar el smoke local y nunca se
inferirá solamente porque exista el archivo.

## Rutas independientes aprobadas

| Responsabilidad | Ruta |
| --- | --- |
| Fuente contractual | `business_contract_graph/contracts.json` |
| Plantilla autocontenida | `business_contract_graph/template.html` |
| Generador/validador | `business_contract_graph/` |
| Tests | `business_contract_graph/tests/` |
| HTML de negocio | `.archify/architecture-documentador-20260928-090859/documentador-business-contracts.html` |
| HTML técnico protegido | `.archify/architecture-documentador-20260928-090859/documentador-architecture.html` |

Las rutas de salida tienen nombres resueltos distintos. El generador deberá rechazar
explícitamente cualquier salida cuyo `Path.resolve()` coincida con el HTML técnico.

URL objetivo cuando el servidor local esté activo:

- Técnica: `http://127.0.0.1:8791/documentador-architecture.html`
- Negocio: `http://127.0.0.1:8791/documentador-business-contracts.html`

## Checklist mecánico

- Dependencias de automatización fijadas en `requirements-dev.txt`.
- `uv` corregido de `latest` a la versión validada `0.11.25` en `VERSIONS.md`, bootstrap y CI.
- `unittest`, smoke del harness, Ruff, formato, compilación y cobertura disponibles.
- Comandos estándar existentes: `format-check`, `lint`, `compile`, `test`, `coverage`, `verify` y suites por capa.
- CI se ejecuta en push/PR, instala versiones fijadas y corre verificación de setup, Graphify, lint y tests.
- La máquina local pasó `scripts/verify-setup.ps1` y `python -m pip check`.
- El nuevo gráfico no requerirá dependencias de ejecución adicionales.

## Resultado de verificación

- `scripts/verify-setup.ps1`: 8 controles aprobados, 0 fallidos.
- Sintaxis PowerShell de bootstrap: aprobada.
- Sintaxis Bash de bootstrap y verificación mediante Git Bash: aprobada.
- `python -m pip check`: sin dependencias rotas.
- `python harness.py verify`: formato, lint, compilación, 145 tests, cobertura y OpenSpec aprobados.
- `openspec validate --changes`: 10 cambios aprobados, 0 fallidos.
- `git diff --check`: aprobado; solo avisos de normalización LF/CRLF.
- SHA-256 técnico después de las verificaciones: `1024D1E1B547451DEE11F758E17FA56122E59647C645BD378EE43DB3D10D7F5B` (sin cambios).

Los comandos específicos `contracts-validate`, `contracts-generate` y
`contracts-smoke` se integrarán en la tarea 1.3 junto con sus ejecutables reales;
no se crean comandos ficticios que reporten éxito antes de existir la funcionalidad.
