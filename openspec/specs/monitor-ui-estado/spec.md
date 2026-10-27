## ADDED Requirements

### Requirement: Tarjeta de estado con semáforo
La vista Monitor de Bandeja SHALL mostrar, debajo del título y antes del texto
explicativo, una tarjeta de estado cuyo color y texto principal se derivan del
estado real del monitor (`enabled`, `paused_reason`, `bot_running`,
`cycle_running`) con esta precedencia:

1. `enabled = false` → **gris**, "Monitor APAGADO".
2. `paused_reason` ∈ {`session_lost`, `navegador_trabado`, `sin_bandejas`} o
   empieza con `error:` → **rojo**, "Requiere atención — <motivo>".
3. `paused_reason` ∈ {`fuera_de_horario`, `run_activo`} o `bot_running = true`
   → **ámbar**, "En espera — <motivo>".
4. En otro caso → **verde**, "Monitor ACTIVO — revisando cada ~2 minutos"
   (o "revisando bandejas…" si `cycle_running = true`).

La tarjeta MUST mostrar además una línea de detalle con los indicadores
aplicables (modo prueba, WhatsApp auto, última revisión hh:mm:ss) y MUST NOT
mostrar a la vez "activo" y "pausado" en el texto principal.

#### Scenario: activo trabajando
- **WHEN** `enabled = true` y `paused_reason` es nulo
- **THEN** la tarjeta queda en verde con el texto "Monitor ACTIVO"

#### Scenario: activo fuera de horario
- **WHEN** `enabled = true` y `paused_reason = "fuera_de_horario"`
- **THEN** la tarjeta queda en ámbar con "En espera — fuera del horario configurado" y no dice "Monitor ACTIVO"

#### Scenario: sesión vencida
- **WHEN** `enabled = true` y `paused_reason = "session_lost"`
- **THEN** la tarjeta queda en rojo y el texto menciona "sesión de Salesforce"

#### Scenario: apagado
- **WHEN** `enabled = false`
- **THEN** la tarjeta queda en gris con "Monitor APAGADO", aunque haya un `paused_reason` del último ciclo (que pasa a la línea de detalle como "último ciclo: …")

#### Scenario: detalle con indicadores
- **WHEN** `enviar_whatsapp = true`, `solo_listar = true` y hay `last_cycle_at`
- **THEN** la línea de detalle incluye "modo prueba", "WhatsApp auto" y "última revisión"

#### Scenario: servidor no responde
- **WHEN** falla la lectura de `/api/monitor`
- **THEN** la tarjeta queda en rojo con el mensaje de servidor caído o sesión obsoleta existente

### Requirement: Interruptor encendido/apagado
El control de activación SHALL ser un interruptor (switch) accesible dentro de
la tarjeta de estado, con `role="switch"` y `aria-checked` reflejando
`enabled`, y la etiqueta "Encendido"/"Apagado". Al accionarlo MUST llamar a
`POST /api/monitor/toggle` y recargar el estado. El botón de texto "Monitor
activo — tocar para pausar" MUST dejar de existir.

#### Scenario: refleja encendido
- **WHEN** `enabled = true`
- **THEN** el switch tiene `aria-checked="true"` y la etiqueta "Encendido"

#### Scenario: refleja apagado
- **WHEN** `enabled = false`
- **THEN** el switch tiene `aria-checked="false"` y la etiqueta "Apagado"

#### Scenario: accionar el switch
- **WHEN** el usuario hace click en el switch
- **THEN** se envía `POST /api/monitor/toggle` y la tarjeta se re-renderiza con el nuevo estado

### Requirement: Opciones agrupadas en dos columnas
Las opciones del monitor SHALL presentarse en dos grupos con título, lado a
lado (apilados en pantallas angostas):
- **Comportamiento**: Modo prueba, WhatsApp auto.
- **Avisos**: Sonido, Notificar y el botón "Probar aviso".

Los ids y el comportamiento de cada checkbox (`monitorDryRun`,
`monitorWhatsapp`, `monitorSound`, `monitorNotify`, `monitorNotifyTest`) MUST
mantenerse sin cambios.

#### Scenario: grupos visibles
- **WHEN** se abre la vista Monitor
- **THEN** se ven los títulos "Comportamiento" y "Avisos" con sus opciones correspondientes, separados de la fila de botones de acción

#### Scenario: comportamiento intacto
- **WHEN** el usuario tilda "Modo prueba"
- **THEN** se llama al mismo endpoint que antes y el checkbox refleja `solo_listar`
