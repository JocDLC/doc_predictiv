# Memoria del proyecto

## Non-goals

- No reemplazar el agente nativo de cada IDE (Cascade, Claude, Codex, etc.). El arnés es agnóstico.
- No crear un instalador `.exe`/`.pkg` propietario. Usamos GitHub Template + scripts.
- No agregar dependencias complejas que no sean esenciales.

## Decisiones arquitectónicas

- **GitHub Template + scripts** como mecanismo de distribución multi-PC.
- **AGENTS.md** como fuente de verdad universal; configs específicas por IDE son derivadas.
- **OpenSpec** para Spec-Driven Development.
- **SDD + TDD por clasificación (Fase 0.5, 2026-10-30)**: cada cambio se
  clasifica con la checklist de `AGENTS.md`; los cambios chicos van por la vía
  TDD (`harness.py tdd-red`/`tdd-green`, skill `tdd`) sin artefactos OpenSpec,
  con trazabilidad en `CHANGELOG.md` `[Sin publicar]` + Gantt.
- **`.devin/skills/tdd` es la fuente** del skill TDD: las copias en
  `.windsurf/skills/tdd/` y `.codex/skills/tdd/` son idénticas y se
  regeneran desde ahí (cambiar la fuente, no las copias).
- **tdd-guard/Probity descartado por ahora** como enforcement externo: requiere
  Node 22, pytest y un modelo Claude con costo, y no cubre Windsurf. Alternativa
  futura si la verificación de `harness.py` no alcanza.
- **Graphify** para context engineering y reducción de tokens.
- **Loop Engineering** integrado en el workflow de 7 fases.

## Failure patterns

- `C:` sin espacio bloquea instalaciones de extensiones y `npm global`.
- Instalar `@latest` sin fijar versiones rompe reproducibilidad.
- Modificar `AGENTS.md` sin actualizar configs por IDE genera inconsistencias.
- No correr `graphify update` deja contexto obsoleto.

## Estado actual

- **PENDIENTE (recordar siempre)**: retomar lo antes posible —
  (a) Fase 2: app nativa con pywebview/WebView2 (elimina servidor HTTP,
  token y puerto por diseño; ver decisión en "Estabilidad del servidor");
  (b) `navegador_trabado` residual: una pestaña del usuario cargando sin
  commit también cuelga NEW_SESSION — si vuelve a pasar, evaluar reload
  del target por CDP o aislar la ventana del monitor en un Edge aparte.
- **Repo vs dist (2026-10-27)**: el `INICIAR.bat` de
  `dist\DocumentadorPredictivo` corre su propia copia de la app
  (`dist\...\app\documentador_predictivo.html` + `app\automation_salesforce\`).
  `dist/` está en `.gitignore` y no hay script que lo regenere. Para probar un
  cambio del repo en la app que corre, copiar los archivos tocados al `dist`
  (con F5 alcanza si solo cambia el HTML; el `no-store` hace que se relea en
  cada pedido).
- **Intervalo del monitor (2026-10-27)**: `MONITOR_INTERVAL_SECONDS = 120` en
  `automation_salesforce/ui_server.py`. La UI NO lo lee por API: el texto
  "~2 minutos" está fijo en `documentador_predictivo.html` (tarjeta de estado y
  texto explicativo del Monitor). Si se cambia el intervalo, actualizar esos
  textos a mano (cambio `mejorar-ui-estado-monitor`).
- **PENDIENTE — renombre y rediseño (pedido 2026-10-26)**: el proyecto pasa
  a llamarse **"Automatización Gestión de Leads"** (sin mencionar IA hasta
  definir dónde va). Etapa 1 (cambio `renombrar-ui-gestion-leads`): solo
  textos de la UI + visual "moderno claro" liviana (sin carga de CPU).
  Después, cuando todo funcione y esté documentado:
  (a) renombre completo: `documentador_predictivo.html`,
  `dist/DocumentadorPredictivo`, ZIP, `INICIAR.bat`, `verificar_pc.py`,
  `open_persistent_browser.py`, `entregables/generar_docs.py`;
  (b) migrar la UI a un layout con **sidebar**.
- Plantilla base funcional.
- `graphify` instalado; `openspec` disponible vía `npx @fission-ai/openspec@1.6.0`
  (Node portátil en `~/Downloads/_dev/tools/node-v24.21.0-win-x64/`).
- `C:` tiene ~24 GB libres.
- Cambio `tomar-leads-automatico` (Monitor de Bandeja) implementado: ciclo en
  `lead_monitor.py`, estado en `monitor_store.py` (`ui_output/monitor_state.json`),
  endpoints `/api/monitor*` + SSE `/api/events` en `ui_server.py`, vista
  "Monitor de Bandeja" en `documentador_predictivo.html`, y `server_guardian.py`
  que supervisa/reinicia el servidor (INICIAR.bat del dist ya lo lanza).
- La UI ya NO hace polling de 3 s: los eventos llegan por SSE (`EventSource`)
  y la página solo se relee durante un run activo.
- Pendiente del cambio: piloto real en Salesforce (6.2, 6.3) y commit/tag (6.5).
- El monitor trabaja en una **ventana dedicada** del navegador del bot
  (`ensure_monitor_window`): nunca minimizarla — la grilla virtual de
  Salesforce no renderiza sin visibilidad (0 filas verificado). Se crea con
  tamaño moderado (1150x760) y se reutiliza entre ciclos.
- Fuga de pestañas corregida: `create_driver` abre una pestaña `about:blank`
  por adjunte; `ensure_monitor_window` la cierra usando
  `driver.bot_work_tab_handle`, y el ciclo libera con
  `release_driver(close_tab=False)` para no cerrar la ventana del monitor.
- **Navegador trabado — causa y mitigaciones (Fase 1 implementada)**:
  el NTP online de Edge ≥148 (`ntp.msn.com`) puede quedar esperando
  headers tras el proxy y eso cuelga `NEW_SESSION` (playwright #41093).
  Mitigado: Edge se lanza con `about:blank`, `close_stuck_debugger_targets`
  cierra NTPs antes de cada attach, y el monitor usa **una sesión de
  driver persistente** (1 NEW_SESSION por arranque, no ~60/hora).
  `restart_browser` la invalida. **No resuelve** una pestaña del usuario
  que quede cargando sin commit — si `navegador_trabado` vuelve, ese es
  el siguiente frente (opciones: reload del target vía CDP, o aislar la
  ventana del monitor en un proceso Edge aparte).
- Tras el Pick Up el monitor **finaliza la toma** (`finalize_pick_up`):
  espera el panel "Contact Client" y pulsa solo su `Save` (nunca
  "Save & SendEmail", sin escribir en la sección — pedido del usuario:
  el texto vive solo en `Otra información`). La marca `Asignado` se
  garantiza en `Otra información` con `_ensure_take_mark`: lectura
  render-aware + append conservando contenido + re-lectura y un
  reintento. El resultado guarda `asignado_a` y `finalizacion`
  (`panel_guardado/marca_ok`, `campo_ausente`, `marca_error:...`) y cada
  `lead_result` se loguea en `ui_server.log`.
- Las franjas horarias se **autoguardan** al agregar/quitar (antes quedaban
  solo en el borrador y un F5 las perdía).
- **Modelo estricto de turnos** (vigente desde 2026-10-19, re-aplicado
  tras un revert breve): los leads solo se toman dentro de franjas.
  `_turno_propio_activo` exige `schedule` no vacío + `within_schedule`;
  `_any_turno_activo` en `ui_server` gatea el ciclo: sin franja propia ni
  del equipo vigente → `fuera_de_horario`. `schedule=[]` = "nunca a mi
  nombre". Prioridad: franja del monitor activa → `equipo=None` en
  `take_lead` (leads del usuario). Si la franja es del equipo → reasigna.
  **Revisar ahora (force) sin turno → corre en modo prueba** (fuerza
  `solo_listar` sin persistirlo): lista `detectado` sin tocar leads;
  `detectado` es reprocesable → al asignar la franja y revisar de nuevo,
  esos leads se toman/reasignan. Las franjas del equipo se autoguardan al
  agregar/quitar/editar (saveEquipo en cada cambio; el par pendiente se
  autocommite cuando ambos inputs fueron tocados).

## Post-Pick-Up: "Modificar Otra información" persistido (2026-10-10, reforzado 2026-10-15)

Bug reportado por el usuario (2 veces): el valor guardado en `Otra información`
quedaba "Modificar Otra información\nAsignado". Causa raíz: `find_field_text`
devuelve el texto del campo incluyendo la etiqueta accesible del lápiz de
edición; el append de `finalize_pick_up` la arrastraba al textarea.

Hardening final en `lead_monitor.py`:

- `OTHER_INFO_VALUE_SCRIPT`: lectura **estricta** que extrae solo el elemento
  de salida del campo (`lightning-formatted-text`/`slot` de salida), sin
  etiquetas accesibles — es la única lectura confiable para verificar lo
  persistido.
- `_strip_edit_button_label` quita la etiqueta **dondequiera que aparezca**
  (línea propia, pegada a glifo de ícono, partida en dos líneas), no solo si
  es la primera línea.
- `_ensure_take_mark` verifica post-Save con lectura estricta: si el valor
  persistido contiene etiqueta de UI (aunque `Asignado` esté presente),
  reescribe limpio y reintenta una vez.
- Tests de regresión en test_lead_monitor (418 tests OK).

Lección: los scripts de fix-up manuales deben usar `_strip_edit_button_label`
+ lectura estricta — el fix-up sin saneado introdujo la contaminación en
`...VUA0` (lectura de 26 chars = solo la etiqueta, campo vacío). El usuario
lo limpió a mano; Ema/Facundo/Gaston verificados limpios con lectura
estricta.

## Envío WhatsApp automático (envio-whatsapp-automatico, 2026-10-15)

Primer contacto por WhatsApp cuando el lead lo pidió
(`preferencia_contacto` ~ "vía whatsapp"), solo **bandeja AR** y con el
toggle UI **"WhatsApp auto"** activo (default apagado, persiste en
`monitor_state.enviar_whatsapp`, endpoint `POST /api/monitor/whatsapp`).

Flujo en `finalize_pick_up`: intento `1 INT Envío WhatsApp DD/MM/AAAA
HH:MM` en `Otra información` **en lugar de** `Asignado` (la línea ES la
evidencia) → verificación estricta → clic en `Send To Whatsapp` del
ribbon → espera del toast verde (~15 s) → cierre con X. Outcome con
tercer segmento: `panel_guardado/marca_ok/wa_ok`. **Si el toast no
aparece → `wa_no_confirmado` y jamás reintenta el clic** (riesgo de
doble mensaje). `_lead_documented` considera ya gestionado un campo con
`Asignado` o cualquier línea `N INT ...` — nunca duplica ni pisa.

**Contaminación `Asignado` en la rama WA** (fix 2026-10-15): el Save del
panel "Contact Client" (estatuto de la llamada) o un flow pueden escribir
`Asignado` en Otra información — el campo quedaba `1 INT...\nAsignado`.
`_ensure_take_mark(..., drop_take_mark=True)` trata la línea `Asignado`
solitaria como contaminación y la elimina (reusa la reparación de valores
contaminados), y `finalize_pick_up` hace una pasada de limpieza final
post-envío por si el `Asignado` aterriza asíncrono. Leads NO-whatsapp
conservan `Asignado` como marca.
Pendiente: validación en vivo con el primer lead AR-whatsapp real.

## Reasignación de leads por turno (reasignacion-por-turno, 2026-10-15)

Solución puente mientras no todos los puestos tienen la app: el bot toma
los leads con un solo usuario y los **reasigna a la encargada de turno**.

- UI "Equipo" (sección de Configuración del monitor): personas con
  `nombre` exacto de Salesforce y `franjas` propias hh:mm — persistido en
  `monitor_state.equipo`, endpoint `PUT /api/monitor/equipo`.
- `_encargada_activa(equipo)` toma la primera persona cuya franja cubre
  la hora (solapes: gana la primera). Si su nombre coincide con el
  propietario post-pickup (el usuario logueado), es su turno → flujo
  normal incl. WhatsApp automático en AR.
- Encargada distinta → **no se escribe ningún comentario** en Otra
  información (quedó pendiente de definición, 2026-10-16: el texto
  `Asignado - <método>` derivado de `preferencia_contacto` sigue
  implementado en `_reasignacion_mark` pero no se invoca hasta que el
  usuario confirme el formato) — y **jamás** se envía WhatsApp
  automático (el envío saldría de la sesión del bot). El outcome marca
  el segmento `sin_comentario`.
- Reasignación reutiliza la maquinaria del modal "Cambiar propietario"
  de `return_lead_to_queue` (scope Usuarios por defecto — no hace falta
  conmutar a Colas): `OWNER_SEARCH_INPUT_SCRIPT` + `send_keys` +
  `PICK_QUEUE_RESULT_SCRIPT` matchea la opción por nombre +
  `MODAL_CONFIRM_SCRIPT` confirma; luego relee el propietario para
  verificar. El lápiz del campo tiene `aria-label="Cambiar propietario"`
  y vive en shadow DOM (el botón de acción del ribbon abre el mismo
  modal). Outcome: 4º segmento `reasignado` / `reasignacion_error:<paso>`
  (modal|busqueda|opcion|confirmar|verificacion); si falla, el lead
  queda con el bot — nada se pierde en silencio.
- Carreras observadas en el lookup del modal (fix 2026-10-16):
  1. El input "Buscar Usuarios…" se monta **después** del contenedor —
     `_wait_owner_search_input` sondea hasta el deadline + settle de ~2 s
     antes de tipear (pegar enseguida no dispara la búsqueda: el texto
     queda pero no salen resultados). `_pick_owner_option` reescribe una
     vez si el primer tipeo no produjo opciones.
  2. El dropdown incluye opciones-acción `Buscar "X"` / `Mostrar todos
     los resultados` que **también contienen el nombre**: clicarlas abre
     la vista expandida "Resultados" donde no existe el botón
     "Cambiar propietario" (solo Cancelar) → `error:confirmar`.
     `PICK_QUEUE_RESULT_SCRIPT` las filtra (`/buscar|mostrar|ver todos|
     show all|search/`) y, si la vista expandida ya abrió, clica la fila
     `tr/[role=row]` del registro.
  3. Tras elegir el registro el footer re-renderiza el botón:
     `_confirm_owner_dialog` sondea en vez de clic único.
  4. `MODAL_CONFIRM_SCRIPT` con >1 match devolvía `ambiguous` y no
     clickeaba: el host `lightning-button` y el `<button>` de su shadow
     DOM llevan la misma etiqueta ("Cambiar propietario" / "Cancelar").
     Ahora se prefiere el `<button>` real — antes el fallo dejaba el
     modal abierto porque el dismiss tampoco podía clicar Cancelar.
- `asignado_a` en la tabla muestra la encargada cuando la reasignación
  sale (`finalize` termina en `/reasignado`).
- Verificación del Pick Up (fix 2026-10-16): el clic puede guardarse
  **después** de la ventana de 15 s y dejar el campo viejo en el DOM
  (lead `00QbD00000vY4bRUAS`: clic OK → `no_verificado` → sin marca ni
  WhatsApp, pero el owner ya era el usuario). Antes de declarar
  `no_verificado`, `take_lead` refresca la ficha y relee una vez
  (`_reread_owner_after_refresh`); y `no_verificado` admite un reintento
  (`should_process`, MAX_ATTEMPTS=2) — el ciclo siguiente relee el
  propietario antes de clicar, no es clic a ciegas.
- `state["bot_owner"]`: nombre del usuario de la sesión, persistido del
  primer `tomado` directo, leído por `load_state` y conservado por
  `_merge_cycle_state`. Si la relectura tras refresh muestra un
  propietario distinto de `bot_owner` (y de la cola), la carrera la ganó
  otra persona → `tomado_por_otro`, sin marca ni WhatsApp en el lead
  ajeno.
- Persona del equipo sin franjas es **inerte** (permitido — 2026-10-16):
  `_encargada_activa` la salta. La UI antes exigía ≥1 franja y bloqueaba
  todo el guardado: la config vieja seguía activa y un lead se asignó a
  una persona que el usuario creía sin franja. La validación solo exige
  nombre + franjas bien formadas.

## Estabilidad del navegador dedicado (2026-10-16)

- Edge suspendía la pestaña de Salesforce → el CDP dejaba de responder
  (`navegador_trabado`, reinicio manual). `launch_persistent_browser`
  ahora abre con `--disable-features=msEfficiencyMode,msSleepingTabs,
  msEdgeSleepingTabs` + `--disable-background-timer-throttling` +
  `--disable-backgrounding-occluded-windows` + `--disable-renderer-backgrounding`.
- Costo: sin sleeping tabs la RAM crece → reinicio automático cada
  `AUTO_BROWSER_RESTART_SECONDS` (4 h) desde `monitor_tick`, solo ocioso
  (lock de ciclo + sin cola activa); las pestañas se restauran solas.
  `browser_started_monotonic` se resetea en cada `restart_browser`.
- Ajuste horario por bandeja (`tz_offset`, horas vs. Colombia — donde
  corre el bot): defaults AR +2 / CO 0 / MX −1, selector ±3h en la UI.
  `_whatsapp_attempt_line(tz_offset)` documenta los intentos en la hora
  del país del lead: 9:00 CO → `11:00` para AR. Los intentos del
  documentador no lo usan: salen del historial de Wolkvox (hora real de
  la llamada).
- Pendiente: prueba real con `00QbD00000vUTK1UAO` o próximo lead en
  franja ajena.

## Panel "Contact Client" no detectado (2026-10-14, reforzado 2026-10-15)

Lead `...VUA0`: tomado pero sin Save del panel ni marca —
`finalizacion: sin_panel/marca_error:TimeoutException`. Lead `...QNxpUAG`:
`sin_panel/marca_ok` — la marca se escribió aunque el panel estaba
visible para el usuario → el panel **no es modal** (no bloquea el editor)
y vive en un contenedor que no matchea los selectores conocidos de
diálogo/panel.

Defensa en profundidad actual en `contactPanel()`/`finalize_pick_up`:

1. Detección por título (regex Contact Client / contactar / estatus...).
2. Detección estructural: botón `Save`/`Guardar` exacto dentro de un
   contenedor que tenga `SendEmail`/`correo` o textarea — acepta los
   selectores de panel conocidos **o cualquier ancestro con
   `position: fixed`** (docked composers/overlays propios).
3. Chequeo tardío: tras escribir la marca, re-mira 4 s — el panel puede
   renderizar pasada la ventana de 15 s. Outcomes
   `panel_tardio_guardado` / `panel_tardio_sin_save`.
4. Si nunca se detecta, `finalize_diag` guarda encabezados de paneles
   visibles + **cadena DOM de cada botón Save/SendEmail** (tag, clases,
   role, `{fixed}`) — esa firma revela el contenedor real.

`marca_error` dice el paso (`:editar:`/`:guardar:`). **Si vuelve
`sin_panel`, revisar `finalize_diag` en monitor_state.json** — la cadena
DOM mostrará exactamente qué contenedor falta en la lista.

Segunda tanda (`...QGd2UAG`, `...QPhxUAG`, 2026-10-14): el diag enriquecido
mostró que **no hay ningún botón Save visible en la pestaña activa** cuando
falla — solo `Rforce Send Email` del ribbon
(`runtime_platform_actions-actions-ribbon`) y lápices inline. El panel no
está en el DOM de esa pestaña en ese momento: abre en otro handle de la
consola o llega muy tarde. Nuevas defensas en `finalize_pick_up`:

- `_save_panel_in_other_handles`: si `sin_panel` persiste tras el chequeo
  tardío, escanea **todos los window handles** y guarda el panel donde lo
  encuentre (`panel_otra_tab_guardado`/`panel_otra_tab_sin_save`).
- Screenshot `sin_panel_<lead>_<ts>.png` en `ui_output/` cuando el panel
  nunca aparece — referenciado desde `finalize_diag` (`shot:<nombre>`).
  `diag_dir` baja por `run_cycle` → `run_bandeja_cycle` → `take_lead` →
  `finalize_pick_up` (ui_server pasa `ui_output`).

`navegador_trabado` reapareció con `/json/list` OK y sin NTP ni
chromedrivers huérfanos: sospechoso nuevo = service workers de
extensiones (`chrome-extension://...`) entre los targets. Si se repite,
probar `--disable-extensions` en el perfil del bot o filtrar workers en
la enumeración.

## Marca "Asignado" no persistía (2026-10-14) — dos causas raíz

Bug real en 3 leads tomados: Pick Up + Save del panel OK, pero `Otra
información` quedaba sin `Asignado` (el `except: pass` lo tragaba en
silencio). Diagnóstico con screenshots sobre lead real:

1. **Lectura ciega**: `find_field_text` devuelve `""` tanto para "campo
   vacío" como para "campo aún no renderizado" (lazy render de la zona de
   detalles tras el Save del panel). Con `""` el append pisaría el
   contenido real. Fix: `_read_other_information` espera el render
   (`field_result_if_found` distingue `found` de `text`) con scroll;
   ausente → `campo_ausente`, nunca escribe a ciegas.
2. **El Guardar descartaba el valor** (la causa principal):
   `SET_EDITOR_VALUE_SCRIPT` seteaba `.value` + `input`/`change`, pero
   Lightning confirma el campo al perder el foco — el clic JS sobre
   Guardar NO genera `blur`, el componente guardaba el valor viejo en
   silencio. Fix: `editor.blur()` + `focusout` tras el set (verificado en
   vivo: el valor persiste). **El documentador usaba el mismo script —
   cualquier escritura previa por este path pudo perderse igual.**

## Race: el ciclo pisaba cambios del usuario (2026-10-10)

`_monitor_cycle` leía el estado al arrancar y lo escribía entero al terminar:
un toggle/modo prueba/bandejas/"Limpiar lista" hecho durante el ciclo se
perdía. `_merge_cycle_state` relee el disco y solo aplica los campos del
ciclo (last_cycle_at, paused_reason, monitor_url y resultados nuevos o
actualizados por lead_id). Test de regresión en test_ui_server.
Nota: el API usa header `X-Bot-Token` (el query `?token=` solo sirve para SSE).

## Estabilidad del servidor: diagnóstico y decisión (2026-10-10)

### Diagnóstico

Los 17 `server_crash_*.log` de 2 días **no contienen ningún traceback**: son
`exit:1` (taskkill) y `exit:4294967295` (Stop-Process) — muertes externas por
despliegues, no caídas espontáneas. El servidor es estable; lo roto es el
ciclo de vida a su alrededor:

- **A. Doble bind del puerto 8765**: `ThreadingHTTPServer` activa
  `SO_REUSEADDR`, que en Windows (a diferencia de Unix) permite que DOS
  procesos se bindeen al mismo puerto sin error (MS docs + CPython #85307).
  Dos servidores conviviendo con tokens distintos → "token inválido"
  intermitente según a cuál le toque la petición.
- **B. Token regenerado por arranque**: `secrets.token_hex` en `main()` →
  cualquier reinicio deja vieja la página abierta → 403 silencioso
  ("el botón no hace nada").
- **C. Desplegar = taskkill**: cada deploy cuenta como crash (hasta el
  fatal marker tras 5 en 10 min) y dispara el backoff del guardián.
- **D. `navegador_trabado` (CDP cuelga)**: Edge ≥148 carga la Nueva Pestaña
  desde `ntp.msn.com` (`edge://new-tab-page-online`). Una pestaña
  `edge://newtab` que queda esperando headers (proxy corporativo) bloquea
  la enumeración de targets al crear la sesión → `NEW_SESSION` colgado
  mientras `/json` responde 200. Es playwright #41093, mismo síntoma
  (nuestro Edge es 154). Agravado por ~60 attach/detach por hora.

### Opciones evaluadas

1. **Endurecer lo actual** — ELEGIDA (Fase 1): lock de instancia, token
   persistente, `/api/reload` limpio, Edge sin NTP online, driver
   persistente entre ciclos.
2. **Servicio de Windows (WinSW/NSSM)**: descartada. Sesión 0 sin
   escritorio; Salesforce necesita ventana visible (grilla virtual
   renderiza 0 filas minimizada).
3. **pywebview (WebView2)**: Fase 2 candidata. UI+Python en un solo
   proceso: elimina A/B/C por diseño (sin HTTP ni token). No arregla D.
4. **Tauri 2 / Electron**: descartadas (sidecar Python no recomendado por
   Tauri; Electron = Chromium extra ~200 MB).
5. **Salesforce REST API** (Reports API + `PATCH Lead.OwnerId`): la
   solución estructural — sin navegador ni DOM frágil. **Bloqueada: el
   usuario lleva ~10 meses esperando que le habiliten la API** (Connected
   App / "API Enabled"). Seguir pidiéndola: cuando llegue, reemplaza la
   lectura de grilla y habilita el dashboard de equipo.
6. **Playwright**: no resuelve el cuelgue CDP (es el issue que documenta
   el bug de Edge); descartada.

### Por qué lock de instancia y no SO_EXCLUSIVEADDRUSE

`SO_EXCLUSIVEADDRUSE` impediría el doble bind, pero también impide
rebindear mientras haya sockets en TIME_WAIT: tras un reinicio con la
conexión SSE abierta, el servidor podría demorar ~2 min en volver. El
combo elegido cubre lo mismo sin ese costo: lockfile `msvcrt` (segunda
instancia sale limpia) + guardián que **adopta** un server sano que ya
ocupe el puerto + token persistente (aunque algo se cuele, el token es
el mismo).

## Diagramas archify (2026-10-20)
- Skill instalado = archify **3.0.0**: trace = barrida de entrada unica (~4 s). Para el
  rele continuo tipo cometa (loop --flow-cycle ~6.4 s) se usa el clone **3.1.0** en
  C:/Users/ax24611/Downloads/_dev/_archify_310 (node ../_archify_310/archify/bin/archify.mjs ...).
- Rutas workflow: cuando una arista horizontal "muro" bloquea una bajada vertical, el
  router manda la vertical por el exterior. Fix: liberar el corredor. manual-to-confirm
  se redirigio como arco de retorno con channelX+channelY+fromSide/toSide (mas
  robusto que via pixel-paths). select-to-bot quedo interior automatico.
- browser-check no reemplaza evidencia de builds viejos -> mover los *.browser-check.json
  previos a prev-static/ antes de re-finalizar.
- Validador 3.1.0 marca: cruces route-route, clearance de nodos/etiquetas de lane, stubs de
  endpoint >=8px, y bordes de lane atravesados en paralelo (label clearance).

## STOPPER resuelto: navegador_trabado = timeout corto (2026-10-19)

La pausa recurrente "navegador_trabado" NO era suspensión de pestañas ni
puerto muerto: el attach WebDriver al perfil dedicado (pestañas Salesforce
+ app, máquina cargada) tarda **~37 s** en completar NEW_SESSION — pero
ATTACH_SESSION_TIMEOUT_SECONDS era **15 s**. Cada ciclo abortaba la
sesión a medio formar → error eterno. Medido: perfil limpio 17.4 s,
perfil dedicado 37.2 s (verbose de msedgedriver). Subido a **60 s** →
recuperó al instante (lead tomado + wa_ok). Ojo: matar el msedgedriver a
medio attach deja procesos zombie difíciles de terminar.

## Auto-recuperación del navegador + notificaciones (2026-10-20)

El stopper de arriba quedó frecuente: cada tanto un ciclo no completa el
attach aun con 60 s y el monitor queda en `navegador_trabado` hasta que
alguien toca "Reiniciar navegador del bot". Ahora `monitor_tick` cuenta
ciclos consecutivos fallidos: a los **3 seguidos** llama a
`restart_browser()` sola, con cooldown de **10 min** entre reinicios
(`AUTO_RESTART_AFTER_FAILURES`, `AUTO_RESTART_COOLDOWN_SECONDS` en
ui_server.py). No corre si el bot de documentación está activo ni a mitad
de ciclo (mismo candado que el restart manual).

**Pestaña en blanco tras reinicio**: `launch_persistent_browser` abre Edge
con `about:blank` como URL inicial (sin URL, Edge ≥148 abre el NTP online
que cuelga el attach). Al restaurar sesión ese blank quedaba huérfano →
`restart_browser` lo cierra por CDP cuando hay más pestañas, y lo conserva
si es la única (cerrarlo tumbaría el navegador).

**Notificaciones de lead nuevo** (dos capas, independientes):
- Backend: `windows_toast()` (PowerShell BurntToast-less) ya disparaba
  toast de Windows por lead `tomado`.
- Frontend: checkbox **"Notificar"** junto a Sonido/WhatsApp → Notification
  API del browser; solo pide permiso al tildar, falla en silencio si el
  navegador lo niega, y solo dispara para lead_ids no vistos (mismo
  `monitorSeenIds` que el beep — sin duplicar en cada refresh).

**Tabla del monitor**: gestor de columnas (botón "Columnas"): checkboxes
para ocultar, drag en el encabezado para reordenar, borde derecho para
redimensionar; persistido en `localStorage` ("monitorColsV1") + botón
"Restablecer vista". Columna `Hace` renombrada a `⏱`. Filas ~20 px.

## Edge fantasma con --remote-debugging-port=0 (2026-10-21)

Stopper real del día: el monitor "tomaba" AR pero MX daba `bandeja_error
TimeoutException` invisible (los errores de bandeja solo iban por SSE, no al
log). La cadena de causas:

1. `create_driver(debugger_address)` con el puerto caído caía en la rama
   "crear navegador nuevo": msedgedriver lanzaba Edge con el perfil dedicado
   pero `--remote-debugging-port=0` (puerto aleatorio) y **sin las flags
   anti-suspensión** → navegador fantasma que el reinicio no podía matar
   (`find_listening_pid` busca por puerto) y cuyas pestañas Edge suspendía.
   Fix: con `debugger_address` configurado y sin listener → RuntimeError
   claro (el camino correcto es `launch_persistent_browser`).
2. `restart_browser` solo mataba el PID que escucha el puerto → con port=0
   no encontraba nada y el relanzado chocaba con el lock del perfil.
   Fix: `dedicated_profile_pids()` (PowerShell Win32_Process +
   `--user-data-dir`) como fallback cuando el puerto está vacío.
3. Reporte con 0 registros: el visor dentro del iframe muestra "Sin
   resultados / No se devolvió ningún registro" **sin renderizar la
   grilla** → `find_report_table` quemaba el timeout entero por ciclo.
   Fix: `ReportEmptyError` en `find_report_table` (chequea página+iframes);
   `read_visible_unassigned_leads` devuelve `(0, [])` y `read_full_report`
   corta limpio. `bandeja_error` ahora también se imprime al log.
   Ojo: "Total de registros 0" no es marcador confiable durante la carga;
   se usan "sin resultados"/"no se devolvio ningun registro"/"no results".

## Notificación de lead nuevo + prefs en servidor (2026-10-22)

Dos bugs reportados: "no llega la notificación de Windows" y "la vista de
columnas no se guarda al reabrir". Causas raíz encontradas:

1. **Permiso del navegador nunca pedido**: la casilla "Notificar" venía
   tildada por defecto pero `Notification.requestPermission()` solo se
   llamaba al destildar/retildar → `permission: "default"` para siempre y
   `monitorNotify()` salía en silencio. Fix: el permiso se pide en el
   primer gesto del usuario sobre la página; si queda `denied`, la casilla
   se deshabilita con tooltip. Además hay botón **"Probar aviso"** junto a
   la casilla: dispara una Notification al instante para verificar la
   cadena Edge→Windows sin esperar un lead.
2. **localStorage no cruza navegadores**: verificado en vivo — el guardado
   de `monitorColsV1` SÍ funcionaba en el Edge dedicado; el usuario abre la
   app en otro navegador/perfil (el corporativo borra site data al cerrar)
   donde arranca vacío. Fix: `PUT/GET /api/ui-prefs` persiste en
   `ui_output/ui_prefs.json` (merge por clave, valida `^[A-Za-z0-9_.-]{1,64}$`,
   tope 64 KB). Frontend: `saveUiPref()` escribe localStorage + servidor;
   `loadUiPrefs()` corre en `openMonitorView` — el servidor gana si tiene
   la clave, y si no, migra la config local una vez. Cubre `monitorColsV1`,
   `monitorSound`, `monitorNotify` (toggles ahora como booleano JSON;
   `prefBool()` convive con el "1"/"0" crudo viejo).
3. **Toast del backend solo cubría `tomado`**: ahora también dispara por
   lead_result **nuevo** que no sea tomado ("N lead(s) nuevo(s) en la
   bandeja") — dedup por `pre_results` (los ya listados no re-suenan cada
   ciclo). Ojo: el toast de PowerShell puede llegar al centro de
   notificaciones (Win+N) sin banner si Windows lo suprime; el registro no
   muestra bloqueo global ni por app, verificado.

## Franjas de equipo por bandeja (2026-10-23)

Bug real reportado: "dejé la bandeja MX para Argentina y el monitor tomó
leads de México y se los reasignó a Andres (AR)". Causa raíz:
`_encargada_activa(equipo)` elegía persona **solo por horario** — la
bandeja del lead no participaba de la decisión.

Modelo nuevo: cada franja del equipo lleva `bandejas: ["AR","MX",...]`
(lista de códigos de las bandejas habilitadas). Una persona puede cubrir
varias bandejas con franjas distintas (Roger: AR 10-12 + CO 11-13) o la
misma franja con varias bandejas (`["AR","MX"]`).

Reglas:

- `_encargada_activa(equipo, moment=None, bandeja=None)`: con `bandeja`
  (str o set de códigos) filtra a quien tenga una franja vigente que la
  incluya. Sin `bandeja` conserva el comportamiento viejo (compat con
  llamadas posicionales existentes).
- `run_bandeja_cycle`: si solo hay cobertura de equipo, el lead se toma y
  reasigna **únicamente** si alguna franja vigente cubre la bandeja del
  lead. Bandeja sin cobertura → `detectado` + `motivo: sin_cobertura`,
  sin abrir el lead (la UI muestra "sin cobertura" en Resultado). Franja
  propia vigente → toma cualquier bandeja, como antes.
- `validate_equipo`: normaliza franjas a `{start, end, bandejas}` —
  franja vieja sin `bandejas` queda `[]` = **no cubre nada** (decisión
  del usuario: no asumir "todas"). Rechaza solape horario **en la misma
  bandeja** (misma persona o entre personas); solapes en bandejas
  distintas son legales.
- `_any_turno_activo(state)`: una franja de equipo solo habilita el ciclo
  si cubre alguna bandeja **habilitada**; franja sin bandejas no
  habilita nada. Sin bandejas encendidas se delega al pause
  `sin_bandejas`.
- UI: checkboxes AR/CO/MX por franja (solo bandejas habilitadas) con
  `equipo-bandeja-cb`, chips por franja muestran los códigos. Columna
  "Contactar por" (antes "Contacto preferido") con SVG inline: logo
  WhatsApp / auricular llamada / vacío.
- Migración hecha por API: `PUT /api/monitor/equipo` con `franjas: []`
  conservando los nombres (las franjas viejas no tenían bandeja
  asignable). El usuario recarga franjas desde la UI.

## Franja propia también por bandeja (2026-10-23, segunda parte)

Pedido: la opción de bandeja faltaba en "Horario del monitor" (la franja
del usuario logueado) — solo existía en Equipo.

Semántica distinta al equipo, por diseño:

- Franja propia con `bandejas: []` o sin la clave = cubre TODAS las
  bandejas. Es la compat: las franjas ya guardadas (sin bandeja) siguen
  tomando todo — vaciar la cobertura habría apagado el monitor en
  silencio. La UI muestra el chip `[todas]`.
- Franja propia con bandejas = solo esas; un lead de otra bandeja cae al
  equipo que la cubra o queda `detectado/sin_cobertura`. La prioridad
  "franja propia gana" ahora es POR bandeja: AR propia no tapa al equipo
  de MX.
- Equipo sigue al revés: `bandejas: []` = no cubre nada (una persona sin
  bandeja es configuración incompleta).

Cambios:

- `monitor_store`: `_validate_franjas(slots, nombre)` unifica el parseo
  de franjas propias y de equipo (prefix de errores por nombre).
  `validate_schedule` ahora normaliza `{start,end,bandejas}` y rechaza
  solape solo en la misma bandeja (`_franjas_se_solapan`: `[]` propio =
  todas = pisa todo). `within_schedule(slots, moment, bandeja)` acepta
  código o iterable; `slot.get("bandejas")` vacío/ausente cubre todo.
- `lead_monitor.run_bandeja_cycle`: `propio_activo` exige que la franja
  vigente cubra `bandeja["code"]`.
- `ui_server._turno_propio_activo(state, bandejas)`: mismo filtro;
  `_any_turno_activo` pasa las bandejas habilitadas.
- UI: checkboxes de bandejas habilitadas junto a los inputs desde/hasta
  del horario propio (`sched-bandeja-cb` en `#schedBandejas`, render en
  `renderSchedule`); sin tildar ninguna = todas. `scheduleError` valida
  solape por bandeja igual que el backend.
- Incidente: el usuario borró sus franjas propias probando la UI y el
  autosave persistió `[]` — se restauraron por API (08-10 y 14-15:59,
  bandejas [] = todas). `saveSchedule` solo corre por clic: quitar chip,
  "Guardar horario" o "+ franja" — no hay disparo automático.

## Disponibilidad de bandejas para franjas (2026-10-23, tercera parte)

Pedido: las opciones de bandeja al armar una franja mostraban solo las
habilitadas — el usuario quiere ver las 3 siempre, pero que solo se
pueda cargar franja sobre bandejas **disponibles** = habilitada + link
de reporte. "Guardar bandejas" decide disponibilidad y el panel se
refresca solo (loadMonitorState re-renderiza tras el save; la
validación ya exigía URL para habilitar).

- UI: `monitorBandejaOptions()` devuelve `{code, available}` de todas
  las bandejas; `bandejaCheckbox()` pinta las 3 opciones y deja
  `disabled`/apagadas (`.bandeja-off`) las no disponibles, con tooltip
  "falta el link o está deshabilitada". `monitorBandejaCodes()` queda
  como el subconjunto disponible.
- `scheduleError` y `equipoError` rechazan franjas que apunten a
  bandejas no disponibles (además del checkbox deshabilitado: cubre el
  caso de datos viejos o editados a mano).
- Backend: `_bandeja_codes_disponibles(state)` (enabled && url) y
  `_franjas_con_bandeja_no_disponible` — `PUT /api/monitor/schedule` y
  `/api/monitor/equipo` devuelven 400 si una franja apunta a bandeja no
  disponible. El PUT de bandejas (`/api/monitor/config`) NO revalida
  franjas existentes: deshabilitar una bandeja con franjas cargadas es
  legal — quedan como cobertura muerta, no bloquean el guardado.
- Franja propia `bandejas: []` (todas) nunca falla el chequeo: cubre
  las que haya disponibles en cada momento.
- En vivo: opciones AR:on, CO:off, MX:on (CO sin link); PUT franja o
  equipo con CO -> 400 "Franjas apuntan a bandejas no disponibles: CO."

## Distribución de leads no hábiles (distribuir-leads-desde-archivo, 2026-10-24)

Módulo "Distribuir leads" en el selector de inicio: sube la BD de leads
nocturnos (`.xlsx`/`.csv` export Salesforce, ej. `QUALIF 24-10.xlsx` con la
persona destino en `Otra información`), mapea hoja+columnas, preview editable
por fila y ejecuta la reasignación en lote.

- `distribucion_loader.py`: `parse_archivo` (openpyxl server-side, archivo
  nunca se persiste) + `validate_distribucion_queue`/`load_distribucion_queue`.
- `run_distribucion_queue.py`: por lead abre registro y resuelve propietario —
  destino → `ya_asignado`; `SKIP_OWNERS` (AR_LEAD_COLD, AR_LEAD_EXPORT_GETLEAD,
  AR_LEAD_LEADIT_EXPORT) → `cola_excluida`; cola de ingreso (`unassigned_owner`
  de las bandejas del monitor) → Pick Up + panel best-effort + reassign;
  otro → reassign directo. Nunca escribe `Otra información`.
- `save_contact_panel_if_present` extraído en lead_monitor (orden inicial→
  marca→tardío preservado: el chequeo tardío va DESPUÉS de la marca porque su
  escritura le da tiempo al panel tardío a aparecer — test de regresión).
- Endpoints: `POST /api/distribucion/parse`, `PUT /api/distribucion-queue`
  (warning `monitor_activo`), `GET /api/distribucion-results`,
  `POST /run-distribucion` (misma exclusión mutua que /run y /run-close).
- Pendiente: prueba visual del preview en la UI y prueba real acotada con 1
  lead en vivo (usuario pidió no tocar Salesforce todavía).

## Verificadores de franja/bandeja (2026-10-24)

1. Franja sin bandeja: ahora es obligatoria en AMBOS editores (antes el
   horario propio permitía `[]` = todas). `scheduleError` la rechaza;
   `schedAdd` valida ANTES de agregar — la franja inválida no entra al
   borrador. Los PUT `/api/monitor/schedule` y `/equipo` devuelven 400
   "Cada franja debe indicar al menos una bandeja". Los datos viejos
   persistidos con `bandejas: []` siguen cargando (todas) — el bloqueo
   es solo en la escritura nueva; el usuario migró sus franjas a AR
   explícita a mano.
2. Bandeja sin link: el checkbox "habilitada" queda `disabled` hasta
   que el campo URL tenga texto (`syncEnabledLock` en renderBandejas);
   si se borra el link con la bandeja prendida, se destilda sola.
   `saveBandejas` corta antes del PUT con mensaje propio; el backend ya
   rechazaba `enabled && !url` (400).

## Bloqueo de alta + pop-up de advertencia (2026-10-24)

- `+ franja` del equipo ahora valida ANTES de agregar (equipoError sobre
  un probe del draft): la franja sin bandeja ya no entra al borrador —
  antes sí entraba y solo fallaba al guardar.
- Las acciones explícitas muestran `alert()`: "+ franja", "Agregar
  franja", "Guardar horario" (saveSchedule(true)) y "Guardar equipo"
  (saveEquipo(true)) — errores de validación y rechazos del servidor.
  Los auto-guardados (quitar chip, cambiar nombre) siguen solo pintando
  el mensaje rojo, para no spamear pop-ups.

## Toast de Windows con asignado + contacto (2026-10-24)

Pedido: que la notificación diga a quién quedó asignado el lead (en
verde) y el método de contacto elegido, avisando errores. Los toasts no
admiten color de texto — el indicador es emoji: ✅ tomado (con
`asignado_a` o "tu usuario"), ❌ error, ⚠️ no verificado, 👤
tomado_por_otro, 🔔 agregado de detectados nuevos; 💬 WhatsApp /
📞 Llamada desde `details.preferencia_contacto` (`_toast_contacto`).

- `windows_toast` pasó de ToastText02 a **ToastText04** (título + 3
  líneas: una por lead, "… y N más" si hay más). `_lead_toast_lines`
  dedup: los resultados sin cambio de status no re-sonan; error solo
  suena cuando el status cambia.
- Pipe a PowerShell ahora es **UTF-8** (`encoding="utf-8"` +
  `[Console]::InputEncoding=UTF8`): los emoji rompían cp1252 con
  UnicodeEncodeError silenciado por el except.

## Toast urgente + leads nombrados (2026-10-24, cierre)

- `scenario="urgent"` en el XML del toast: atraviesa el "No molestar"
  de Windows — el banner salta igual (verificado en vivo).
- Los detectados nuevos ya no van agregados ("N lead(s) nuevo(s)"): una
  línea por lead `🔔 nombre — nuevo en BANDEJA · contacto`, para que el
  toast identifique quién entró sin abrir la app.

## Foco de Windows / notebook de una pantalla (2026-10-26)

Queja: en una sola pantalla la ventana del bot salía al frente cada
ciclo. Causa: `switch_to.window` en ChromeDriver ejecuta
`Page.bringToFront` — `ensure_monitor_window` lo llamaba SIEMPRE aunque
el handle activo ya fuera el del monitor, más switch+close para limpiar
la pestaña de trabajo. Fix: switch solo cuando el handle activo difiere
del monitor, y la pestaña de trabajo se cierra por CDP
(`Target.closeTarget` vía `_close_tab_without_focus`) sin activarla.
NO minimizar la ventana (la grilla virtual da 0 filas) pero oculta
detrás de otras sí rinde por las flags anti-occlusion.
