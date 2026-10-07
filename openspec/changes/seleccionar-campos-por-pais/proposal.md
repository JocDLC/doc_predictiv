# Propuesta: seleccionar-campos-por-pais

## Contexto

La app documenta intentos en `Otra información` y escribe el motivo de cierre en `Comentario` (sección `Cualificación`). Para Colombia y México Salesforce usa los destinos inversos. El flujo de documentación, los valores de `Cualificación` y `Sub-Cualificación`, la conversión y la verificación del propietario `AR_LEAD_COLD` no cambian.

Los archivos de resultados predictivos de Wolkvox se entregan por tandas de un único país. La app ya lee `TEL1` en memoria al importar la BD y conoce los prefijos de las campañas: Argentina `91549`, México `9352` y Colombia `957`. Esta información permite detectar inconsistencias antes de escribir en Salesforce, sin llevar teléfonos a la cola del bot.

## Objetivo

Permitir elegir en la app `Argentina` o `Colombia/México` antes de documentar o cerrar. En Argentina los intentos van a `Otra información` y el motivo de cierre a `Comentario`; en Colombia/México los intentos van a `Comentario` y el motivo de cierre a `Otra información`, sin borrar el texto anterior. Mostrar con una bandera el país concreto detectado en la BD y no arrancar una tanda si el país seleccionado no coincide o la BD no es homogénea.

## Alcance

- Al cargar una BD, identificar el país concreto por `TEL1` en **todas las filas del CSV**, incluso antes de descartar registros sin Lead ID: Argentina `91549`, México `9352`, Colombia `957`. No inferir el país del nombre del archivo, de `HISTORY_TEL` ni de una muestra de Leads seleccionados.
- Selector visible de modo `Argentina` / `Colombia/México`, bandera local del país concreto detectado (Argentina, Colombia o México), nombre del país y destinos de campos en la pantalla del bot. Ofrecer cambiar la selección si no coincide con la BD; el cambio no omite la comprobación.
- Antes de documentar, cerrar o exportar cualquiera de las colas, validar el lote completo: mismo país concreto en todos los Leads, sin `TEL1` vacío, inválido ni con prefijo desconocido, y modo seleccionado compatible. Bloquear toda la tanda ante discrepancias y explicar el motivo solo con cantidades/países, sin publicar teléfonos.
- Propagar el modo elegido y validado dentro de cada cola congelada por ejecución, sin depender de cambios posteriores del selector. Mantener las colas libres de números de teléfono.
- Lectura, numeración `INT`, detección de duplicados, edición, guardado, verificación y snapshots de intentos en el campo que corresponda al modo elegido.
- Cierre por los mismos dos motivos y picklists; en Colombia/México anexar el motivo a `Otra información` conservando íntegro el texto previo y sin modificar `Comentario`.
- Adaptación de snapshots y correcciones locales para que conozcan y validen el campo fuente antes de proponer una escritura; compatibilidad explícita con colas históricas argentinas sin modo declarado.
- Pruebas sintéticas por país, validación local, documentación de uso y reconstrucción del ZIP mínimo sin datos operativos ni herramientas de desarrollo.

## Fuera de alcance

- Cambiar literales de negocio, propietario final, reglas de conversión o Salesforce API.
- Migrar automáticamente historiales ya escritos en otro campo o mezclar países en una misma BD.
- Inferir el país de Salesforce directamente por teléfono: la cola no contiene teléfonos; el prefijo del CSV es un control de coherencia, no prueba de los campos persistidos en Salesforce.
- Ejecutar operaciones sobre Leads reales sin autorización específica.

## Riesgos

- El prefijo se agrega al generar una campaña Wolkvox según el país elegido, por lo que puede validar coherencia interna del archivo, pero no garantiza el origen real de un número ni sustituye la verificación de escritura en Salesforce.
- Una BD mezclada, un teléfono faltante o un prefijo inesperado detiene la tanda completa: no se debe ignorar silenciosamente el Lead anómalo ni permitir un bypass por cambiar el selector.
- `Comentario` puede tener controles distintos en vista y edición; las pruebas deben confirmar que se lee, edita y verifica el mismo campo visible.
- Un cierre con timeout puede haber guardado el motivo: antes de reintentar se relee y no se duplica el texto ni se repite `Convert Lead → Yes` sin certeza.
- Los snapshots históricos carecen de metadatos de país/campo: no se aplican como correcciones de otro país sin comprobación explícita.
