# Spec: monitor-bandeja-leads

## ADDED Requirements

### Requirement: REQ-801: Monitoreo opt-in y cadencia fija

El servidor MUST exponer un Monitor de Bandeja que ejecuta un ciclo cada
~60 segundos solo cuando está habilitado. El monitor MUST arrancar
deshabilitado por defecto y su estado habilitado MUST persistir entre
reinicios del servidor. MUST NOT ejecutar ningún ciclo ni tocar Salesforce
mientras esté deshabilitado.

#### Scenario: arranque del servidor

**Given** un servidor recién iniciado sin habilitación previa.
**When** transcurre el intervalo del monitor.
**Then** no se abre ninguna sesión de navegador ni se consulta Salesforce.

#### Scenario: habilitación explícita

**Given** el monitor deshabilitado.
**When** el usuario lo activa desde la UI con el token de sesión.
**Then** el estado persistido queda `enabled=true` y el próximo ciclo se
ejecuta en el intervalo correspondiente.

### Requirement: REQ-802: Bandejas configurables por país

El monitor MUST soportar varias bandejas identificadas por país (AR, CO, MX),
cada una con `enabled`, `url` del reporte y `unassigned_owner` editables y
persistidos. La UI MUST permitir elegir bandejas por bandera y guardar/cambiar
la URL de cada una. MUST rechazar URLs que no sean `https://` de un reporte
Lightning. Una bandeja deshabilitada MAY quedar sin URL (cada operador puede
vigilar solo un subconjunto de países); la URL MUST ser obligatoria solo para
habilitarla. Si una bandeja falla, el ciclo MUST continuar con las demás.

#### Scenario: operador de un solo país

**Given** un operador que solo vigila Argentina.
**When** habilita `AR` con su URL y deja `CO`/`MX` deshabilitadas sin URL.
**Then** la configuración se guarda y el monitor solo revisa `AR`.

#### Scenario: habilitar bandeja sin URL

**Given** la bandeja `MX` sin URL.
**When** el usuario intenta habilitarla.
**Then** el servidor rechaza el guardado pidiendo la URL del reporte.

#### Scenario: configurar la bandeja de Colombia

**Given** la bandeja `CO` sin URL configurada.
**When** el usuario pega el link del reporte y habilita la bandera.
**Then** la configuración queda persistida y el próximo ciclo incluye esa
bandeja con su propio `unassigned_owner`.

#### Scenario: URL inválida

**Given** una URL que no corresponde a un reporte Lightning.
**When** el usuario intenta guardarla.
**Then** el servidor la rechaza y la configuración previa no se altera.

#### Scenario: una bandeja falla

**Given** dos bandejas habilitadas y una cuya URL no carga.
**When** corre el ciclo.
**Then** la bandeja fallida queda marcada con error y la otra se procesa con
normalidad.

### Requirement: REQ-803: Franjas horarias configurables

La UI MUST permitir definir una lista de franjas horarias `hh:mm–hh:mm` que
acotan la ejecución **automática** del monitor. Con lista vacía el monitor
corre siempre que esté habilitado; con franjas, fuera de ellas el ciclo MUST
omitirse con `paused_reason="fuera_de_horario"`. El servidor MUST validar
formato `HH:MM` y rechazar franjas solapadas o invertidas. La revisión manual
(`POST /api/monitor/check`, botón "Revisar ahora") MUST ejecutarse en cualquier
momento ignorando toggle y franjas, pero MUST seguir respetando el candado de
un run activo y la existencia de bandejas configuradas, y MUST NOT correr dos
ciclos simultáneos.

#### Scenario: fuera de horario

**Given** el monitor habilitado con franja `08:00–20:00`.
**When** el reloj marca 22:15 y vence el intervalo.
**Then** el ciclo se omite y el estado muestra pausa por horario.

#### Scenario: revisión manual fuera de franja

**Given** franja `08:00–20:00` y monitor deshabilitado, con la bandeja AR
configurada.
**When** el usuario pulsa "Revisar ahora" a las 22:15.
**Then** el ciclo corre igualmente y el estado refleja la revisión.

#### Scenario: revisión manual duplicada

**Given** un ciclo del monitor en curso.
**When** llega `POST /api/monitor/check`.
**Then** el servidor responde `409` sin lanzar un segundo ciclo.

#### Scenario: franja inválida

**Given** una franja `18:00–09:00` o `aa:bb–12:00`.
**When** el usuario intenta guardarla.
**Then** el servidor la rechaza con error de validación.

### Requirement: REQ-804: Detección por propietario y estado en la bandeja

Cada ciclo MUST refrescar el reporte de cada bandeja habilitada y detectar
únicamente las filas visibles cuyo propietario sea exactamente el
`unassigned_owner` configurado tras quitar espacios externos Y cuyo `Estado de
candidato` sea exactamente el `expected_status` de la bandeja (por defecto
`"Nuevo"`), reutilizando la lectura existente del reporte. MUST NOT procesar
filas de otros propietarios ni de otros estados: son dos condiciones
obligatorias simultáneas.

#### Scenario: bandeja mixta

**Given** un reporte visible con filas del propietario sin asignar y otros
propietarios.
**When** el ciclo lee la bandeja.
**Then** solo las filas sin asignar y con estado `Nuevo` y Lead ID válido pasan
a la etapa de toma, conservando el orden visible.

#### Scenario: propietario sin asignar pero estado distinto

**Given** una fila con propietario `AR_LEAD_QUALIF` pero `Estado de candidato`
diferente de `Nuevo`.
**When** el ciclo la evalúa.
**Then** la fila se ignora: no se abre el registro ni se pulsa nada.

### Requirement: REQ-805: Toma automática con verificación doble

Por cada Lead detectado, el monitor MUST abrir el registro, re-verificar que el
propietario visible siga siendo el `unassigned_owner` de la bandeja y solo
entonces pulsar el botón `Pick Up` de la barra de acciones. Tras el clic MUST
releer el propietario: el resultado `tomado` exige observar un propietario
distinto del `unassigned_owner`. MUST NOT pulsar ningún otro control ni repetir
`Pick Up` cuando la verificación no confirma el cambio.

Tras la verificación, el monitor MUST finalizar la toma: si aparece el panel
"Contact Client" MUST pulsar solo el `Save` del panel (nunca "Save & SendEmail").
La toma MUST NOT escribir `Asignado` ni otro comentario en el panel o en
`Otra información`. La documentación de un envío real de WhatsApp es una
operación de contacto separada, no una marca de toma. La
finalización es best-effort: un panel ausente o un guardado fallido MUST NOT
degradar un `tomado` ya verificado. El resultado MUST registrar el propietario
observado en `asignado_a` para que la tabla del monitor muestre a qué persona
quedó asignado el Lead.

#### Scenario: toma exitosa

**Given** un Lead cuyo propietario es el `unassigned_owner` en la bandeja y en
el registro.
**When** el monitor ejecuta Pick Up.
**Then** el propietario releído ya no es el `unassigned_owner` y el resultado
es `tomado`, `asignado_a` registra el nombre observado y el bot no escribe
en `Otra información`.

#### Scenario: lead tomado por otro operador

**Given** un Lead listado sin asignar cuyo registro muestra otro propietario
al abrirse.
**When** el monitor lo inspecciona.
**Then** el resultado es `tomado_por_otro`, MUST NOT pulsar `Pick Up` y
`asignado_a` registra al propietario observado.

#### Scenario: verificación fallida

**Given** un Lead donde el clic en Pick Up se ejecutó.
**When** el propietario releído sigue siendo el `unassigned_owner`.
**Then** el resultado es `no_verificado`, no se repite el clic y el Lead queda
marcado para revisión.

#### Scenario: panel Contact Client ausente

**Given** un Lead tomado cuyo registro no muestra el panel "Contact Client".
**When** el monitor finaliza la toma.
**Then** el resultado sigue siendo `tomado` y el bot no edita
`Otra información` ni intenta escribir una marca como alternativa al panel.

#### Scenario: modo prueba solo listar

**Given** el monitor con `solo_listar` activado (checkbox "Modo prueba").
**When** un ciclo detecta Leads QUALIF con estado `Nuevo`.
**Then** cada Lead queda registrado como `detectado` con sus columnas, MUST NOT
abrir el registro ni pulsar `Pick Up`, y al desactivar el modo los mismos
Leads vuelven a ser candidatos de toma.

### Requirement: REQ-806: Tabla del Monitor con columnas de la bandeja

La vista Monitor de Bandeja MUST mostrar una fila por Lead procesado con las
columnas visibles del reporte: fecha de creación, campaña, preferencia de
contacto, propietario, sub-tipo de interés, nombre, apellido, teléfono móvil,
nombre corto del concesionario, vehículo de interés, correo electrónico,
Lead ID y otra información. La tabla MUST NOT mostrar la columna `#` ni
`Estado de candidato` (el estado se usa solo como verificador de detección).
Los valores MUST provenir de las columnas visibles extraídas en la lectura; una
columna ausente MUST mostrar "No disponible en bandeja" sin abrir el registro
para completarla.

#### Scenario: columna ausente

**Given** una bandeja sin la columna "Otra información".
**When** se muestra un Lead tomado en el Monitor.
**Then** esa celda muestra "No disponible en bandeja" y no se hizo ninguna
lectura adicional para completarla.

### Requirement: REQ-807: Resultados y estado sin exposición indebida

El estado persistido MAY contener los `details` del Lead en el archivo local
ignorado por Git (equipo autorizado), igual que los snapshots existentes. Los
logs, la consola y los diagnósticos MUST usar solo conteos y `lead_id`
enmascarado. Las notificaciones toast MUST usar texto genérico sin datos del
cliente. Los resultados MUST NOT contener más datos que los necesarios para la
tabla del Monitor.

#### Scenario: archivo de estado

**Given** un ciclo que procesó leads.
**When** se inspecciona `monitor_state.json`.
**Then** contiene `enabled`, `bandejas`, `schedule`, `last_cycle_at`,
`paused_reason` y `results` con `lead_id`/`status`/`details`; y `git status`
no lo muestra como archivo nuevo rastreable.

### Requirement: REQ-808: Notificación en tiempo real sin polling

El servidor MUST exponer un canal de eventos (SSE) que empuje a la UI los
eventos del monitor y de los runners en el momento en que ocurren. La UI
MUST NOT consultar periódicamente el estado para descubrir novedades. Al
recibir un evento de leads tomados la UI MUST mostrar un aviso visible y
emitir un sonido. El servidor MUST emitir además una notificación toast de
Windows por tanda de leads tomados, con texto genérico sin datos del cliente.

#### Scenario: lead tomado con UI abierta

**Given** la UI conectada al canal de eventos.
**When** el monitor toma un Lead.
**Then** la UI recibe el evento, muestra el aviso y suena sin haber realizado
consultas periódicas previas.

#### Scenario: lead tomado con UI cerrada

**Given** el monitor habilitado sin navegador con la UI abierta.
**When** el monitor toma un Lead.
**Then** el usuario recibe la notificación toast de Windows igualmente.

#### Scenario: UI ociosa

**Given** la UI abierta sin eventos nuevos.
**When** transcurre un tiempo sin actividad.
**Then** la página no se redibuja y la selección de texto del usuario no se
pierde.

### Requirement: REQ-809: Convivencia con los runners existentes

El monitor MUST saltear su ciclo completo mientras una operación de
documentación o cierre esté activa, sin interferir en la sesión del navegador
que usa esa operación. De forma recíproca, los endpoints de ejecución MUST
rechazar con `409` y mensaje claro cualquier arranque de documentación o
cierre mientras un ciclo del monitor esté en curso, y la UI MUST avisarlo
tanto en la vista del monitor como en la vista del bot. El ciclo MUST
trabajar sobre una ventana dedicada del navegador del bot para que el
usuario pueda seguir usando sus propias pestañas mientras el monitor
revisa. MUST NOT reiniciar el navegador ni forzar reintentos agresivos: un
ciclo fallido espera al siguiente intervalo.

#### Scenario: bot de documentación corriendo

**Given** un proceso de documentación activo.
**When** vence el intervalo del monitor.
**Then** el ciclo se omite y queda registrado como pausado por operación
activa.

#### Scenario: documentación pedida durante un ciclo del monitor

**Given** un ciclo del monitor en curso.
**When** se invoca el endpoint de ejecución del bot.
**Then** responde `409` con un mensaje que indica esperar a que termine la
revisión, y la vista del bot muestra un aviso mientras dure el ciclo.

#### Scenario: monitor en ventana dedicada

**Given** el navegador del bot con pestañas abiertas del usuario.
**When** corre un ciclo del monitor.
**Then** la navegación ocurre en una ventana propia del monitor y las
pestañas del usuario no cambian de URL.

#### Scenario: sesión Salesforce caída

**Given** una sesión expirada que devuelve la página de login.
**When** el ciclo intenta leer la bandeja.
**Then** el monitor se pausa, emite `session_lost` y no reintenta lecturas
hasta que una verificación vuelva a ver la tabla del reporte.

### Requirement: REQ-810: Guardián del servidor local

Un proceso supervisor MUST lanzar `ui_server.py` y mantenerlo vivo: si el
proceso termina inesperadamente o deja de responder a `GET /status` tras N
sondeos consecutivos, MUST registrar la salida de la caída en un log dedicado y
reiniciarlo con backoff creciente. Si las caídas se repiten en ráfaga (≥5 en
10 minutos) MUST dejar de reintentar y dejar un marcador fatal legible. La UI
MUST mostrar un indicador de "conexión perdida" cuando el canal de eventos se
caiga y recuperarse sola al volver el servidor.

#### Scenario: el servidor muere

**Given** `ui_server.py` lanzado por el guardián.
**When** el proceso termina con error.
**Then** el guardián guarda la salida en `logs/server_crash_<ts>.log` y
reinicia el servidor automáticamente.

#### Scenario: servidor vivo pero colgado

**Given** el proceso del servidor existe pero `/status` no responde en varios
sondeos seguidos.
**When** el guardián agota los sondeos.
**Then** reinicia el servidor y registra el motivo como falta de respuesta.

#### Scenario: caídas en ráfaga

**Given** un servidor que muere apenas arranca, repetidamente.
**When** supera el límite de caídas en la ventana de tiempo.
**Then** el guardián deja de reintentar y deja el marcador fatal para revisión,
en lugar de un loop de reinicios infinito.

#### Scenario: UI pierde la conexión

**Given** la UI con el canal de eventos abierto.
**When** el servidor se reinicia.
**Then** la UI muestra el aviso de conexión perdida y se reconecta sola cuando
el servidor vuelve.
