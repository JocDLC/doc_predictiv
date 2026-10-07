# Spec: campos-salesforce-por-pais

## ADDED Requirements

### Requirement: detección homogénea y bloqueo previo de la BD Wolkvox

La app MUST detectar el país concreto de **todas** las filas de la BD, incluso las que no tienen Lead ID, a partir del prefijo de `TEL1`: Argentina `91549`, México `9352`, Colombia `957`. MUST bloquear ejecutar documentación, ejecutar cierre y exportar colas si existen países mezclados (incluidos Colombia + México), un `TEL1` vacío/inválido, un prefijo desconocido o una BD sin Leads. MUST volver a validar justo antes de cada acción, no solo durante la importación. MUST NOT omitir Leads anómalos ni mostrar/guardar los teléfonos en los errores o las colas.

#### Scenario: lote argentino homogéneo

**Given** una BD con varios Leads y `TEL1` de prefijo `91549` en todos ellos.
**When** se carga y se valida antes de ejecutar.
**Then** se identifica Argentina y el modo compatible es `argentina`.

#### Scenario: lote colombiano homogéneo

**Given** una BD cuyos `TEL1` comienzan todos con `957`.
**When** se valida.
**Then** el país concreto detectado es Colombia y el modo compatible es `colombia_mexico`.

#### Scenario: lote mexicano homogéneo

**Given** una BD cuyos `TEL1` comienzan todos con `9352`.
**When** se valida.
**Then** el país concreto detectado es México y el modo compatible es `colombia_mexico`.

#### Scenario: Colombia y México no se mezclan

**Given** una BD con un `TEL1` `957` y otro `TEL1` `9352`.
**When** se intenta ejecutar o exportar, aunque solo un Lead esté marcado.
**Then** se bloquea todo el lote y se informa la mezcla sin exponer los teléfonos.

#### Scenario: número faltante o prefijo no reconocido

**Given** un Lead sin `TEL1` o con prefijo distinto de los tres aprobados.
**When** se intenta documentar, cerrar o exportar.
**Then** la acción se bloquea sin filtrar el Lead anómalo ni enviar datos a Salesforce.

### Requirement: selector de modo, bandera y cambio guiado

La UI MUST ofrecer `Argentina` y `Colombia/México` como modos de campos y MUST mostrar una bandera local y el nombre del país **concreto detectado** en la vista del bot, además de los destinos de intentos y cierre. Si el modo elegido no coincide con el detectado, MUST ofrecer cambiar la selección al modo compatible y MUST impedir la acción hasta que coincidan. Cambiar el selector MUST NOT omitir el control de homogeneidad. La bandera MUST NOT depender de servicios externos.

#### Scenario: selección incompatible

**Given** una BD homogénea de México y el selector en Argentina.
**When** el operador pulsa `Ejecutar bot` o `Ejecutar cierre`.
**Then** la app no ejecuta nada, muestra México y ofrece cambiar a Colombia/México; solo después de un cambio explícito y nueva validación permite continuar.

#### Scenario: país no detectable

**Given** una BD mezclada o con prefijos desconocidos.
**When** el operador cambia manualmente el selector.
**Then** la BD permanece bloqueada y no se muestra una bandera como prueba de país confirmado.

### Requirement: contrato inmutable de modo por ejecución

Ambas colas MUST transportar el modo seleccionado/validado (`country: argentina` o `country: colombia_mexico`), que MUST quedar congelado por `run_id`. Los runners MUST rechazar valores desconocidos antes de abrir el navegador. Las colas históricas sin país MUST conservar la semántica argentina; como no contienen teléfonos, el runner CLI MUST NOT afirmar que comprobó sus prefijos. Las colas, resultados y logs MUST NOT incluir números de teléfono.

#### Scenario: selección durante corrida

**Given** una cola creada para Colombia/México.
**When** el selector cambia después de iniciado el bot.
**Then** la tanda sigue usando `Comentario` para intentos y `Otra información` para cierre.

#### Scenario: cola histórica y valor inválido

**Given** una cola sin `country` o una con un valor no reconocido.
**When** se valida.
**Then** la primera usa Argentina; la segunda se rechaza sin modificar Salesforce.

### Requirement: documentación en el campo de intentos del modo

El runner MUST leer, numerar, agregar, guardar y verificar intentos solo en `Otra información` para Argentina y solo en `Comentario` para Colombia/México. MUST preservar el contenido preexistente de ese campo, no duplicar intentos existentes y no modificar el campo de cierre. La marca de Lead duplicado MUST seguir impidiendo escrituras.

#### Scenario: historial preexistente colombiano

**Given** un Lead con texto previo y `INT` en `Comentario` y con contenido en `Otra información`.
**When** se documenta un intento nuevo con modo `colombia_mexico`.
**Then** el próximo `INT` y la deduplicación salen de `Comentario`, el nuevo intento se anexa ahí y `Otra información` queda intacta.

#### Scenario: IDs mexicanos independientes del formato

**Given** historial INT con IDs de varios puntos, numéricos, alfanuméricos o con ceros iniciales en la columna posterior a fecha/hora.
**When** se reintenta documentar los mismos IDs completos en el campo del país.
**Then** Python y UI los reconocen como existentes sin imponer formato, sin comparar subcadenas ni convertir a número; el runner no abre el editor, no guarda ni renumera. Los duplicados históricos no se borran automáticamente.

#### Scenario: persistencia no verificable

**Given** un formulario cuyo valor guardado no coincide con el texto preparado del campo correcto.
**When** el runner relee el Lead.
**Then** registra error/revisión y no afirma `guardado`.

### Requirement: cierre con motivo en campo apropiado y texto conservado

El cierre MUST mantener los dos motivos, los literales, las opciones de `Cualificación`/`Sub-Cualificación`, `Convert Lead → Yes` y la verificación `Cerrado + AR_LEAD_COLD`. Para Argentina MUST escribir el motivo en `Comentario` y preservar `Otra información`. Para Colombia/México MUST conservar el texto previo de `Otra información` y agregar ahí el motivo exacto, preservando `Comentario` con los intentos; si el motivo ya está persistido, MUST NOT anexarlo de nuevo. MUST verificar el texto completo esperado, los picklists, el estado y el propietario antes de declarar el cierre verificado.

#### Scenario: cierre colombiano con texto previo

**Given** `Otra información` con contenido anterior y `Comentario` con intentos.
**When** el operador cierra un Lead como `Ilocalizable` en Colombia/México.
**Then** el contenido previo se conserva, se anexa `Ilocalizable` una sola vez, `Comentario` queda intacto y la conversión solo sigue si se verificaron los campos y `Cerrado`.

#### Scenario: etiqueta mexicana de Sub cualificación

**Given** un formulario con `Cualificación` y `Sub cualificación` como controles distintos.
**When** el bot selecciona y verifica la subcualificación aprobada.
**Then** reconoce la etiqueta con espacio, selecciona solo en su desplegable y verifica el mismo campo guardado; siguen siendo válidas las etiquetas históricas con guion.

#### Scenario: lectura inicial incompleta o reanudación no verificada

**Given** un Lead cuyo estado/propietario no se pueden leer, o un Lead Cerrado pendiente de conversión cuyos picklists no se verifican.
**When** se intenta cerrar o reanudar.
**Then** queda en revisión sin escritura ni conversión; un Lead ya cerrado con propietario final y motivo compatible se informa como ya cerrado sin abrir el editor.

#### Scenario: guardado o conversión ambiguos

**Given** una respuesta tardía de Salesforce o una conversión sin verificación.
**When** termina el plazo acotado.
**Then** el Lead queda pendiente/de revisión, sin duplicar el motivo ni repetir `Yes` a ciegas.

### Requirement: snapshots y correcciones aislados por modo

Snapshots, progreso y correcciones de intentos MUST estar ligados al modo/campo que los produjo. Una copia histórica o de otro campo MUST NOT autorizar una corrección automática del campo actual. Los resultados y logs MUST NOT incluir contenido de campos ni datos del cliente.

#### Scenario: cambio de modo con snapshot previo

**Given** un snapshot de `Otra información` generado en Argentina.
**When** el usuario elige Colombia/México y solicita corregir los intentos.
**Then** la app no envía ese snapshot a editar `Comentario`; pide una lectura compatible o deja la corrección en revisión.
