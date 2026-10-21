# Propuesta: endurecer-servidor-navegador

## Contexto

El servidor local no se cae solo: los crash logs muestran solo muertes
externas por despliegue (`exit:1`/`exit:-1` de taskkill). Los síntomas
reales ("token inválido", "reiniciar navegador no hace nada",
`navegador_trabado`) tienen cuatro causas raíz identificadas:

1. `SO_REUSEADDR` en Windows permite dos servidores en el puerto 8765 con
   tokens distintos (CPython #85307).
2. El token se regenera en cada arranque → la página abierta queda vieja.
3. Desplegar código exige `taskkill` → cada deploy es un "crash" para el
   guardián y dispara su backoff.
4. Edge ≥148 crea una pestaña `edge://newtab` que carga `ntp.msn.com`;
   detrás del proxy puede quedar esperando headers y eso **cuelga la
   creación de sesión CDP** aunque `/json` responda (playwright #41093).
   Se agrava con ~60 attach/detach de driver por hora.

## Objetivo

Eliminar las cuatro causas sin cambiar la arquitectura (la migración a
app nativa con pywebview queda como Fase 2; la API de Salesforce está
bloqueada hace meses por terceros).

1. **Instancia única**: lockfile `msvcrt` — un segundo `ui_server` sale
   limpio en vez de pelear el puerto; el guardián **adopta** un server
   sano que ya ocupe el puerto en vez de reiniciar en bucle.
2. **Token persistente**: se genera una vez y se reutiliza en
   `bot_session.json`; una página abierta nunca queda vieja.
3. **Reload limpio**: `POST /api/reload` termina el proceso con exit 0
   (convención "reinicio intencional") y el guardián lo relanza al
   instante sin contarlo como caída.
4. **Navegador anti-cuelgue**: Edge se lanza con `about:blank` (nunca el
   NTP online); antes de cada attach se cierran targets `edge://newtab`/
   `new-tab-page-online` vía CDP; el monitor mantiene **una sesión de
   driver persistente** entre ciclos (1 NEW_SESSION por arranque, no
   ~60/hora).

## Impacto

- `ui_server.py`: token, lock, `/api/reload`, driver persistente del
  monitor, adopción de ventana intacta.
- `server_guardian.py`: pre-probe de adopción + semántica `exit:0`.
- `browser_factory.py`: `about:blank` por defecto +
  `close_stuck_debugger_targets`.
- Tests de regresión en `tests/`. Sin cambios de UI.
- Riesgo controlado: si la sesión persistente queda vieja, el ciclo la
  recrea; `restart_browser` la invalida explícitamente.
