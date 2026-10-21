# Diseño: endurecer-servidor-navegador

## Arquitectura

```
INICIAR.bat ──▶ server_guardian.py ──probe /status──▶ ¿puerto ya servido?
                       │                                 │
                       │                    sí ─▶ adoptar (vigilar probes
                       │                         hasta que deje de responder)
                       ▼
                 spawn ui_server.py ──▶ lockfile .ui_server.lock
                       │                    │ (2ª instancia → exit 0 limpio)
                       ▼
                 token persistente (bot_session.json)
                 + ThreadingHTTPServer :8765
                 + hilo monitor_loop ──▶ monitor_driver persistente
                                            │ 1 NEW_SESSION por arranque
                                            │ recreada solo si muere
                                            ▼
                                     Edge dedicado :9222
                                     (lanzado con about:blank;
                                      edge://newtab se cierra por
                                      /json/close antes de attach)

POST /api/reload ──▶ exit(0) ──▶ guardián respawnea sin contar crash
```

## Decisiones

### Lockfile en vez de SO_EXCLUSIVEADDRUSE

`SO_EXCLUSIVEADDRUSE` bloquea el rebind mientras haya sockets en
TIME_WAIT: cerrar una conexión SSE deja TIME_WAIT del lado servidor, y un
reinicio podría demorar hasta ~2 min. El lockfile `msvcrt.locking` impide
la segunda instancia del mismo script; el guardián adopta cualquier server
ajeno sano en el puerto; y el token persistente neutraliza el único daño
real del doble bind (el desfase de token).

### exit:0 = reinicio intencional

Convención nueva entre server y guardián: un hijo que sale con código 0
se relanza inmediatamente, sin crash log ni backoff. `/api/reload` usa
`os._exit(0)` tras responder — los deploys dejan de parecer caídas.

### Driver persistente del monitor

`monitor_driver` global: `_monitor_driver()` devuelve la sesión viva
(sonda `current_url`) o crea una nueva. El ciclo ya no llama
`release_driver` — la sesión sobrevive; solo se descarta si falla
(`_drop_monitor_driver` la libera best-effort) o si `restart_browser`
mata al navegador. Los bots de documentación/cierre siguen creando su
driver propio por run (no comparten la sesión del monitor).

### NTP sin contenido online

`launch_persistent_browser` abre `about:blank` cuando no recibe URLs —
Edge nunca crea el target `edge://new-tab-page-online`. Además
`close_stuck_debugger_targets` cierra por `/json/close` cualquier target
`edge://newtab`/`new-tab-page-online`/`chrome://newtab` residual antes de
cada `create_driver` adjunto: una pestaña que nunca termina de cargar no
puede colgar la sesión (causa raíz del `navegador_trabado`, playwright
#41093).
