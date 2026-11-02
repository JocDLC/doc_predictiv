# Modo prueba para Distribuir leads

## Problema

El módulo "Distribuir leads" ejecuta la asignación real en Salesforce. Antes de
usarlo en producción (mañana) el usuario necesita una simulación que recorra
toda la lista y valide que el flujo completo funciona — incluyendo que los
nombres de auxiliar del archivo existen como usuarios en Salesforce — sin
guardar ningún cambio.

## Propuesta

Agregar un **modo prueba** visible (casilla + banner, estilo el modo prueba del
Monitor de Bandeja) que ejecuta el mismo recorrido por lead:

- abre el registro por Lead ID y lee el propietario real;
- clasifica lo que haría la corrida real (`ya_asignado`, `cola_excluida`,
  `pickup_y_reasignar`, `reasignar`);
- para los leads que se reasignarían abre el diálogo "Cambiar propietario",
  tipea el nombre del auxiliar y verifica que el lookup lo encuentra;
- **siempre cancela el modal**: nunca pulsa Pick Up ni el botón de confirmar,
  nunca escribe en Salesforce.

Resultados con prefijo `prueba_*` en la tabla y banner de simulación.

## Non-goals

- No se cambia la semántica de los estados reales (`reasignado`,
  `ya_asignado`, ...).
- No se simula el Pick Up (cambiaría el propietario): solo se marca como
  acción que haría la corrida real.
- No se ejecuta nada de Salesforce durante carga/parseo/vista previa (ya
  es así).
