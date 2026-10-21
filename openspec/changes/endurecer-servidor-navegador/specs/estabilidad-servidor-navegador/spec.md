# Spec: estabilidad-servidor-navegador

## ADDED Requirements

### Requirement: REQ-1001: Instancia única del servidor

El servidor MUST impedir que dos `ui_server.py` convivan en la misma
instalación: un segundo proceso MUST salir con código 0 sin bindear el
puerto ni escribir `bot_session.json`. El guardián MUST NOT pelear el
puerto: si `/status` ya responde (propio o ajeno), MUST vigilarlo con
sondeos y spawnear solo cuando deje de responder.

#### Scenario: segundo ui_server sale limpio

**Given** un `ui_server.py` corriendo con el lock de instancia tomado.
**When** se lanza otro `ui_server.py`.
**Then** imprime el aviso y termina con código 0 sin tocar el puerto.

#### Scenario: el guardián adopta un server ajeno

**Given** un servidor sano ya escuchando en 8765.
**When** arranca `server_guardian.py`.
**Then** NO spawnea un segundo servidor; vigila con `/status` hasta que
deje de responder y recién ahí levanta el suyo.

### Requirement: REQ-1002: Token de sesión persistente

El token de `bot_session.json` MUST sobrevivir a los reinicios del
servidor: se genera una única vez y se reutiliza mientras el archivo
siga siendo válido.

#### Scenario: la página abierta no queda vieja

**Given** una UI abierta con el token de la sesión N.
**When** el servidor se reinicia (sesión N+1).
**Then** las peticiones con el token N siguen siendo aceptadas.

### Requirement: REQ-1003: Reinicio intencional del servidor

`POST /api/reload` con token válido MUST responder 200 y terminar el
proceso con código 0. El guardián MUST tratar `exit:0` como reinicio
intencional: relanzar de inmediato, sin crash log ni backoff ni conteo
hacia el marcador fatal.

#### Scenario: deploy sin "caída"

**Given** el servidor corriendo bajo el guardián.
**When** se invoca `POST /api/reload`.
**Then** el proceso sale con 0 y el guardián lo relanza sin registrar
`server_crash_*.log` ni sumar al contador de caídas.

### Requirement: REQ-1004: El navegador no cuelga el attach por el NTP online

El navegador dedicado MUST lanzarse con `about:blank` cuando no hay URLs
que abrir (nunca `edge://newtab` online). Antes de cada sesión adjunta,
los targets `edge://newtab`/`new-tab-page-online`/`chrome://newtab`
MUST cerrarse vía CDP para que una pestaña que nunca termina de cargar
no pueda bloquear la creación de sesión.

#### Scenario: attach sin NTP trabado

**Given** un navegador con un target `edge://newtab` presente.
**When** el monitor crea su driver.
**Then** el target se cierra vía `/json/close` antes de `NEW_SESSION`.

### Requirement: REQ-1005: Sesión de driver persistente del monitor

El monitor MUST mantener una única sesión de WebDriver entre ciclos:
mientras la sesión responda, los ciclos la reutilizan; si murió se recrea
una sola vez. `restart_browser` y el apagado del servidor MUST
invalidarla/liberarla.

#### Scenario: reutilización entre ciclos

**Given** un ciclo del monitor que terminó bien.
**When** corre el siguiente ciclo.
**Then** usa la misma sesión (sin nueva `NEW_SESSION` ni chromedriver).

#### Scenario: sesión muerta

**Given** la sesión persistente que ya no responde.
**When** corre el ciclo.
**Then** se crea una sesión nueva una sola vez; la próxima iteración
la reutiliza.
