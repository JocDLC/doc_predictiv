# Diseño: tomar-leads-automatico — "Monitor de Bandeja"

## Arquitectura

```
ui_server.py (proceso persistente)
  │  hilo monitor (daemon, apagado por defecto)
  │    cada MONITOR_INTERVAL_S (~60):
  │      ¿current_process activo?      → pausar ciclo
  │      ¿fuera de franja horaria?     → pausar ciclo
  │      ¿sesión caída?                → pausar + evento session_lost
  │      por cada bandeja habilitada:
  │        attach driver → GET bandeja.url → read_visible_unassigned_leads()
  │        por cada lead: GET record_url → owner==bandeja.owner? → Pick Up
  │                       → verificar owner cambió → resultado + estado
  │      broadcast SSE a la UI + toast Windows por lead tomado
  ▼
GET /api/events ──SSE──▶ documentador_predictivo.html  (vista Monitor de Bandeja)
GET    /api/monitor           estado + bandejas + franjas + últimos leads
POST   /api/monitor/toggle    habilitar/deshabilitar           (token)
PUT    /api/monitor/config    bandejas (url, owner, enabled)   (token)
PUT    /api/monitor/schedule  franjas [{inicio, fin}] hh:mm    (token)
```

`run_lock`/`current_process` siguen serializando documentación/cierre; el
monitor consulta ese estado y se salta el ciclo si hay operación activa, sin
tomar el lock (los runners tienen prioridad sobre el navegador).

## Configuración de bandejas

Cada bandeja es:

```json
{
  "code": "AR" | "CO" | "MX",
  "enabled": true,
  "url": "https://…/lightning/r/Report/…/view…",
  "unassigned_owner": "AR_LEAD_QUALIF",
  "expected_status": "Nuevo"
}
```

- `unassigned_owner` por defecto `<CODE>_LEAD_QUALIF`, editable (las colas de
  cada país pueden tener otro nombre). `expected_status` por defecto `"Nuevo"`,
  editable por si otra bandeja usa otra etiqueta.
- La UI ofrece las tres banderas; al habilitar una se exige URL válida
  (`https://` + `/lightning/r/Report/` en el path).
- La config vive en `ui_output/monitor_state.json` (persistida, editable desde
  la UI); `config.json` sigue siendo la fuente de `report_url` legacy para los
  runners existentes.

## Franjas horarias

`schedule: [{"start": "08:00", "end": "13:00"}, …]` validadas `HH:MM`, ordenadas
y sin solaparse (el servidor rechaza solapes). Interpretación:

- Lista **vacía** → el monitor corre en todo momento mientras esté habilitado.
- Con franjas → dentro de una franja el ciclo corre; fuera, el ciclo se omite
  con `paused_reason="fuera_de_horario"`. La habilitación sigue siendo manual:
  la franja acota, no enciende sola.

## Ciclo de monitoreo (`lead_monitor.py`)

`run_cycle(driver, bandeja, store) -> list[MonitorEvent]` separado del `sleep`,
para testearlo con driver falso:

1. `driver.get(bandeja.url)` y esperar tabla del reporte. Si la URL final es de
   login/auth → `session_lost`, el monitor se pausa.
2. `read_visible_unassigned_leads(driver, …)` con `unassigned_owner` de la
   bandeja y `field_aliases` de `lead_list_fields` (ya cubre las columnas del
   Monitor) → filas sin asignar con `details` completos. Segundo candado: la
   fila además exige `estado_candidato == bandeja.expected_status` (default
   `"Nuevo"`); una fila con otro estado se ignora aunque el propietario
   coincida.
3. Por cada `VisibleLead` con `lead_id` válido no procesado aún:
   a. `driver.get(build_record_url(salesforce_url, object, lead_id))`.
   b. Leer propietario visible: si ya no es el `unassigned_owner` →
      `tomado_por_otro` (no pulsar nada).
   c. Localizar `Pick Up` en la barra de acciones del registro (texto visible
      exacto, patrón any-frame existente). Si no existe → `error`.
   d. Clic → esperar asentamiento → releer propietario.
      Sigue igual → `no_verificado` (nunca re-clic a ciegas);
      distinto → `tomado`.
4. Guardar resultado + `details` de la fila (para la tabla del Monitor) y
   emitir eventos.

## Contrato de estado (`ui_output/monitor_state.json`)

```json
{
  "enabled": false,
  "bandejas": [{"code": "AR", "enabled": true, "url": "…", "unassigned_owner": "AR_LEAD_QUALIF"}],
  "schedule": [{"start": "08:00", "end": "20:00"}],
  "last_cycle_at": "…ISO…",
  "paused_reason": null,
  "results": [
    {"lead_id": "00Q…", "bandeja": "AR", "status": "tomado", "at": "…",
     "details": {"nombre": "…", "apellido": "…", "campana": "…", "…": "…"}}
  ]
}
```

`results` es acotado (p. ej. últimos 200). Los `details` contienen datos de
clientes: el archivo vive en `ui_output/` (ignorado por Git, equipo autorizado)
como ya hacen los snapshots; logs/consola/eventos de diagnóstico usan solo
`lead_id` enmascarado. Los eventos SSE hacia la UI sí transportan `details`
porque la tabla del Monitor los muestra (mismo nivel de exposición que la UI
actual).

Estados por Lead: `tomado`, `tomado_por_otro`, `no_verificado`, `error`
(misma tabla del diseño previo). Los estados finales no se reprocesan; `error`
permite un reintento en el ciclo siguiente.

## Vista "Monitor de Bandeja" (UI)

- **Tabla de leads** con las columnas de la bandeja: fecha de creación,
  campaña, preferencia de contacto, propietario, sub-tipo de interés, nombre,
  apellido, teléfono móvil, concesionario, vehículo de interés, correo,
  Lead ID, otra información — valores tomados de `details` (lo que la columna
  visible del reporte expone; si falta una columna → "No disponible en bandeja",
  mismo criterio que REQ-402). La tabla MUST NOT mostrar `#` ni
  `Estado de candidato`: el estado solo se usa como verificador interno.
- **Toggle** de activación con estado visible (habilitado / pausado + motivo).
- **Selector de bandejas**: banderas AR/CO/MX con checkbox + campo de URL
  editable y guardado.
- **Editor de franjas**: filas `hh:mm – hh:mm` con agregar/quitar.
- **Aviso**: al llegar evento `monitor` con `taken>0` → banner + beep Web
  Audio + refresco de la tabla solo en ese momento.

## Notificaciones

- **SSE** `GET /api/events`: conexión larga; el servidor emite
  `data: {"type":"monitor","taken":N,"leads":[{lead_id,details,status}]}` y
  `{"type":"session_lost"}`. Cada suscriptor es una cola en memoria. Reemplaza
  el polling de ~3 s para eventos del monitor y de los runners.
- **Windows toast**: `subprocess` PowerShell con `Windows.UI.Notifications`
  XML nativo, fire-and-forget; texto genérico ("Nuevo lead asignado") sin datos
  del cliente; si falla solo queda en log.

## Recuperación ante fallos

- Timeout al abrir registro / encontrar botón → `error` (máx. 1 reintento en el
  siguiente ciclo, luego revisión manual).
- `no_verificado` nunca repite el clic: queda marcado y se avisa.
- Sesión caída: pausa total hasta que una lectura vuelva a ver la tabla
  (recuperación automática tras re-login manual).
- URL de bandeja inválida o sin permisos → esa bandeja se marca `error` y el
  ciclo continúa con las demás.

## Guardián del servidor (`server_guardian.py`)

Hoy `INICIAR.bat` lanza `ui_server.py` y si el proceso muere nadie lo revive.
El guardián es un proceso mínimo y separado (un crash del servidor no puede
matar al guardián):

```
server_guardian.py
  ├── lanza  python ui_server.py  (stdout/stderr → logs/ui_server.log)
  ├── cada 30 s: GET /status
  │     proceso muerto o N sondeos fallidos seguidos
  │       → copia la salida a logs/server_crash_<ts>.log
  │       → relanza con backoff (0 s, 5 s, 15 s, 30 s … máx 5 min)
  ├── ≥5 caídas en 10 min → deja de reintentar y escribe
  │     logs/server_crash_FATAL.log (evita loop infinito)
  └── Ctrl+C → apaga el servidor hijo y sale
```

- `INICIAR.bat` lanza el guardián en vez de `ui_server.py` directo (el cambio
  del `.bat` viaja con el próximo paquete `dist/`).
- La UI, al perder el canal SSE, muestra "conexión perdida con el servidor" y
  reconecta sola (`EventSource` ya reintenta por defecto).

## Datos y privacidad

- Logs y consola: solo conteos y `lead_id` enmascarado (`00Q***EAA`).
- `monitor_state.json` puede contener `details` del Lead (equipo autorizado,
  ignorado por Git), consistente con `*.snapshots.json`.
- Toast de Windows: texto genérico sin datos del cliente.
