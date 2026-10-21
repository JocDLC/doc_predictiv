# Propuesta: tomar-leads-selectivo

## Contexto

El Monitor de Bandeja (cambio `tomar-leads-automatico`) ya detecta los leads
`QUALIF`/`Nuevo` y puede tomarlos automáticamente con Pick Up. En la operación
real la toma no siempre debe ser automática:

- Al comenzar el día hay leads QUALIF acumulados del tiempo sin cobertura
  (noche/fin de semana). La persona quiere **ver la lista completa actual de la
  bandeja** — no solo los que el monitor ya procesó — y decidir cuáles tomar.
- Cada lead debe contactarse en sus primeros 10 minutos. La columna
  `Preferred mean of contact` (visible solo en la bandeja, no es un campo del
  Lead) indica el canal: WhatsApp, llamada telefónica, o vacío (decisión del
  auxiliar).
- La app aún no está distribuida: por ahora la toma se hace desde un único
  computador y queda a nombre del usuario logueado en Salesforce ahí.
- Una persona puede necesitar tomar un lead y **reasignarlo a otro auxiliar**
  (cambiando `Propietario del candidato`, el mismo campo que se usa para la
  cola `*_LEAD_QUALIF`); necesario también para las pruebas.

## Objetivo

Una **toma selectiva asistida**: la bandeja se lista completa bajo demanda y
la persona elige qué leads tomar; el bot ejecuta Pick Up por cada lead
elegido, con las mismas garantías que el ciclo automático.

1. Botón **"Ver bandeja ahora"**: lectura solo-listar de las bandejas
   habilitadas que muestra TODOS los leads `QUALIF`/`Nuevo` presentes en este
   momento (incluidos los acumulados fuera de horario), sin tocar nada.
2. En la tabla, cada lead candidato tiene checkbox + botón **"Tomar"**;
   también **"Tomar seleccionados"** para varios a la vez.
3. Endpoint `POST /api/monitor/take {lead_ids}`: por cada lead elegido abre
   el registro, re-verifica que el propietario siga siendo la cola, pulsa
   Pick Up y verifica el cambio — reutilizando el flujo ya probado.
4. La columna `Preferred mean of contact` se muestra destacada en la tabla
   para que la persona decida el canal de contacto tras tomar el lead.
5. Botón **"Limpiar lista"**: elimina únicamente los resultados persistidos
   del Monitor de Bandeja, después de confirmación, sin modificar Salesforce,
   bandejas, horarios, toggle ni modo prueba.

## Decisiones aprobadas (del análisis con el usuario)

- **Toma manual por selección**: la persona decide cuáles; el bot ejecuta.
  Coexiste con el ciclo automático (modo prueba / monitor activo).
- **Asignación a nombre del logueado**: Pick Up siempre asigna al usuario de
  la sesión de Salesforce del computador donde corre el servidor.
- **Reasignación a otro auxiliar**: flujo manual en Salesforce hoy; el bot
  ya tiene `return_lead_to_queue` y la mecánica de "Cambiar propietario"
  (Usuarios/Colas) como base para una futura acción "Asignar a auxiliar".
- **Seguridad intacta**: la toma selectiva respeta el candado de ciclo y la
  exclusión mutua con los bots de documentación/cierre (mismo lock).

## Fuera de alcance (documentado como features futuras)

- **Gestión de Qualif**: sección propia con la lógica especial de la primera
  hora (tomar todos los QUALIF acumulados y repartirlos). Existe un
  desarrollo previo del equipo para usar como base. *Feature nueva posible.*
- **Distribución del equipo**: tras tomar los leads se reparten entre los
  auxiliares con una lógica a definir.
- **Flujo de contacto automatizado**: si `Preferred mean of contact` =
  WhatsApp → documentar el envío en `Otra información` y pulsar el botón
  "Send To Whatsapp" (primer botón desde la derecha en la cabecera del Lead);
  si = llamada → llamar con Wolkvox y documentar; si no atiende en el primer
  intento, WhatsApp después; si vacío → decisión del auxiliar.
- **Tablero por auxiliar**: cada auxiliar tendrá un "informe personal" (URL de
  reporte, como las bandejas) con sus leads asignados — intentos hechos,
  contacto por WhatsApp, notas — más notificaciones para tomar leads. La
  identificación por auxiliar se definirá después (hoy toma a nombre de la
  sesión del computador).
- **Vista compartida en red**: requiere abrir el servidor más allá de
  loopback; se evalúa cuando la app se distribuya.

## Impacto

- `ui_server.py`: endpoints `POST /api/monitor/take` y
  `POST /api/monitor/clear-results`.
- `lead_monitor.py`: `take_leads(driver, config, state, lead_ids)` —
  reutiliza `open lead → verificar cola → Pick Up → verificar`.
- `report_reader.py`: lectura bajo demanda de la bandeja completa (ya existe
  `read_visible_unassigned_leads`).
- `documentador_predictivo.html`: botón "Ver bandeja ahora", checkboxes y
  botones Tomar en la tabla del monitor.
- `monitor_store.py`: sin cambios de esquema; se añade una operación explícita
  que vacía `results` preservando toda la configuración.
