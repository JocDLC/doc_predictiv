# Corrección de revisión: documentación en Salesforce

Fecha: 2026-10-01

## Observación recibida

La revisión indicó que el recorrido de Wolkvox hacia Salesforce no hacía visible que la documentación final se registra en Salesforce, un sistema externo.

## Corrección aplicada

- El destino común de la ruta manual y de la ruta con bot se muestra como `Documentar en Salesforce`.
- El nodo usa el tipo visual `cloud` y la etiqueta `Externo`.
- Se conserva el contrato aprobado `Confirmar en Salesforce`: la documentación y su comprobación siguen siendo un único resultado del proceso.
- No se modifican integraciones, datos ni automatizaciones.

## Evidencia de verificación

- Archify `finalize`: `validate`, `deliver`, `check` y `browser-check` aprobados.
- Archify `visual-check`: contención, legibilidad, interfaz, temas y capturas aprobados; revisión perceptual de la captura clara 1440×900 realizada.
- `python automation_salesforce/harness.py verify`: aprobado; 166 pruebas de automatización y 32 pruebas del gráfico.
- La regresión `test_salesforce_documentation_is_a_visible_external_destination` exige el texto, tipo y etiqueta externos.

## Estado

La corrección está lista para la revisión de comprensión no técnica y la aprobación explícita. No se archivó ni se hizo commit.
