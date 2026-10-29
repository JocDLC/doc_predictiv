# Historial de versiones

La versión vigente es la constante `APP_VERSION` de `documentador_predictivo.html`
(única fuente). `ui_server.py` la expone en `GET /status` como `version`.

Esquema: [SemVer](https://semver.org/lang/es/) — `MAYOR.MENOR.PARCHE`.

- **MAYOR**: cambios que rompen compatibilidad (formato de cola, resultados, snapshots).
- **MENOR**: funcionalidad nueva compatible.
- **PARCHE**: correcciones de defectos.

Cada versión liberada lleva un tag de Git `v<versión>`.

Los cambios hechos por la vía **TDD** (Fase 0.5 de `AGENTS.md`) se registran
acá en `[Sin publicar]` — sin artefactos OpenSpec — nombrando el test que
queda como regla permanente (no se borra ni se debilita sin autorización).

## [Sin publicar]

### Agregado

- **Vía TDD para cambios chicos**: nueva Fase 0.5 en `AGENTS.md` clasifica
  cada cambio (TDD vs SDD) con una checklist de 6 criterios confirmada por el
  usuario. `harness.py` gana `tdd-red <test_id>` (exige que el test falle,
  con aviso si falla por error y no por aserción) y `tdd-green <test_id>`
  (test + suite `unit` + `ruff check .`). Nuevo skill `tdd`
  (`.devin/skills/tdd/` + copias en `.windsurf/` y `.codex/`), reglas y
  workflows `/tdd` por IDE. Test-regla: `tests.test_harness_tdd`.

## [1.4.2] — 2026-10-27

### Cambiado

- **Monitor de Bandeja — estado visible**: tarjeta de estado con semáforo
  según el estado real (verde activo, ámbar en espera, rojo requiere atención,
  gris apagado); ya no muestra "activo · pausado" a la vez. El botón "Monitor
  activo — tocar para pausar" pasa a ser un interruptor Encendido/Apagado
  dentro de la tarjeta. Las opciones se agrupan en dos columnas
  (Comportamiento / Avisos). Intervalo del monitor: 120 s ("~2 minutos").
- **Aviso único de Windows**: la casilla "Notificar" ahora enciende/apaga el
  toast nativo con colores que emite el servidor (`/api/monitor/notify`) y
  "Probar aviso" dispara ese mismo toast (`/api/monitor/notify-test`). Se
  eliminó la notificación gris del navegador, que salía duplicada.

### Corregido

- **Monitor de Bandeja — detección invisible**: cuando el reporte se leía
  pero ningún lead matcheaba el "propietario sin asignar" (nombre de cola
  mal configurado, columna fuera de vista, estado distinto), el ciclo no
  dejaba rastro: parecía que "el bot no toma ni lista nada". Ahora cada
  ciclo loguea `[monitor] XX bandeja: N filas, M sin asignar`, lista los
  propietarios vistos cuando hay 0 coincidencias, y cuenta los QUALIF
  omitidos por estado ≠ al esperado. El match de propietario además es
  insensible a mayúsculas.
- **Monitor de Bandeja — lista vacía**: la fila "Todavía no se detectaron
  leads" salía aplastada (`line-height: 0` de la tabla); ahora tiene clase
  propia con alto y padding legibles.

## [1.4.1] — 2026-10-22

### Corregido

- **Bandeja MX**: ya toma leads — estaba deshabilitada y vacía en el estado
  persistido. Además el reporte con 0 registros mostraba "Sin resultados"
  dentro del iframe del visor sin renderizar la grilla → quemaba el timeout
  de 30 s por ciclo con un `bandeja_error` invisible (solo iba por SSE).
  Ahora `ReportEmptyError` devuelve bandeja vacía al instante y los errores
  de bandeja quedan en el log.
- **Edge fantasma**: cuando el debugger estaba caído, `create_driver`
  lanzaba un Edge oculto con `--remote-debugging-port=0` (puerto aleatorio)
  y sin las flags anti-suspensión; el reinicio no podía matarlo porque
  buscaba el PID por puerto. Ahora el attach falla con error claro y
  `restart_browser` localiza el Edge del perfil por `--user-data-dir`.
- **Vista de columnas no persistía entre navegadores**: `localStorage` es
  por perfil y el corporativo borra datos de sitio al cerrar. Nuevo
  endpoint `/api/ui-prefs`: la vista de columnas y los toggles de
  sonido/notificar se guardan en `ui_output/ui_prefs.json` del servidor y
  siguen al usuario a cualquier navegador (migra lo local automáticamente).
- **Notificación de Windows muda**: la casilla "Notificar" venía tildada
  pero el permiso del navegador solo se pedía al retildar → quedaba en
  `default` y el aviso salía en silencio. Ahora se pide en el primer gesto
  sobre la página, la casilla avisa si quedó bloqueada, y hay botón
  "Probar aviso" para verificar sin esperar un lead.
- **Toast del backend solo cubría `tomado`**: ahora también avisa cuando
  entra un lead nuevo a la bandeja (una vez por lead; los ya listados no
  repiten en cada ciclo).

## [1.4.0] — 2026-10-21

### Agregado

- **Equipo del monitor**: sección con personas auxiliares (nombre + franjas
  horarias). Con una franja del equipo vigente, el lead se toma con el usuario
  central y se **reasigna** a la persona de turno (lookup del propietario con
  verificación). Sin franja propia ni del equipo no hay turno: nada se toca.
- **Horario estricto**: los leads solo se toman dentro de una franja vigente.
  "Revisar ahora" fuera de turno corre en modo prueba: lista los leads como
  `detectado` sin abrirlos, y quedan reprocesables al asignar una franja.
- **WhatsApp automático** (opcional): leads de Argentina con preferencia
  WhatsApp reciben el primer mensaje tras el Pick Up verificado; "Otra
  información" registra `N INT Se envía WhatsApp dd/mm/YYYY HH:MM`.
- **Gestor de columnas** en la lista del monitor: ocultar, reordenar
  (arrastrando el encabezado) y redimensionar columnas; persiste en el
  navegador con "Restablecer vista". Filas compactas (~20 px), columna `⏱`
  con minutos desde la detección y número de orden descendente.
- **Click en nombre/apellido/ID** del lead abre el registro de Salesforce en
  otra pestaña.
- **Notificaciones de lead nuevo**: sonido opcional, resaltado de la fila y
  notificación del navegador (checkbox "Notificar"); el toast de Windows
  existente sigue avisando los leads tomados.
- **Auto-recuperación del navegador**: tras 3 ciclos seguidos sin conectar al
  navegador dedicado, el servidor lo reinicia solo (cooldown de 10 minutos,
  sin interferir con runs del bot). Tras el relanzado se cierra la pestaña
  `about:blank` inicial que quedaba huérfana.
- Franjas del equipo se **autoguardan** al agregar/quitar; la franja propia
  también al agregarla.

### Corregido

- `navegador_trabado` crónico: el attach WebDriver al perfil dedicado tarda
  ~37 s; el timeout de sesión subió de 15 s a 60 s.
- "Revisar ahora" ya no toma leads fuera de horario (modelo estricto).
- El autoguardado de franjas ya no agrega la franja mientras se teclea la
  hora: se agrega con "+ franja" y se persiste al instante.
- La ventana del monitor se adopta tras un reinicio en vez de duplicarse, y
  la pestaña temporal de trabajo no queda abierta.

## [1.3.0] — 2026-10-09

### Agregado

- **Monitor de Bandeja**: vista nueva que revisa las bandejas habilitadas cada
  ~1 minuto, detecta leads con el propietario "sin asignar" configurado y
  estado `Nuevo`, abre el registro y ejecuta `Pick Up` con verificación del
  propietario antes y después del clic. Nunca repite un Pick Up no confirmado.
- Bandejas por país (Argentina / Colombia / México) con URL del reporte y
  propietario "sin asignar" editables y persistidos; activación por bandeja.
- Franjas horarias `hh:mm` configurables; sin franjas el monitor corre siempre
  que esté activo.
- Notificaciones: banner + beep en la UI y toast nativo de Windows al asignar
  leads; el estado del monitor y los leads detectados llegan por SSE.
- Canal de eventos `GET /api/events` (SSE): la UI deja de releer el servidor
  cada 3 segundos; solo se actualiza cuando hay una novedad real.
- `server_guardian.py`: supervisa `ui_server.py`, lo reinicia con espera
  creciente si se cae o deja de responder, guarda `logs/server_crash_*.log`
  por caída y frena tras 5 caídas en 10 minutos con un marcador fatal.
  `INICIAR.bat` del paquete ahora lanza el guardián.

## [1.2.1] — 2026-10-07

### Corregido

- Identidad de intentos independiente del país: Python y UI comparan el ID
  completo de la columna posterior a fecha/hora en líneas INT, sin imponer
  cantidad de puntos, longitud numérica o alfabeto. Los IDs mexicanos ya
  documentados no se vuelven a escribir; no se borran duplicados históricos.
- Reconocimiento de `Sub cualificación`/`Sub cualificacion` en México tanto
  para seleccionar la opción como para verificar el valor persistido.
- Cierre bloqueado en revisión si estado o propietario no se pudieron leer;
  al reanudar una conversión pendiente se verifican también los picklists.
- Documentación: la UI bloquea colas sin intentos pendientes y no ejecuta si
  falla la sincronización. El servidor valida la copia congelada antes de
  lanzar el runner; un código 2 ya no sugiere reiniciar el navegador.
  El cierre sigue siendo independiente de los intentos pendientes.
- Puerto de depuración trabado: el servidor ahora hace una sonda real de
  sesión Selenium antes de lanzar el runner (que `/json` responda no basta).
  Si la sonda falla, reinicia el navegador dedicado **una sola vez** y
  reintenta, todo antes de tocar ningún Lead; solo si tampoco revive rechaza
  la tanda con 503.
- Pestañas duplicadas: al abrir o reiniciar el navegador dedicado se abre
  solo la pestaña que falta (app y Salesforce se detectan por host, así una
  pestaña de un Lead ya cuenta como Salesforce abierto). Las pestañas
  restauradas tras un reinicio tampoco se duplican.
- Propietario final del cierre por país: la conversión en México asigna
  `MX_LEAD_COLD` y en Colombia `CO_LEAD_COLD`; antes se exigía siempre
  `AR_LEAD_COLD` y un cierre exitoso quedaba como `conversion_no_verificada`.
- Verificación local: 283 tests, incluidos escenarios DOM y runner con datos
  sintéticos. Los pilotos reales por país quedan pendientes de autorización.
  La CLI OpenSpec continúa no disponible en esta máquina.

## [1.2.0] — 2026-10-06

### Agregado

- Selector de país/modo de campos en la vista de la cola del bot:
  **Argentina** (intentos en `Otra información`, motivo de cierre en
  `Comentario`) y **Colombia/México** (intentos en `Comentario`, motivo de
  cierre agregado al final de `Otra información` conservando el texto previo).
- Detección del país de la tanda por `TEL1` sobre **toda** la base Wolkvox
  (`91549` Argentina, `9352` México, `957` Colombia) con bandera e indicador
  visibles. Una base mezclada, con prefijos desconocidos o teléfonos vacíos
  bloquea la documentación y el cierre antes de tocar Salesforce; si el país
  detectado no coincide con el selector, la app ofrece cambiarlo.
- El modo de país viaja congelado en las colas de documentación, cierre y
  correcciones; los runners resuelven las etiquetas del campo desde ese
  valor y no pueden cambiarlo a mitad de ejecución.
- Los snapshots registran el campo físico y el modo de país, de modo que una
  lectura de `Otra información` (Argentina) nunca se aplique como evidencia de
  `Comentario` (Colombia/México) ni al revés.

### Seguridad

- Los teléfonos se usan solo localmente para detectar el país: nunca entran
  a colas, resultados, logs ni mensajes de error (los reportes muestran
  cantidades y categorías).

### Compatibilidad

- Las colas, snapshots y correcciones históricas sin `country` se interpretan
  como `argentina`, el comportamiento previo.

## [1.1.0] — 2026-10-03

### Agregado

- Cierre de Leads por lote desde la vista de cola del bot: checkbox
  "Incluir en cierre" por Lead, motivo exclusivo `Ilocalizable` o
  `Deja de interactuar`, selección masiva Todos/Ninguno y asignación de
  motivo a seleccionados. La decisión de cuándo cerrar es del auxiliar:
  no hay mínimo ni validación de cantidad de intentos.
- El bot de cierre (`run_close_queue.py`) edita Comentario, Cualificación
  y Sub-Cualificación con los literales exactos del motivo, guarda, verifica
  el estado `Cerrado` y ejecuta `Convert Lead → Yes`, confirmando el
  propietario final `AR_LEAD_COLD`. Los resultados quedan separados de los
  de documentación (`conversion_pendiente`, `conversion_no_verificada`,
  `cerrado_verificado`, `ya_cerrado`, `revision`, `conflicto`, `error`).
- Servidor local: `PUT /api/close-queue`, `GET /api/close-results` y
  `POST /run-close` con los mismos controles de token, prechequeo del
  navegador y exclusión mutua que la documentación.

### Seguridad

- La ejecución del cierre requiere confirmación explícita del lote en la
  UI; seleccionar o asignar motivos no escribe nada en Salesforce.

### Corregido

- Verificación posterior a `Convert Lead → Yes`: el bot ahora espera el
  resultado definitivo (`Cerrado + AR_LEAD_COLD`) durante el período de carga
  y la propagación del propietario, en lugar de cortar la comprobación con
  cualquier texto no vacío. También lee el nombre visible del lookup de
  propietario; Salesforce puede exponer el ID interno del usuario en `.value`.
  Esto evita falsos `conversion_no_verificada` y las recargas repetidas.

## [1.0.10] — 2026-10-03

### Corregido

- Falsos errores por lentitud de Salesforce: si la espera del editor tras
  Guardar vence, el bot ahora recarga el registro y verifica el valor
  persistido antes de declarar `error` — un guardado que completó de fondo
  ya no se reporta como fallido.
- Los motivos de error del log registran el tipo de excepción
  (`TimeoutException`, etc.) además del mensaje, que suele venir vacío.

## [1.0.9] — 2026-10-03

### Corregido

- Puerto de depuración trabado tras cada tanda: en modo adjunto
  `release_driver` no cerraba la sesión, así que cada ejecución dejaba un
  chromedriver y una pestaña huérfanos hasta que Chromium dejaba de aceptar
  sesiones nuevas. Ahora se cierra la pestaña de trabajo y la sesión:
  verificado en vivo que el navegador persistente queda abierto.

## [1.0.8] — 2026-10-02

### Agregado

- Al abrirse, el navegador dedicado deja la app como primera pestaña y
  Salesforce al lado (antes era al revés), tanto en
  "Reiniciar navegador del bot" como en `open_persistent_browser.py`.
- La app indica el requisito de estar logueado en Salesforce: en la
  pantalla de inicio y en la vista de cola del bot.

## [1.0.7] — 2026-10-02

### Corregido

- Sesión vencida explícita: al reiniciarse el servidor el token de la
  pestaña queda viejo y antes solo se veía "token inválido o ausente".
  Ahora cualquier 403 marca la sesión y la app indica
  "El servidor del bot se reinició: recargá la página (F5)", en "Ejecutar
  bot", "Reiniciar navegador del bot" y el indicador de sincronización.

## [1.0.6] — 2026-10-02

### Agregado

- Verificación previa en `POST /run`: si el navegador dedicado está cerrado
  el bot no arranca y la UI muestra cómo reabrirlo; si el puerto de
  depuración acepta TCP pero no responde HTTP (`/json/version`, señal de
  puerto trabado) indica usar "Reiniciar navegador del bot". Ya no se puede
  lanzar una tanda condenada a fallar.

## [1.0.5] — 2026-10-02

### Corregido

- La protección de `v1.0.4` usaba `client_config`, que el constructor público
  de `webdriver.Edge` no acepta: el bot fallaba con `TypeError` en cada
  ejecución adjunta. Se reemplazó por un watchdog con hilo que abandona la
  creación de sesión a los 15 s y libera el driver huérfano.

## [1.0.4] — 2026-10-02

### Corregido

- Si el puerto de depuración del navegador dedicado queda trabado (responde
  `/json` pero no crea sesiones WebDriver), el bot ahora falla en **15 s** con
  un mensaje claro en vez de colgar ~120 s sin abrir pestañas.
- La UI avisa cuando el bot termina con `exit_code != 0` ("reiniciá el
  navegador del bot") en lugar de quedar en silencio.

### Detalle técnico

- `create_driver` crea la sesión adjunta en un hilo con límite de 15 s
  (mecanismo corregido en v1.0.5).

## [1.0.3] — 2026-10-02

### Corregido

- Vista de cola: el panel "Texto actual en Salesforce" se contraía solo a los
  ~3 segundos porque el polling reconstruye la lista. El estado abierto se
  persiste por Lead y **los Leads recién guardados abren solos** el texto
  confirmado para verificación.
- Lista principal: el panel editable del snapshot también conserva su estado
  abierto entre re-renders.

## [1.0.2] — 2026-10-02

### Corregido

- Lista principal: un Lead pendiente con snapshot viejo ya no muestra el texto
  histórico del campo como si fuera el texto a documentar — y lo que es peor,
  "Copiar texto" ya no copia contenido viejo. Ahora la tarjeta muestra el
  texto a documentar (solo intentos pendientes) con rótulo explícito.
- El texto a documentar se numera desde el último `N INT` de la lectura local
  del campo (si existe), no desde el offset global: un Lead con 3 INT
  guardados muestra el pendiente como `4 INT`.
- Rótulos sobre el cuadro de texto: "Texto a documentar" (pendiente) vs
  "Documentado en Salesforce — última lectura local" (hecho).

## [1.0.1] — 2026-10-02

### Corregido

- Vista de cola: el snapshot histórico de `Otra información` ya no se muestra
  suelto debajo del Lead (parecía texto recién documentado). Ahora va
  colapsado en un `details` rotulado "Texto actual en Salesforce (lectura
  anterior…)", con fecha/hora de la lectura.
- La tarjeta muestra primero el bloque **"A documentar (intento nuevo)"** con
  resultado, fecha, hora y `call_id` de cada intento pendiente.
- En la lista principal, el detalle del snapshot indica la fecha de lectura en
  lugar del ambiguo "confirmada por bot".

## [1.0.0] — 2026-10-01

Primera versión etiquetada. Corrige el incidente de "falsos documentados"
detectado el 2026-10-01.

### Corregido

- Un Lead ya no se marca como documentado por un resultado o snapshot
  histórico que solo coincide por `lead_id`: el estado ahora es por
  Lead + `call_id` concretos.
- Resultados/snapshots legados (sin `run_id` ni `call_ids`) se muestran como
  `histórico` y no confirman intentos nuevos.
- La marca manual registra el conjunto de intentos visto al marcar
  (`manualDoneScope`): un intento nuevo del mismo CSV no hereda el check.
- La cola activa solo exporta intentos pendientes; `pollBotResults` no la
  reescribe mientras el bot corre.
- El bot es idempotente: antes de escribir en `Otra información` lee el campo,
  deduce los `call_id` presentes y agrega solo los faltantes. Estados nuevos:
  `ya_documentado` (sin escritura) y `revision` (intento no verificable).

### Agregado

- `attempt_identity.py`: extracción de `call_id` y partición de intentos.
- `run_id` estable por ejecución: el servidor congela la cola en
  `run_<run_id>.json` bajo lock; resultados, snapshots y métricas quedan
  enlazados a ese run.
- Snapshots con `run_id`, `call_ids`, `content_hash` y `read_at`.
- Botón "Reiniciar navegador del bot" (`POST /api/restart-browser`).
- Badge de versión en el pie + aviso si el servidor tiene versión distinta.
- 21 tests nuevos (identidad, cola, snapshots, servidor, UI en Node `vm`).

### Compatibilidad

- El formato de cola/resultados/snapshots gana campos nuevos pero acepta los
  archivos anteriores (se tratan como históricos).

## Historial previo (versiones retroactivas `0.x`)

Las fases de desarrollo previas a la primera versión estable fueron etiquetadas
retroactivamente sobre sus commits originales, para mantener la trazabilidad.
`git checkout v0.x.y` reconstruye cada estado histórico.

### [0.4.0] — commit `9a3d1e7`

Documentación automática con guardado verificado y cola viva en la UI
(bot en modo `--auto`, verificación post-guardado, polling en vivo).

### [0.3.1] — commit `35a451f`

Aviso de columnas omitidas del CSV y alto de fila ajustable en la UI.

### [0.3.0] — commit `1fdf366`

UI local para leads `AR_LEAD_QUALIF`: selección de cola, snapshot y progreso.

### [0.2.0] — commit `e0850e1`

Automatización local asistida de Salesforce (Selenium + Edge dedicado,
modo supervisado sin guardar).

### [0.1.0] — commit `7119405`

Aplicación inicial de campañas predictivas: carga del CSV, normalización,
generación de archivos Wolkvox y documentación manual de intentos.
