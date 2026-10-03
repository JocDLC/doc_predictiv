# Historial de versiones

La versión vigente es la constante `APP_VERSION` de `documentador_predictivo.html`
(única fuente). `ui_server.py` la expone en `GET /status` como `version`.

Esquema: [SemVer](https://semver.org/lang/es/) — `MAYOR.MENOR.PARCHE`.

- **MAYOR**: cambios que rompen compatibilidad (formato de cola, resultados, snapshots).
- **MENOR**: funcionalidad nueva compatible.
- **PARCHE**: correcciones de defectos.

Cada versión liberada lleva un tag de Git `v<versión>`.

## [1.0.4] — 2026-10-02

### Corregido

- Si el puerto de depuración del navegador dedicado queda trabado (responde
  `/json` pero no crea sesiones WebDriver), el bot ahora falla en **15 s** con
  un mensaje claro en vez de colgar ~120 s sin abrir pestañas.
- La UI avisa cuando el bot termina con `exit_code != 0` ("reiniciá el
  navegador del bot") en lugar de quedar en silencio.

### Detalle técnico

- `create_driver` usa `ClientConfig(timeout=15)` solo para crear la sesión
  adjunta y restaura 120 s para los comandos Lightning.

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
