# Tasks: endurecer-servidor-navegador

> Ningún cambio debilita tests existentes; el ciclo del monitor conserva
> sus garantías (un candado, ventana dedicada, merge de estado).

## 1. Token persistente e instancia única (ui_server.py)

- [x] 1.1 `load_or_create_token(ui_output_directory)`: lee el token de
  `bot_session.json` si existe; genera uno nuevo solo si falta o el
  archivo es inválido.
- [x] 1.2 `acquire_instance_lock(ui_output_directory)`: lock `msvcrt`
  no bloqueante sobre `.ui_server.lock`; segunda instancia imprime
  aviso y sale con código 0. Sin lock en plataformas sin `msvcrt`.
- [x] 1.3 `main()` usa ambas: lock → token → bind → session file.
- [x] 1.4 Tests: token se reutiliza del archivo; segundo lock devuelve
  None.

## 2. Reload limpio

- [x] 2.1 `POST /api/reload` (token obligatorio): responde 200 y sale con
  `os._exit(0)` en un timer daemon.
- [x] 2.2 `server_guardian.py`: `exit:0` se relanza sin crash log ni
  backoff ni conteo hacia `MAX_CRASHES`.
- [x] 2.3 Tests: endpoint 200; guardián no cuenta exit:0 como caída.

## 3. Adopción de server ajeno (server_guardian.py)

- [x] 3.1 Antes de spawnear, si `probe()` responde, vigilar ese server
  con probes periódicos; spawnear recién cuando deje de responder.
- [x] 3.2 Tras la muerte del hijo, si el puerto sigue servido por otro
  proceso, adoptar en vez de spawnear.
- [x] 3.3 Tests con probe/spawn falsos: no spawnea mientras probe sea
  true; tras exit:0 con puerto ocupado adopta sin contar crash.

## 4. Navegador anti-cuelgue (browser_factory.py)

- [x] 4.1 `launch_persistent_browser` usa `about:blank` cuando `urls`
  es None/vacío.
- [x] 4.2 `close_stuck_debugger_targets(debugger_address)`: cierra por
  `/json/close/{id}` (PUT con fallback GET) los targets `edge://newtab`,
  `edge://new-tab-page-online` y `chrome://newtab`.
- [x] 4.3 `create_driver` lo invoca antes de crear la sesión adjunta.
- [x] 4.4 Tests: launch incluye about:blank; close solo toca targets
  newtab; create_driver lo llama antes del attach.

## 5. Driver persistente del monitor (ui_server.py)

- [x] 5.1 `monitor_driver` global + `_monitor_driver(...)`: reutiliza la
  sesión si `current_url` responde; la recrea si murió.
- [x] 5.2 El ciclo ya no libera el driver al terminar; excepciones que
  mataron la sesión la descartan para el próximo ciclo.
- [x] 5.3 `restart_browser` y el shutdown del servidor descartan/liberan
  `monitor_driver`.
- [x] 5.4 Tests: segundo ciclo reutiliza; sesión muerta se recrea;
  restart_browser la invalida.

## 6. Cierre

- [x] 6.1 Suite completa + Ruff. (410 tests OK, ruff check limpio)
- [x] 6.2 Sync a `dist/DocumentadorPredictivo/app/` y reinicio limpio
  del stack (guardián único); verificar `/status`, token persistente
  tras reinicio y un ciclo del monitor sin `navegador_trabado`.
  (Verificado en vivo: /api/reload respawnea sin crash log, token
  conservado, Edge abre con about:blank, 2 ciclos limpios, ventana
  adoptada sin duplicados.)
- [x] 6.3 `graphify update .`; `openspec validate --changes`.
  (1840 nodos/2861 aristas; 18/18 cambios válidos.)
