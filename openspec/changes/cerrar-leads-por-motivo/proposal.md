# Propuesta: cerrar-leads-por-motivo

## Contexto

La app documenta intentos del predictivo en `Otra información`, pero cerrar el
Lead en Salesforce sigue siendo un proceso manual de varios pasos: editar los
campos `Comentario`, `Cualificación` y `Sub-Cualificación`, guardar, verificar
el estado `Cerrado` y ejecutar `Convert Lead → Yes` (el Lead pasa al
propietario `AR_LEAD_COLD`).

El auxiliar decide cuándo cerrar. No hay mínimo de intentos ni otras reglas
automáticas de volumen: la decisión comercial es humana. Lo que el sistema sí
controla es el procedimiento, los valores exactos y la verificación del
resultado.

## Objetivo

Cerrar Leads por lote con dos motivos soportados, seleccionados explícitamente
por el auxiliar en la UI:

- **Ilocalizable**: nunca hubo contacto efectivo.
- **Deja de interactuar**: hubo contacto pero después no se pudo continuar.

Cada Lead lleva un único motivo; el lote puede ser mixto. La ejecución requiere
confirmación explícita del auxiliar tras revisar el resumen del lote.

## Valores y recorrido Salesforce (aprobados por el usuario)

| Campo | Ilocalizable | Deja de interactuar |
|---|---|---|
| Comentario | `Ilocalizable` | `Cliente deja de interactuar` |
| Cualificación | `Rechazo no argumentado` | `Rechazo argumentado` |
| Sub-Cualificación | `Ilocalizable` (o `Permanece ilocalizable` si la primera no existe) | `Interesado en precio o condición` |

Pasos: doble clic en `Comentario` (sección Cualificación) para entrar en modo
edición, reemplazar Comentario con el literal exacto, seleccionar Cualificación
por etiqueta, esperar el desplegable dependiente Sub-Cualificación y elegir por
etiqueta (en Deja de interactuar la opción es la última de la lista), Guardar,
verificar campos y `Estado de candidato = Cerrado`, luego `Convert Lead → Yes`
y verificar propietario `AR_LEAD_COLD`.

`Otra información` no se modifica. El comentario queda solo con el literal:
nada de anotaciones extra (el dashboard los contabiliza).

## Alcance

- `documentador_predictivo.html`: sección de cierre por Lead en la cola del
  bot, selección masiva (todos/ninguno), asignación de motivo por lote,
  resumen y confirmación, estados de cierre separados de documentación.
- `automation_salesforce/lead_closure.py` (nuevo): definición cerrada de
  motivos y valores, procedimientos de edición/guardado/conversión.
- `automation_salesforce/closure_store.py` (nuevo): contrato versionado de
  solicitudes de cierre y resultados por paso.
- `automation_salesforce/run_close_queue.py` (nuevo): runner secuencial del
  lote de cierre.
- `automation_salesforce/ui_server.py`: endpoints token-protegidos para la
  cola de cierre y el lanzamiento del runner, con exclusión mutua respecto
  de documentación.
- Tests Python + Node/vm con datos sintéticos; sin Salesforce real en suite.

## Fuera de alcance

- Conteo/mínimo de INT para autorizar cierres (decisión del auxiliar).
- Verificación de la identidad del auxiliar (alcance solicitado por el
  usuario; la sesión Salesforce y los permisos siguen siendo necesarios).
- Reapertura de Leads cerrados, conversión a otras entidades o edición de
  otros campos.
- Cierre automático al terminar la documentación.

## Riesgos

- `Convert Lead → Yes` es una acción de negocio con efectos adicionales: el
  relevamiento del diálogo y un piloto autorizado son puertas de habilitación.
- Los dos pasos (Guardar, conversión) no son una transacción: un fallo
  intermedio se registra como cierre parcial verificable, no se reintenta a
  ciegas.
- Los valores de picklist dependen de Salesforce: si una etiqueta exacta no se
  encuentra, el runner aborta ese Lead sin elegir una aproximada.
