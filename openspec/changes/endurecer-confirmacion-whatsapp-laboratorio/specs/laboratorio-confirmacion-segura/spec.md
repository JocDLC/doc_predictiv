## ADDED Requirements

### Requirement: Confirmación atribuible a una operación
El laboratorio SHALL aceptar únicamente una señal positiva posterior al clic,
atribuible al registro, origen, pestaña y operación esperados. SHALL distinguir
aceptación por Salesforce de entrega al destinatario.

#### Scenario: Éxito transitorio posterior al clic
- **WHEN** aparece una confirmación positiva válida después del clic y desaparece antes del siguiente polling
- **THEN** el observador previamente instalado conserva evidencia y permite confirmar aceptación por Salesforce

#### Scenario: Aviso previo, negativo o ajeno
- **WHEN** existe un toast anterior, “WhatsApp no enviado”, “status actualizado”, un aviso de guardado o de otra operación
- **THEN** ninguno confirma el envío actual y se guarda el motivo

#### Scenario: Señales contradictorias o timeout
- **WHEN** aparecen éxito y error sin resolución inequívoca o termina el deadline sin evidencia atribuible
- **THEN** el resultado queda no confirmado o indeterminado, sin reenvío automático

### Requirement: Identidad y clic único
El laboratorio MUST verificar identidad positiva antes de guardar y enviar,
mantener pestaña propia y efectuar como máximo un clic autorizado por reserva.

#### Scenario: Identidad ausente o cambiada
- **WHEN** falta ID, cambia el registro tras recarga o la sesión vence
- **THEN** se bloquean acciones posteriores y no se actúa sobre otro registro

#### Scenario: Pestaña cerrada o botón no accionable
- **WHEN** se cierra la pestaña propia o el botón está deshabilitado, cubierto o es ambiguo
- **THEN** no se cambia a la pestaña del usuario y no se produce un clic efectivo

### Requirement: Historial íntegro y documentación anterior al envío
El laboratorio SHALL conservar el texto real previo, agregar una sola línea con
numeración consecutiva y verificar persistencia tras recarga antes de reservar el envío.

#### Scenario: Contenido parecido a un label
- **WHEN** el historial incluye literalmente “Modificar Otra información”, tildes o varias líneas
- **THEN** la lectura y escritura conservan ese contenido sin confundirlo con botones asistivos

#### Scenario: Guardado fallido o historial concurrente
- **WHEN** la recarga no confirma el contenido esperado o detecta una modificación concurrente
- **THEN** no envía; conserva lo existente y solo recompone el intento cuando puede hacerlo sin pérdida

### Requirement: Reserva duradera entre campañas del laboratorio
El laboratorio SHALL excluir reenvíos automáticos del mismo lead/canal/origen
con envío reservado, ambiguo o confirmado, incluso al cambiar motor, campaña o archivo.

#### Scenario: Reinicio después de reservar
- **WHEN** el proceso muere antes o después del clic y luego se reanuda
- **THEN** la reserva persistida impide un segundo clic y expone necesidad de revisión

#### Scenario: Nueva importación y concurrencia
- **WHEN** otra campaña o runner intenta reservar el mismo envío
- **THEN** una transacción e índice único impiden duplicar la reserva y el clic

#### Scenario: Migración de datos históricos
- **WHEN** se migra el journal con operaciones antiguas sin evidencia u origen seguro
- **THEN** se conservan estados y reservas con bloqueo conservador, sin inventar confirmaciones

### Requirement: Evidencia y resultados históricos consultables
El laboratorio SHALL conservar resultados por corrida y evidencia mínima redactada,
con estados independientes de documentación y aceptación, accesibles desde Resultados.

#### Scenario: Otra corrida y reinicio de app
- **WHEN** se inicia otra corrida o se recarga la app
- **THEN** siguen disponibles las corridas anteriores sin mezclar sus filas ni perder reservas

#### Scenario: Verificación sin cambios
- **WHEN** se ejecuta comparación o auditoría de lectura
- **THEN** no guarda campos ni pulsa WhatsApp y la UI distingue texto previsto de texto auditado

#### Scenario: Consulta no autorizada
- **WHEN** falta token válido o se solicita un run_id inválido con traversal
- **THEN** la API rechaza la consulta y no expone evidencia ni archivos ajenos
