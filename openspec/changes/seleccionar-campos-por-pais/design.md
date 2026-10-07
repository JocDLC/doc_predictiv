# Diseño: seleccionar-campos-por-pais

## Contratos de país y campos

| País detectado en la BD | Prefijo de `TEL1` | Modo de la UI/cola | Campo de intentos | Campo del motivo de cierre |
|---|---|---|---|---|
| Argentina | `91549` | `argentina` | `Otra información` | `Comentario` |
| México | `9352` | `colombia_mexico` | `Comentario` (sección Cualificación) | `Otra información` |
| Colombia | `957` | `colombia_mexico` | `Comentario` (sección Cualificación) | `Otra información` |

Son tres países **concretos** y dos **modos de campos**. La BD Wolkvox es homogénea por país concreto: México y Colombia en una misma BD constituyen un lote inválido aunque compartan modo. No usar el país de preparación de campaña como sustituto de inspeccionar `TEL1` en la BD cargada.

## Validación local del lote, interfaz y privacidad

1. Conservar el `TEL1` de **todas las filas parseadas del CSV** localmente para la validación, incluidas las filas que `buildLeads` descartaría por no tener Lead ID; `buildLeads` ya retiene `lead.tel` para los Leads admitidos. Validar al cargar la BD y justo antes de ejecutar documentación, ejecutar cierre, exportar cola total o exportar selección, no solo los Leads marcados o visibles. Normalizar solo representaciones inocuas (espacios/apóstrofe inicial si procede); exigir prefijo exacto de `TEL1` sin reescribir el número ni adivinar el país por sus últimos dígitos.
2. Devolver un único país concreto si todos los prefijos pertenecen al mismo país. Rechazar país mezclado, prefijo desconocido, `TEL1` vacío o inválido. Wolkvox normalmente excluye números vacíos; conservar esta comprobación de seguridad para archivos dañados. Un lote de cero Leads también es inválido. No escribir números en alertas, consola, logs, resultados ni colas; mostrar solo países detectados, recuentos y categoría de error.
3. Ofrecer un selector de dos opciones (`Argentina`, `Colombia/México`) y una bandera/etiqueta visible en la vista de cola para el país concreto detectado (usar SVG/CSS inline o recurso local; no cargar imágenes externas). Al cargar una BD válida y sin una selección previa para ese archivo, proponer el modo detectado; con una selección previa incompatible, mantenerla a la vista y pedir un cambio explícito, sin alterar una tanda en marcha. Si el modo seleccionado difiere, mostrar un control para **cambiarlo** al modo compatible; no iniciar ni exportar hasta que la persona lo confirme. Cambiarlo no evita la validación: una BD mezclada/desconocida continúa bloqueada. Antes de los botones de ejecución, presentar país y destinos de campos; no hacer cierres reales sin la confirmación de cierre existente.
4. La bandera refleja el país **detectado**, no un país supuesto por la opción `Colombia/México`. Si el usuario selecciona otro modo, la bandera y el estado de discrepancia siguen visibles. La elección debe mantenerse por archivo/sesión sin reutilizar progreso incompatible; bloquear su modificación durante una tanda o mantener la selección congelada en la cola.

## Cola y límites de garantía

- `buildBotQueue`/exportación y `buildCloseQueue` agregan `country` (`argentina` o `colombia_mexico`) solo después de validación; `ui_server` congela el valor con `run_id`. La carga de colas rechaza códigos no reconocidos **antes** de crear WebDriver; la falta de `country` en colas históricas conserva Argentina. La selección del usuario y los metadatos de resultado no incluyen teléfonos.
- La comprobación de prefijos se realiza en la UI con el CSV cargado. Un runner de CLI alimentado por un JSON histórico sin teléfonos **no puede revalidar el prefijo**: valida el contrato de país de la cola y sigue verificando campos persistidos. No afirmar que el runner verificó teléfonos que nunca recibió ni introducirlos en el JSON para simular esta garantía.

## Escritura Salesforce por modo

1. Resolver un contrato único de campos. Documentación lee, calcula `INT`, detecta `call_id` existente, agrega solo faltantes, guarda y relee **el mismo campo de intentos**. Comprueba la marca `Lead duplicado` sin confundirla con el historial y preserva el campo de cierre. El ID es texto opaco completo, independiente del país y de su cantidad de puntos, letras o ceros iniciales; se obtiene de su posición después de fecha/hora en una línea INT, no de un patrón de ID argentino. Python y UI aplican la misma extracción y comparación exacta, sin subcadenas. No se eliminan duplicados históricos automáticamente.
2. Argentina conserva el cierre probado: reemplazar el literal del motivo en `Comentario`, guardar y verificar que `Otra información` no cambió.
3. Colombia/México conserva la totalidad del texto previo de `Otra información` y anexa en una línea separada el motivo exacto una sola vez. Comprobar el valor completo en formulario y tras recargar; no cambiar `Comentario` con los intentos. Si no se puede garantizar la edición/verificación y conservación de ambos campos, abortar ese Lead antes de convertir.
4. Picklists, estado `Cerrado`, `Convert Lead → Yes` único y propietario final `AR_LEAD_COLD` no cambian. En timeout tras guardar o convertir, releer antes de decidir, no repetir motivos ni `Yes` a ciegas. Reconocer también `Sub cualificación`/`Sub cualificacion` (México) como etiquetas exactas del mismo campo, tanto al editar como al verificar. Si estado o propietario no se pudieron leer, dejar revisión sin editar. Al reanudar un estado Cerrado sin propietario final, verificar nuevamente motivo y picklists antes de convertir.
5. Snapshots, progreso, resultados y correcciones llevan modo/campo de origen. Una corrección automática con snapshot antiguo o de otro campo no se aplica; comparar hash del campo correcto antes de editar. Los estados de documentación de otro país no marcan Leads actuales como documentados.

## Pruebas y entrega

Usar DOM sintético/mocks de Selenium sin datos reales. Probar tres prefijos válidos, mezclas AR/COL, COL/MEX, discrepancia selector, teléfonos anómalos, cambio explícito, validación del lote completo frente a selección parcial, ambas colas y exportaciones; probar país congelado, compatibilidad antigua y ausencia de teléfonos en colas/logs. Probar documentación y cierre por ambos modos, duplicados, texto previo, valor persistido, protección de otro campo, correcciones y recuperación tras timeout. Ejecutar suite/lint/compilación, validar OpenSpec si la CLI está disponible, actualizar Graphify y reconstruir un ZIP mínimo con chequeo de privacidad/imports. Los pilotos de Salesforce requieren autorización aparte.
