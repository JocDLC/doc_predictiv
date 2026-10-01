# Harness del gráfico de contratos de negocio

## Gates obligatorios

1. Validación del esquema estructurado y unicidad de IDs.
2. Resolución de todas las referencias OpenSpec permitidas.
3. Cobertura de las nueve macrofunciones y de todos los campos contractuales.
4. Generación determinística del HTML autocontenido.
5. Comprobación de que el artefacto técnico no fue sobrescrito.
6. Lint, formato, compilación y tests del repositorio.
7. Smoke de navegador local sin Salesforce ni red externa.
8. Accesibilidad básica: teclado, foco, nombres, contraste y viewport.
9. Escaneo de privacidad de fuente, HTML y exportaciones.
10. Validación de todos los cambios OpenSpec.

## Casos negativos obligatorios

- Macrofunción sin requisito OpenSpec.
- Referencia a requisito inexistente, ambiguo o archivado no vigente.
- Contrato sin entrada, resultado, regla o comportamiento de fallo.
- Relación cuyo origen o destino no existe.
- ID duplicado.
- Dato sintético marcado como sensible en un canal publicable.
- Generación que intenta escribir en la ruta del gráfico técnico.
- HTML que necesita una dependencia externa para abrirse.

## Evidencia mínima

- Revisión y hash del gráfico técnico antes y después.
- Hash de dos generaciones consecutivas del nuevo HTML.
- Matriz macrofunción → requisito/escenario → evidencia.
- Resultados de tests, smoke, accesibilidad, privacidad y OpenSpec.
- Captura sintética o exportación del nuevo gráfico.
- Resultado de la revisión de comprensión no técnica.

## Criterio de salida

El gráfico solo podrá presentarse como vigente cuando todos los contratos tengan
fuente OpenSpec resoluble, los gates automáticos pasen, el artefacto técnico se
mantenga intacto y el usuario apruebe la terminología y la revisión visual.

## Configuración resuelta en Fase 3

- Código y fuente: `business_contract_graph/`.
- Tests: `business_contract_graph/tests/` con `unittest`.
- Salida nueva: `.archify/architecture-documentador-20260928-090859/documentador-business-contracts.html`.
- Artefacto protegido: `.archify/architecture-documentador-20260928-090859/documentador-architecture.html`.
- URL nueva prevista: `http://127.0.0.1:8791/documentador-business-contracts.html`.
- Herramientas: Python estándar y harness existente; sin dependencia productiva nueva.
- Versión `uv` fijada: `0.11.25`.

El puerto 8791 estaba inactivo durante la línea base. La disponibilidad HTTP se
validará mediante un servidor local efímero y con cierre garantizado; no se dejarán
procesos huérfanos ni se considerará aprobado un endpoint no ejecutado.
