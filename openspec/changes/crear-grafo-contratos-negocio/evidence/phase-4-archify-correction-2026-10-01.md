# Corrección con Archify — Fase 4

Fecha: 2026-10-01

## Artefactos vigentes

- Modelo contractual: `business_contract_graph/contracts.json`.
- Candidato Workflow v2:
  `.archify/workflow-documentador-negocio-20261001-190644/candidate.json`.
- HTML finalizado por Archify:
  `.archify/workflow-documentador-negocio-20261001-190644/documentador-business-contracts.html`.
- Copia publicada:
  `.archify/architecture-documentador-20260928-090859/documentador-business-contracts.html`.
- Gráfico técnico protegido:
  `.archify/architecture-documentador-20260928-090859/documentador-architecture.html`.

## Modelo implementado

- Camino 1: CSV de Salesforce → preparación automática → CSV Wolkvox → carga
  externa en Wolkvox.
- Camino 2: CSV de intentos Wolkvox → organización → selección → ruta manual o
  ruta con bot → confirmación en Salesforce → resultados.
- La corrección segura aparece como una excepción opcional.
- Nueve tarjetas Archify contienen `Qué recibe`, `Qué entrega`,
  `Regla principal` y `Si falla`.
- Todos los archivos operativos visibles se describen como CSV; XLSX no se
  anuncia como disponible.

## Finalización Archify

- Tipo: `workflow`, schema v2.
- Calidad: `showcase`.
- Gates `validate`, `deliver`, `check` y `browser-check`: PASS.
- Diagnósticos: 0.
- SHA-256 del candidato:
  `6a1de14bd605f3bf539acc83372c3cae33abdafda4d16409d65347628f1e3273`.
- SHA-256 del HTML:
  `52d802665c06f74427476fff5b6498e68726ade20ad83e5dc7d11b17dd38b37f`.

## Revisión visual

`visual-check` pasó en 1440×900 y 2048×1320, en temas claro y oscuro, con
containment, legibilidad, controles, temas y capturas aprobados. La inspección
perceptual confirmó que ambos caminos, la bifurcación manual/bot y la corrección
opcional se distinguen sin solapamientos.

El primer intento de captura usó una ruta demasiado larga para Windows. Se
repitió en `.archify/vis-negocio/` y pasó sin cambiar el artefacto.

## Protección del gráfico técnico

- SHA-256 antes y después:
  `1024d1e1b547451dee11f758e17fa56122e59647c645bd378ee43db3d10d7f5b`.
- El HTML técnico no fue modificado.
