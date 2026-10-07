# Historial de versiones

La versión vigente es la constante `APP_VERSION` de `documentador_predictivo.html`
(única fuente). `ui_server.py` la expone en `GET /status` como `version`.

Esquema: [SemVer](https://semver.org/lang/es/) — `MAYOR.MENOR.PARCHE`.

- **MAYOR**: cambios que rompen compatibilidad (formato de cola, resultados, snapshots).
- **MENOR**: funcionalidad nueva compatible.
- **PARCHE**: correcciones de defectos.

Cada versión liberada lleva un tag de Git `v<versión>`.

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
- Verificación local: 281 tests, incluidos escenarios DOM y runner con datos
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
