# Propuesta: tomar-leads-automatico

## Contexto

Los leads llegan a las bandejas (reportes `LEADS ARG`, `LEADS CO`, `LEADS MX`)
con propietario sin asignar (`<PAIS>_LEAD_QUALIF`) y deben ser tomados y
gestionados en menos de 10 minutos. Hoy una persona recarga la pestaña cada
pocos minutos: si aparece una fila sin asignar, abre el registro y pulsa el
botón `Pick Up` para que el Lead quede a nombre de su usuario.

Esa revisión manual constante es el cuello de botella: la persona está atada a
la bandeja en vez de gestionar los leads que ya tomó.

## Objetivo

Un **Monitor de Bandeja** dentro de `ui_server.py` + una vista propia en la UI
que, mientras esté activado:

1. Cada ~60 s refresca las bandejas habilitadas y lee las filas con
   propietario sin asignar (reutilizando `read_visible_unassigned_leads`).
2. Por cada Lead encontrado: abre el registro, re-verifica el propietario,
   pulsa `Pick Up` y verifica que el propietario cambió.
3. Avisa a la persona: evento en tiempo real a la UI (banner + sonido) y
   notificación toast de Windows, aunque la UI esté cerrada.
4. Muestra en la vista Monitor la lista de leads detectados/tomados con sus
   columnas de la bandeja.

## Decisiones aprobadas (del análisis con el usuario)

- **Pick Up automático**: sin confirmación humana por Lead; la habilitación del
  monitor completo es la decisión humana.
- **Todos los visibles**: si un ciclo encuentra varios leads sin asignar, toma
  todos.
- **Ubicación**: hilo dentro de `ui_server.py` (proceso ya persistente; permite
  pausar el monitor mientras corren los bots de documentación/cierre).
- **Aviso**: banner + sonido en la UI **y** toast de Windows.
- **Sin polling de 3 s**: la comunicación servidor → UI pasa a eventos empujados
  por el servidor (SSE). El polling actual rompe la selección de texto y genera
  tráfico innecesario.
- **Nombre**: la vista y la función se llaman "Monitor de Bandeja".
- **Multi-bandeja**: bandejas por país (AR/CO/MX) elegibles con bandera, cada
  una con su URL y su propietario-sin-asignar editables y persistidos.
- **Franjas horarias**: lista de ventanas `hh:mm–hh:mm` editables en la UI;
  fuera de franja el monitor se pausa solo.
- **Verificador de estado**: un lead solo se toma si además del propietario sin
  asignar su `Estado de candidato` es `Nuevo` (solo los leads qualif tienen ese
  estado). La columna no se muestra en la tabla; sirve como segundo candado.
- **Guardián del servidor**: `ui_server.py` se cae en producción y nada lo
  revive. Se agrega un proceso supervisor que lo reinicia con backoff, sondea
  `/status` para detectar "vivo pero trabado" y guarda el motivo de cada caída.

## Alcance

- `automation_salesforce/lead_monitor.py` (nuevo): ciclo único de monitoreo
  testeable con driver falso (detectar → Pick Up → verificar → resultado),
  iterando las bandejas habilitadas.
- `automation_salesforce/monitor_store.py` (nuevo): estado persistente
  (`ui_output/monitor_state.json`): habilitación, bandejas configuradas, franjas
  horarias, resultados y detalles de leads para la tabla del Monitor.
- `automation_salesforce/server_guardian.py` (nuevo): supervisor que lanza y
  mantiene vivo `ui_server.py` (reinicio con backoff, sondeo `/status`, log de
  caídas); `INICIAR.bat` del paquete pasa a lanzar el guardián.
- `automation_salesforce/ui_server.py`: hilo monitor (apagado por defecto),
  endpoints `/api/monitor*` (estado, toggle, bandejas, franjas), canal de
  eventos SSE (`/api/events`), toast de Windows vía PowerShell sin dependencias
  nuevas.
- `documentador_predictivo.html`: vista **Monitor de Bandeja** con tabla de
  leads, toggle de activación, selector de bandejas con URL editable, editor de
  franjas horarias, cliente SSE, banner + sonido; reemplazo del polling de
  estado por eventos.
- Tests Python (driver falso, servidor, store) y Node/vm (UI); sin Salesforce
  real en suite.

## Fuera de alcance

- Scrapling / ScrapeGraphAI: evaluadas y descartadas (ScrapeGraphAI enviaría
  datos de clientes a un LLM y no ejecuta acciones; Scrapling opera sobre sus
  propias sesiones, no sobre el Edge persistente adjunto). La idea de
  relocalización adaptativa queda anotada como plan B si Salesforce cambia el
  DOM.
- Franjas distintas por día de semana (las franjas aplican a todos los días).
- Asignación a usuarios específicos o reparto entre auxiliares: `Pick Up`
  asigna al usuario de la sesión activa, que es quien corre el bot.
- Reintentos infinitos, colas de prioridad o reglas de negocio sobre qué leads
  tomar: se toma todo lo visible sin asignar.
- Notificaciones por correo/chat externo.

## Riesgos

- **Primera escritura sin confirmación por registro**: `Pick Up` cambia el
  propietario. Mitigación: monitor apagado por defecto, re-verificación de
  propietario antes del clic y verificación posterior obligatoria.
- **Carrera entre operadores**: dos monitores o una persona manual pueden
  disputar el mismo Lead. Mitigación: si el propietario ya no es el de la
  bandeja al abrir el registro, se clasifica `tomado_por_otro` y no se pulsa
  nada.
- **Contención del navegador**: el monitor comparte el Edge persistente con los
  bots existentes. Mitigación: el ciclo se salta mientras `current_process`
  está activo.
- **Sesión expirada**: el login/2FA es manual. Si el reporte no carga por
  sesión caída, el monitor se pausa y avisa; no reintenta a ciegas.
- **Multi-bandeja**: cada bandeja puede tener columnas/propietarios distintos;
  por eso el propietario-sin-asignar y la URL son configurables por bandeja.
- **SSE**: conexiones largas ocupan un hilo del `ThreadingHTTPServer` cada una;
  es aceptable para una UI local, pero el handler debe tolerar desconexiones.
