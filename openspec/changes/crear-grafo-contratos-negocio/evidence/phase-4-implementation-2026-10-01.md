# Evidencia de implementación — Fase 4

Fecha: 2026-10-01

## Artefactos

- Fuente contractual: `business_contract_graph/contracts.json`.
- Plantilla autocontenida: `business_contract_graph/template.html`.
- Validador, generador, CLI y smoke: `business_contract_graph/`.
- HTML generado: `.archify/architecture-documentador-20260928-090859/documentador-business-contracts.html`.
- Gráfico técnico protegido: `.archify/architecture-documentador-20260928-090859/documentador-architecture.html`.

## Resultados determinísticos

- `python automation_salesforce/harness.py business-contracts`: PASS.
- Tests nuevos: 23 PASS.
- Suite existente: 145 PASS.
- Ruff format y lint: PASS.
- Compileall: PASS.
- `openspec validate --changes`: 10 PASS, 0 FAIL.
- URL técnica: HTTP 200.
- URL de contratos: HTTP 200.
- SHA-256 técnico: `1024d1e1b547451dee11f758e17fa56122e59647c645bd378ee43db3d10d7f5b` (sin cambios).
- SHA-256 del gráfico de contratos: `62d67ad17da98fd022f87e11b6bbb7f1abe76fad44f0c5c160058deee863d0a2`.

## Casos negativos verificados

- Campo contractual ausente.
- ID duplicado.
- Relación a macrofunción inexistente.
- Requisito OpenSpec inexistente.
- Referencia OpenSpec duplicada.
- Fuente OpenSpec archivada.
- Evidencia ausente marcada incorrectamente como verificada.
- Canario sensible.
- Intento de sobrescribir el gráfico técnico.
- Comando CLI desconocido con salida distinta de cero.
- Correo, ID de Lead y asignación con apariencia de credencial.

## Smoke interactivo

- Navegador integrado conectado y URL local cargada.
- 9 macrofunciones y 4 rutas alternativas renderizadas.
- Contratos de carga y guardado inspeccionados.
- Secciones OpenSpec y evidencia técnica desplegadas.
- Referencias OpenSpec internas resolubles dentro del artefacto.
- Cierre con ratón y teclado; foco devuelto al nodo de origen.
- Temas claro/oscuro y modo presentación operativos.
- Consola: 0 errores y 0 advertencias.

El primer recorrido detectó que los enlaces `../../openspec/...` no eran
resolubles bajo la raíz HTTP del artefacto. Se corrigieron como referencias
internas autocontenidas y se añadió un test de regresión.

## Accesibilidad y diseño adaptable

- Orden de teclado: controles de tema/presentación y luego macrofunciones.
- Foco visible: contorno sólido de 3 px.
- Botones sin nombre accesible: 0.
- Diálogo etiquetado por su título y cierre con Escape.
- El foco retorna al nodo que abrió el contrato.
- Contraste mínimo claro: 4,92:1.
- Contraste mínimo oscuro: 8,97:1.
- 1440 px: 3 columnas, sin desbordamiento horizontal.
- 768 px: 2 columnas, sin desbordamiento horizontal.
- 375 px: 1 columna, contrato contenido dentro del viewport.
