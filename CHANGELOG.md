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

## [1.6.1] — 2026-11-23

> Primer paquete con la corrección de Edge/EdgeDriver 158. El zip `v1.6.0` que
> circuló el 21/11 se armó antes del fix y queda sustituido por éste.

### Agregado

- **Recogida de QUALIF fuera de horario (apertura)**: sección nueva en la
  vista Monitor. La persona elige bandeja y rango manual `Desde`/`Hasta`,
  ve la vista previa de candidatos (Lead ID, nombre, fecha de creación,
  clasificación y motivo de exclusión) y confirma la toma a nombre del
  usuario logueado — sin reasignación de equipo ni WhatsApp. Solo entran
  leads `no_habil_elegible` (creados cuando ninguna franja cubría la
  bandeja); los de turno personal y los de fecha ilegible quedan fuera o
  en revisión. La vista previa es de solo lectura. Lotes persistidos en
  `ui_output/apertura/` con estados por lead y reconciliación al arranque.
  Endpoints: `POST /api/apertura/preview`, `POST /api/apertura/confirm`,
  `GET /api/apertura/disponibles`, `POST /api/apertura/mezclar`.
  Tests-regla: `tests.test_apertura.*`, `tests.test_apertura_store.*`,
  `tests.test_ui_server.AperturaApiTests.*`.
- **QUALIF de apertura en "Distribuir leads"**: botón "Agregar QUALIF de
  apertura" lista los tomados confirmados no consumidos, se tildan y se
  suman a la vista previa por Lead ID (chip "apertura" + bandeja).
  Duplicado con el archivo → una sola fila con el destino del archivo.
  La corrida real marca `consumido` por `run_id` solo en `reasignado` /
  `ya_asignado`; la simulación y los errores no consumen.
  Tests-regla: `tests.test_distribucion_loader.MezclarAperturaTests.*`,
  `tests.test_run_distribucion_queue.ConsumirAperturaTests.*`.
- **Toasts de Windows con bandera y bandeja**: cada línea del aviso del
  monitor lleva prefijo `🇦🇷 AR` / `🇨🇴 CO` / `🇲🇽 MX` (el toast no
  admite color de texto, la bandera es el indicador) — tomado, error, no
  verificado, tomado por otra persona y detectado. Test-regla:
  `tests.test_ui_server.MonitorTickTests.test_toast_lines_identifican_bandeja_en_cada_estado`.
- **Ventana de gracia post-cierre de franja**: si una franja que cubre una
  bandeja habilitada terminó hace menos de un intervalo de monitor, el
  ciclo sigue corriendo para recuperar leads que entraron justo antes del
  corte (ej. lead 09:59 con franja hasta 10:00, recuperado en el ciclo de
  10:02). Vence la gracia → pausa normal. Tests-regla:
  `tests.test_ui_server.UiServerMonitorTests.test_gracia_*`,
  `tests.test_lead_monitor.*test_lead_ingresado_antes_del_cierre_*`.
- **Laboratorio WhatsApp** (botón "Laboratorio" en la home): área de pruebas
  para comparar Selenium con `agent-browser` sobre el mismo flujo de envío.
  - Importa una BD (.xlsx/.csv) con el mismo parser de "Distribuir Leads" o
    reutiliza la base ya cargada allí; mapeo por columnas con detección de
    aliases, vista previa y selección por lead (atajo "3 primeros").
  - Modo **Verificación (prueba)**: recorre los leads seleccionados, lee país,
    preferencia y `Otra información`, y reporta apto/no elegible/bloqueado
    **sin escribir ni pulsar nada** en Salesforce.
  - Modo **Ejecución real** (confirmación explícita): agrega
    `N INT Se envía WhatsApp DD/MM/AAAA HH:mm` al final de `Otra información`
    (numeración consecutiva sobre el historial, igual que el Monitor),
    verifica la persistencia tras recargar y solo entonces pulsa
    Send To Whatsapp. Sin toast de confirmación el lead queda
    `documentado_wa_no_confirmado` y **jamás se reenvía automáticamente**
    (journal SQLite en `ui_output/laboratorio.sqlite3`: un clic reservado sin
    cierre terminal queda `indeterminado` y bloquea el lead).
  - Motores: `selenium` (referencia), `agent_browser` (CLI 0.43.0 por CDP
    contra el mismo Edge del bot) y `comparacion` (ambos motores sobre los
    mismos leads, solo en modo prueba). La comparación real debe hacerse con
    grupos de leads distintos para no enviar dos WhatsApp.
  - Cola congelada por run (`queues/laboratorio_<run>.json`), resultados
    JSONL por motor, métricas agregadas en
    `cola_laboratorio_activa.metricas.json` y reanudación que omite los leads
    ya terminal/ambigüos. Endpoints: `/api/laboratorio-queue`,
    `/run-laboratorio`, `/api/laboratorio/results|status|engines|control`.
  - Setup: `agent-browser` requiere Node ≥22
    (`npm i -g --allow-scripts=agent-browser agent-browser@0.43.0`);
    sin la CLI el laboratorio corre solo con Selenium.
  - Tests: `test_laboratory_contracts`, `test_laboratory_store`,
    `test_run_laboratory_queue`, `test_agent_browser`,
    `test_laboratory_metrics` (reglas permanentes del laboratorio).

### Corregido

- **La documentación de envíos moría por `StaleElementReferenceException`
  tras el auto-update a Edge 158**: la edición en línea de Salesforce
  ubicaba el lápiz/editor/Guardar como WebElement y los usaba en la
  llamada siguiente; con Edge/EdgeDriver 158 esos handles mueren entre
  evaluaciones (persistente, incluso 150 s post-refresh — verificado in
  situ). Ahora lápiz, escritura del editor, lectura de verificación y
  Guardar se resuelven y actúan dentro de la misma evaluación JS
  (`*_ATOMIC_SCRIPT`), igual que el botón Send To Whatsapp. La edición de
  Comentario del cierre usa el mismo camino atómico. Además los helpers
  `execute_in_any_frame` / `field_result_in_any_frame` toleran un frame o
  documento que muera al serializar, en vez de abortar la toma o el scan
  de bandeja. Tests-regla:
  `tests.test_comment_writer.AtomicEditorTests.*`,
  `tests.test_comment_reader.FrameToleranceTests.*`.
- **El cierre de Leads moría por `StaleElementReferenceException` en Edge
  158 y encadenaba revisiones falsas**: tres causas, tres correcciones.
  (a) El picklist de Cualificación/Sub-Cualificación devolvía el
  disparador como WebElement y lo usaba en la evaluación siguiente —
  ahora se ubica, revisa `aria-expanded` y clickea dentro de la misma
  evaluación (`CLICK_PICKLIST_TRIGGER_ATOMIC_SCRIPT`), y todos los
  scripts del picklist corren por `execute_in_any_frame` (ningún handle
  cruza evaluaciones ni frames). (b) `read_closure_state` leía una sola
  vez apenas listo el shell de Lightning: la ficha llega después como
  pestaña "Cargando…" y los Leads siguientes a un fallo salían
  `revision` con Estado/Propietario vacíos — ahora
  `wait_closure_state` sondea hasta que ambos campos rendericen
  (acotado por el timeout). (c) Una edición que quedó abierta tras un
  fallo activaba el guard de cambios sin guardar —
  `discard_open_edit_form` la cancela (best-effort) antes de registrar
  el error. Tests-regla:
  `tests.test_lead_closure.PicklistFrameTests/PicklistRetryTests/
  DiscardEditFormTests`, `tests.test_run_close_queue.WaitClosureStateTests`,
  `test_state_arriving_after_first_read_still_closes`,
  `test_edit_failure_discards_the_open_form`.
- **La etiqueta del lápiz ("Modificar <label>") podía persistirse dentro
  del campo al documentar o cerrar**: el strip que el Monitor aplicaba a
  la marca de toma vivía solo en `lead_monitor`. Se mudó a
  `comment_reader.strip_edit_button_label` y ahora lo aplican
  `find_field_value` y `find_field_text` — toda lectura de campo sale
  limpia, así el texto compuesto para Documentar/Cerrar no re-escribe la
  etiqueta. Test-regla:
  `tests.test_comment_reader.EditButtonLabelStripTests.*`.
- **La clasificación corría la fecha de creación con el `tz_offset` de
  documentación**: ese campo nació (v1.4.0) solo para escribir la línea
  de intentos WhatsApp en la hora del país del lead; el reporte ya muestra
  la hora del visor (= la PC). Con AR=+2, leads creados 07:08–07:55 dentro
  de la franja 06:00–08:59 quedaban en 05:08–05:55 → `sin_cobertura` sin
  tomarse. Ahora la clasificación usa la fecha del reporte tal cual;
  `tz_offset` sigue aplicando solo a la línea de intentos. Test-regla:
  `tests.test_apertura.ClassifyLeadTests.test_tz_offset_de_documentacion_no_corre_el_reporte`.
- **La vista previa de apertura solo leía el viewport del reporte**: la
  grilla de Lightning renderiza ~35 filas — una bandeja con 139 pendientes
  listaba solo la primera página. Dos causas: la preview usaba la lectura
  horizontal acotada (ahora `read_bandeja_leads(full=True)` →
  `read_full_report`, el ciclo del monitor conserva la lectura rápida) y
  el script de scroll vertical se rendía en el primer wrapper con
  `scrollHeight > clientHeight` aunque su rango estuviera agotado
  (`data-grid-table-ctr`, 17px) sin llegar al viewport real (`widgets`) —
  ahora sigue subiendo si el contenedor no se movió. Test-regla:
  `tests.test_ui_server.AperturaApiTests.test_preview_pide_barrido_completo_del_reporte`.
- **Un lead sin franja que lo cubra se tomaba igual por el fallback a la
  hora del ciclo**: si la Fecha de creación caía fuera de toda franja
  configurada (u era de otro día o ilegible), el monitor la evaluaba a la
  hora actual — y si el ciclo corría dentro de una franja, tomaba el
  lead. Ahora la clasificación es por lead: `turno_personal` se toma,
  `no_habil`/`fuera_de_rango` queda `detectado` con motivo
  `sin_cobertura` (lo recoge la apertura manual), y fecha ilegible queda
  `detectado` con motivo `revision` — nunca se toma. Las franjas son
  día-agnósticas (`HH:MM` vale cualquier fecha) y `tz_offset` convierte
  la hora del reporte a la de la PC. Tests-regla:
  `tests.test_lead_monitor.*test_lead_sin_cobertura*`,
  `...test_fecha_ilegible*` y los reescritos de fecha vieja en
  `tests.test_lead_monitor`.
- **La cobertura de la toma se evaluaba a la hora del ciclo, no a la de
  ingreso del lead**: un lead creado 10:58 en franja de 9:00–10:59 y
  revisado 11:01 quedaba "sin cobertura"; y uno creado antes de la franja
  se tomaba igual si el ciclo corría en franja (leads QUALIF de antes de
  las 12:00 tomados al abrir el turno de las 12:00). Ahora `covered` se
  evalúa lead por lead con su Fecha de creación (misma semántica de
  franja propia/equipo/por-bandeja; si la fecha no es usable, cae a la
  hora del ciclo como antes). Tests-regla:
  `tests.test_lead_monitor.*test_lead_ingresado_*`.
- **`column_offset` anclaba la grilla con el owner de AR en todas las
  bandejas**: en reportes CO/MX la columna de propietario se desalineaba
  porque el valor centinela (`CO_LEAD_QUALIF`, `MX_LEAD_QUALIF`) no
  coincidía con `AR_LEAD_QUALIF`. Ahora recibe el `unassigned_owner` de
  la bandeja en curso. Test-regla:
  `tests.test_report_reader.*.test_column_offset_aligns_values_using_bandeja_owner`.
- **"Distribuir leads" declaraba `propietario_ilegible` a leads cuyo
  propietario sí era visible**: el campo "Propietario del candidato" a veces
  renderiza después de la primera lectura (lote del 17/11: ~133 de ~380
  resultados marcados inaccesibles, varios con el propietario a la vista).
  Tanto la corrida real como la simulación ahora reintentan una vez con
  refresh + relectura —el mismo rescate que el post-pickup— antes de
  rendirse. Si el campo sigue sin aparecer, el `detalle` del resultado ya
  no dice solo `propietario_ilegible`: lleva evidencia de la página
  (`titulo`, cola de la `url` y si existe alguna etiqueta de propietario
  —"propietario", "lead owner", "responsable"—) más screenshot en
  `capturas/`, que distingue un registro sin permiso de un campo con otra
  etiqueta o de un render lento. Tests-regla:
  `tests.test_run_distribucion_queue.*.test_unreadable_owner_retries_with_refresh_reread`,
  `...test_unreadable_owner_reports_page_diagnostic`.
- **"Nombre no encontrado" volcaba opciones de otro contenedor de la
  página**: cuando el modal "Cambiar propietario" se cerraba antes del
  volcado de diagnóstico, el dump leía contenedores ajenos (casos con
  `input: ''` y opciones como "notas y archivos adjuntos" o "actividades
  abiertas" del lote del 17/11). Ahora el volcado solo corre si el modal
  sigue abierto; si se cerró, el detalle dice
  "el diálogo se cerró antes de leer el desplegable". Tests-regla:
  `tests.test_lead_monitor.PickOwnerOptionTests.test_dump_skipped_when_dialog_closed`,
  `tests.test_run_distribucion_queue.SimulateOneLeadTests.test_lookup_diag_reports_closed_dialog`.

## [1.5.1] — 2026-11-10

### Corregido

- **La bandeja AR volvía "0 sin asignar" con QUALIF a la vista**: la grilla
  de reportes de Lightning solo renderiza las columnas del viewport — con
  `Propietario` a la izquierda y el enlace/`Lead ID` a la derecha de la
  columna ancha `Campaña`, la fila QUALIF se descartaba sin rastro (el caso
  de la PC de Roger, y reproducible en notebooks de 13"). El Monitor ahora
  barre el reporte horizontalmente (hasta 20 pasadas, sin scroll vertical)
  y une los fragmentos de cada fila por su identidad estructural — clave
  `data-row-*`/`aria-rowindex` estable, jamás por nombre ni datos
  personales — fallando cerrado ante claves ausentes, duplicadas u orden
  cambiante. El escaneo reporta `horizontal_passes`, `viewport_width`,
  `owner_without_id` y `unstable_or_ambiguous_rows`, y el log distingue
  bandeja vacía de `N QUALIF sin ID`. La ventana dedicada además usa hasta
  1600 px cuando el escritorio lo permite (fallback 1150×760). Tests-regla:
  `tests.test_report_reader.ReportReaderTests.test_horizontal_reader_merges_fragments_and_restores_scroll`,
  `...test_horizontal_reader_counts_qualif_without_id`,
  `tests.test_lead_monitor.ReadBandejaLeadsTests`.
- **Lead tomado que quedaba en "Nuevo" cuando el panel no renderizaba**:
  ~17% de las tomas terminaban `sin_panel` — el panel "Contact Client" no
  montaba por error transitorio de Salesforce (o un formulario de edición
  colgado tapándolo) y su Save, que pasa el estado a "En curso", nunca se
  ejecutaba. Tras las ventanas de espera el Monitor ahora aguarda ≤3 s,
  **recarga la ficha** y reintenta la búsqueda/Guardado del panel
  (`finalizacion: panel_tras_reload`), re-verificando la marca de `Otra
  información` porque el reload descarta ediciones inline abiertas.
  Tests-regla:
  `tests.test_lead_monitor.FinalizePickUpTests.test_missing_panel_reloads_page_and_retries`,
  `...test_reload_retry_reverifies_the_attempt_mark`.
- **"Asignado" inyectado por Salesforce ya no queda en el lead**: el Save
  del panel "Contact Client" (o un flow) puede escribir `Asignado` en
  `Otra información` de forma asíncrona — ante Compliance cuenta como
  lead ya gestionado, cuando solo lo tomó el bot. Tras el guardado del
  panel, toda toma sin comentario propio (llamada, sin método o
  reasignación) corre una limpieza que quita la línea `Asignado` dejando
  el resto del contenido intacto; el resultado muestra `asignado_quitado`
  cuando hubo que limpiar. Tests-regla:
  `tests.test_lead_monitor.FinalizePickUpTests.test_injected_asignado_is_cleaned_for_own_take`,
  `...test_injected_asignado_removed_preserving_notes`.
- **Una persona por bandeja y horario**: la franja del usuario logueado
  ya no puede pisar la de un auxiliar en la misma bandeja — los PUT de
  `schedule` y `equipo` responden 400 y la UI avisa en vivo y con pop-up
  al agregar la franja. Además el minuto límite compartido ahora cuenta
  como solape (…–12:00 + 12:00–… pisa el minuto 12:00, igual que la
  evaluación inclusiva del turno): contiguas de verdad es 11:59/12:00.
  Tests-regla:
  `tests.test_monitor_store.SolapePropioEquipoTests`,
  `tests.test_ui_server.UiServerMonitorTests.test_franja_no_puede_solapar_al_otro_editor`.
- **Toma de leads sin comentario de asignación**: el Monitor ya no escribe
  `Asignado` cuando el lead queda con el usuario del bot. Tanto la toma
  propia como la reasignación y la distribución por archivo guardan Contact
  Client sin modificar `Otra información`. Se elimina el generador sin uso
  de `Asignado - <método>`. La documentación del envío real de WhatsApp
  continúa separada de la toma. Tests-regla:
  `tests.test_lead_monitor.FinalizePickUpTests.test_toma_simple_o_reasignada_no_escribe_comentarios`
  y `tests.test_run_distribucion_queue.DistributeOneLeadTests.test_pickup_y_reasignacion_no_escriben_comentarios`.

## [1.5.0] — 2026-11-04

### Corregido

- **Reinicio del navegador espera a que el Edge viejo muera**: tras el
  taskkill, el relanzamiento ahora aguarda a que desaparezcan los procesos
  del perfil dedicado (antes solo esperaba a que el puerto soltara). Sin la
  espera, el nuevo arranque se delegaba al Edge que aún se estaba cerrando
  y el puerto de depuración nunca abría — el loop de navegador_trabado que
  se veía tras los reinicios programados (RAM).
  Test-regla: `tests.test_ui_server.MonitorTickTests.test_restart_browser_waits_for_profile_processes_to_die`.

### Agregado

- **Distribuir leads — modo prueba**: casilla "Modo prueba" en la vista
  previa (banner violeta, mismo estilo que el Monitor de Bandeja). Con la
  casilla activa el botón pasa a "Probar (sin guardar)": el runner abre cada
  lead, lee el propietario real y, para los que se reasignarían, verifica en
  el modal "Cambiar propietario" que el nombre del auxiliar existe como
  usuario — siempre cancela, nunca pulsa Pick Up ni confirma. Resultados
  `prueba_*` en la tabla con banner "Simulación — nada se guardó".
  Cambio OpenSpec `distribuir-leads-modo-prueba`.

### Cambiado

- **Lookup "Cambiar propietario" — diagnóstico y foco**: `_pick_owner_option`
  hace click en el input antes de tipear (los combobox de Lightning pueden
  ignorar `send_keys` sin foco) y, cuando la opción no aparece, la
  simulación guarda en `detalle` lo que el desplegable mostraba (texto
  tipeado + opciones vistas) — el dato que explica un "nombre no
  encontrado". Herramienta nueva `debug_owner_lookup.py` para inspeccionar
  el lookup en vivo. Tests-regla:
  `tests.test_lead_monitor.PickOwnerOptionTests`,
  `tests.test_run_distribucion_queue.SimulateOneLeadTests.test_nombre_no_encontrado_detail_shows_what_lookup_saw`.
- **Distribuir leads — columna Lead persistente**: la cola y el resultado
  guardan el `nombre` del lead (local, en `queues/`); la tabla de
  Resultados lo muestra como link a Salesforce igual que la vista previa.
  Al entrar a la vista se cargan solos los últimos resultados — tras un
  F5 queda todo como estaba. Test-regla:
  `tests.test_run_distribucion_queue.DistributeOneLeadTests.test_entry_carries_lead_nombre`.
- **Distribuir leads — Detalle y semáforo en Resultados**: el Detalle de los
  reasignados muestra `propietario anterior → persona destino` (antes decía
  solo "propietario: X" y parecía el dueño final). La celda Resultado se
  pinta: verde (reasignado / ya asignado), ámbar (cola excluida) y rojo
  (errores y "nombre no encontrado").
- **Distribuir leads — colas ya gestionadas (MX/CO)**: `SKIP_OWNERS` suma
  `MX_LEAD_COLD`, `MX_LEAD_EXPORT_GETLEAD`, `CO_LEAD_COLD` y
  `CO_LEAD_EXPORT_GETLEAD`: un lead ya derivado al canal frío/export de
  cualquier país (lista vieja) no se toca — solo se lista, con la celda
  "cola excluida" resaltada en ámbar. Tests-regla:
  `tests.test_run_distribucion_queue.DistributeOneLeadTests.test_other_country_managed_queues_are_never_touched`,
  `...SimulateOneLeadTests.test_other_country_managed_queues_are_listed_only`.

### Corregido

- **Distribuir leads — resultados mezclados entre corridas**: el archivo de
  resultados acumulaba corridas; tras una simulación, la corrida real
  mostraba estados viejos. Ahora cada corrida arranca con el resultado
  limpio. Test-regla:
  .


- **Reasignación por hora de ingreso (completa)**: el fix de 1.4.3 no
  alcanzaba porque, con la franja propia vigente al momento de la toma, el
  ciclo descartaba al equipo antes de mirar la hora de ingreso — un lead
  de las 13:59 (turno de Andres) tomado a las 14:01 quedaba con el usuario
  logueado. Ahora el destino se decide lead por lead con su Fecha de
  creación (solo si es de hoy); la toma sigue exigiendo cobertura vigente.
  Además el minuto final de la franja es inclusivo ("12:00–13:59" cubre
  13:59). Test-regla:
  `tests.test_lead_monitor.RunBandejaCycleTests.test_lead_ingresado_en_turno_del_equipo_se_reasigna`.

## [1.4.3] — 2026-10-30

### Corregido

- **INICIAR.bat en PCs nuevas**: espera al servidor hasta 60 s (antes 15 s;
  el primer arranque con antivirus escaneando el Python portable superaba
  el límite).
- **verificar_pc sin falso fallo de pip**: con Selenium ya importable
  (Python portable del paquete, sin pip) no se exige pip. Test-regla:
  `tests.test_verificar_pc.PipSeleniumTests.test_no_exige_pip_si_selenium_importa`.
- **Reasignación por hora de ingreso**: la encargada del lead se elige por
  la Fecha de creación del reporte (hora de entrada a la cola), no por la
  hora en que el bot lo toma — un lead ingresado minutos antes del cambio
  de turno ya no cae en la franja siguiente por la demora de toma.
  Test-regla: `tests.test_lead_monitor.ReassignOwnerTests.test_encargada_para_lead_usa_hora_de_ingreso`.
- **Marca del header**: "LBS REC" pasa a "GBS REC". Test-regla:
  `tests.test_ui_monitor.UiMonitorViewTests.test_header_brand_shows_gbs_rec`.
- **Modo prueba del monitor resaltado**: con la casilla tildada, la tarjeta
  de estado se tiñe de violeta, aparece el chip "⚠ MODO PRUEBA", un banner
  bajo la tarjeta aclara que no se toma ningún lead y la casilla con su
  sección "Comportamiento" quedan resaltadas. Test-regla:
  `tests.test_ui_monitor.UiMonitorViewTests.test_dry_run_indicator_is_present_in_markup`.
- **Chip "MODO PRUEBA" quitado**: redundante con la tarjeta violeta y el
  banner; además su `display:inline-flex` pisaba la clase `hidden`.
- **Tarjeta de estado congelada en "En espera"**: el servidor escribía
  `paused_reason` pero no lo empujaba por SSE (la pausa no genera
  `cycle_start/end`), así que la vista mostraba un motivo viejo mientras el
  monitor ya tomaba leads. Ahora el tick emite `monitor_state` con
  `paused_reason` y `last_cycle_at` tanto al pausar como al cerrar el ciclo,
  y la UI los aplica al estado en vivo. Test-regla:
  `tests.test_ui_server.MonitorTickTests.test_tick_pause_broadcasts_reason_to_sse`.
- **Casilla "Notificar" que "saltaba"**: `toggleNotify` no releía el estado
  y el evento SSE `monitor_state` no mapeaba `notificar`, así que tras el
  broadcast la casilla volvía al valor viejo (parecía doble clic y podía
  dejar los avisos de Windows apagados sin saberse). Ahora el toggle recarga
  el estado y el SSE actualiza el flag. Además, si el toast nativo falla
  queda registrado en el log del servidor en vez de fallar en silencio.

### Cambiado

- **Revisión visual de Inicio y Monitor**: encabezado con el degradado
  azul-violeta original; tarjetas claras que se vuelven azules con texto e
  iconos blancos en hover y foco de teclado, sin desplazamiento. El monitor
  conserva sus colores originales y opciones más legibles. Solo CSS;
  sin shadcn ni nuevas dependencias.

### Agregado

- **Armado reproducible del paquete**: `packaging/` versiona INICIAR.bat,
  LEEME.txt, RECOGER_DIAGNOSTICO.bat y VERIFICAR_PC.bat;
  `packaging/build_zip.py` arma `dist/DocumentadorPredictivo_v<versión>.zip`
  desde la fuente y lo valida.
- **Paquete con verificación de PC**: `VERIFICAR_PC.bat` corre
  `verificar_pc.py` con el Python del paquete (políticas de Edge, depuración
  remota, adjunte de Selenium, acceso a Salesforce) y deja
  `reporte_verificacion_pc.txt`. `RECOGER_DIAGNOSTICO.bat` suma
  `navegador.log`, `guardian.log` y ese reporte al `diagnostico_bot.zip`.
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
