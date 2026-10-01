# Handoff — automation_salesforce

## PRIORIDAD — Traspaso del incidente de falsos documentados (2026-10-01)

**Leer esta sección antes del material histórico que sigue.** Este es un plan
pendiente de implementación, no una declaración de que el defecto esté corregido.
El usuario pidió dejar instrucciones para que otro agente implemente la solución.

### Situación del usuario y límites

- El usuario detectó Leads verdes como `guardado` cuyo campo conservaba comentarios
  anteriores y no incluía las llamadas del CSV nuevo.
- **El usuario ya hizo las correcciones manualmente en Salesforce.** No regenerar
  ni ejecutar una cola con los afectados. No reintentar tandas como prueba.
- No invocar `/run`, runners con `--auto`, correcciones ni reinicio/cierre de Edge
  para investigar. Una prueba real que escriba necesita autorización específica
  del usuario para esa tanda; aprobaciones históricas no aplican.
- No borrar progreso, selección, recuperación local ni históricos. No recomendar
  importar resultados antiguos o desmarcar documentados como solución provisional.
- Conservar cambios del usuario en código/tests. Revisar `git status` y los diffs
  antes de editar; no hacer reset, commit ni push sin autorización actual.
- No incluir datos de clientes en tests, logs, Git ni ZIP. El CSV y los snapshots
  solo se usan localmente para cotejo; las pruebas automatizadas usan datos ficticios.

### Diagnóstico comprobado y alcance

Se cruzó el archivo local proporcionado por el usuario
`C:\Users\ax24611\Downloads\predictive-Leads_en_curso_ARG-20260930-152140.csv`
con `queues/cola_activa.resultado.json` y
`ui_output/cola_activa.snapshots.json`.

En el momento del diagnóstico:

- CSV: 137 registros con 137 IDs distintos y llamadas reconocidas por el parser.
- Los 13 IDs reportados tenían dos llamadas cada uno del 29 y 30/09; ninguno de
  esos IDs de llamada aparecía en su snapshot antiguo. Los resultados eran
  anteriores: 11 del 28/09 y 2 del 29/09 de madrugada, fechas UTC.
- El cruce completo encontró 22 Leads con 44 llamadas ausentes de sus snapshots
  pero marcables como documentados por el historial. **No es un inventario actual
  de faltantes en Salesforce:** el usuario ya hizo correcciones manuales.
- Prueba en Node `vm`, usando las funciones reales del HTML y datos solo en memoria:
  13 Leads elegibles -> aplicar resultados antiguos -> 0 elegibles.
  Repitiendo con SOLO snapshots antiguos también quedaron 0.
- Desmarcar un Lead con `setDone(lead, false)` no lo protege: el siguiente
  `pollBotResults()` vuelve a ponerlo en `done: true` y a excluirlo de la cola.
- También se reprodujo: resultado `error` reciente + snapshot antiguo -> `done: true`.
- No se probó un fallo de Guardar de Salesforce para estos 13 casos. El defecto
  reproducido es atribuir éxito histórico a llamadas nuevas y excluirlas del envío.
- No se conoce con certeza qué acción vació la selección del usuario. No afirmar
  que todo es recuperable solo porque sobreviven resultados: estos conservan el
  último registro por Lead, no un historial completo de todas las ejecuciones.

### Cadena causal y archivos que hay que leer

En `../documentador_predictivo.html`:

1. `loadCSVContent()` separa progreso por nombre y tamaño del CSV, pero eso no
   impide que el polling vuelva a importar estados globales históricos.
2. `applyBotResult()` pone `done: true` por `lead_id` y estado `guardado/corregido`,
   sin comprobar las llamadas, contenido solicitado ni ejecución.
3. `applySnapshot()` también pone `done: true` por `lead_id`, sin comprobar cobertura.
4. `pollBotResults()` carga todos los resultados y snapshots, actualiza progreso
   y llama a `writeActiveQueue()`; `startQueuePolling()` lo ejecuta inmediatamente
   al entrar a la cola y cada 3000 ms.
5. `buildBotQueue()` excluye `isDone(lead)`. `renderQueueList()` usa
   `lastRunStatus[lead.id]` y puede mostrar un éxito/tiempo antiguo con llamadas nuevas.
6. Revisar también `isDone`, `docStatus`, `setDone`, `importBotResults`,
   `importSnapshots`, `saveProgress`, `saveSelection`, `runBot`, recuperación local
   y eventos de quitar/limpiar/reiniciar para evitar caminos alternativos del defecto.

En Python:

- `run_document_queue.py`: `result_entry`, `record_result`, `main`, `verify_saved_value`.
  El resultado guarda cantidad de intentos pero no sus identidades; se reemplaza por
  `lead_id`. La verificación compara el texto esperado, pero no resuelve la asociación
  errónea que hace la UI con otra tanda.
- `snapshot_store.py`: `record_snapshot` conserva último texto/hash/fecha por Lead;
  eso no prueba que todas las llamadas de cualquier CSV estén documentadas.
- `comment_writer.py`: `compose_attempts` agrega todos los intentos recibidos, sin
  deduplicarlos contra lo existente. Calcular el próximo INT no evita duplicados.
- `queue_loader.py`, `ui_server.py`: validar contratos, límites de directorio,
  endpoints de cola y `/run`, concurrencia y creación de procesos.
- `run_corrections.py`, `correction_loader.py`, `productivity_metrics.py` y sus tests:
  adaptar compatibilidad, invalidación de evidencias y conteos sin romper los flujos.

### Paso 0 — Preservar el estado y fijar una línea base

- [ ] Leer `AGENTS.md`, esta sección y los artefactos OpenSpec existentes.
- [ ] Consultar estado del servidor sin lanzar el bot. Si hay una tanda activa,
      no detenerla ni reemplazar archivos: coordinar con el usuario antes de continuar.
- [ ] Hacer un respaldo local fechado, no destructivo y fuera del ZIP/Git, de cola,
      resultados, métricas y snapshots. Verificar hashes/conteos del respaldo.
- [ ] Preservar también estado de ESTA app en el navegador (progreso por CSV,
      selección y recuperación). Si no puede obtenerse sin alterar el estado,
      pedir ayuda al usuario; no inspeccionar cookies ni credenciales del perfil.
- [ ] Registrar tests/lint actuales y problemas preexistentes. No considerar 138 u
      otro conteo histórico como resultado de la suite actual.

### Paso 1 — Formalizar contrato y escenarios antes de implementar

- [ ] Proponer un cambio OpenSpec separado, sugerido:
      `corregir-documentacion-por-intento`. Este nombre es una propuesta; sus
      artefactos todavía NO fueron creados por este handoff.
- [ ] Redactar proposal/design/spec/tasks, revisar coherencia con
      `documentar-automatico-guardado` y `medir-productividad-documentacion`, obtener
      aprobación del plan según AGENTS y validar con OpenSpec antes del código.
      En la investigación `openspec` no estaba en PATH; verificar instalación/PATH
      antes de intentar reinstalar. No afirmar validación si no se pudo ejecutar.
- [ ] Definir esquema versionado de ejecución y evidencia: `run_id`, identidad de
      Lead, IDs de llamadas, huella de los intentos solicitados, IDs confirmados,
      IDs realmente agregados y fecha de verificación. La huella debe ser
      determinista y cubrir resultado traducido/fecha/hora/ID, no solo cantidad.
- [ ] Mantener `call_id` como string opaco (puede tener punto y ceros). Identidad
      mínima `(lead_id, call_id)`; no convertir a número ni comparar subcadenas.
- [ ] Fijar cómo se representa `pendiente`, `parcial`, `guardado`, `ya_documentado`,
      `revision`, `error`, `duplicado` e `historico`; nombres finales en el spec.
      `guardado` significa escritura verificada; `ya_documentado` lectura confirmada
      sin nueva escritura. Un éxito histórico no equivale a éxito de la tanda actual.
- [ ] Conservar contratos de resultados/snapshots antiguos como solo históricos.
      No inventar call IDs ni asignarles el `run_id` actual. Un `corregido` genérico
      tampoco confirma automáticamente llamadas nuevas.

### Paso 2 — Escribir primero pruebas que reproduzcan el incidente

- [ ] Probar ejecución real de funciones JS, no solo buscar cadenas en el HTML.
      Aprovechar harness existente; si no cubre JS, añadir pruebas aisladas con
      Node y mocks de DOM/storage/fetch, integradas en verificación y CI.
- [ ] Fixture ficticia: Lead con llamadas A/B históricas y CSV nuevo C/D; resultado
      y snapshot A/B no deben completar C/D ni retirarlas de la selección/cola.
- [ ] Cubrir cada entrada: polling, importación manual, recuperación tras F5,
      cambio de CSV, misma cantidad de intentos pero otros IDs, y resultados fuera de orden.
- [ ] Snapshot antiguo + error/duplicado reciente no debe convertir el Lead a done.
- [ ] Desmarcar estado o volver a la lista no debe reintroducir confirmaciones
      históricas. Una instantánea de texto por sí sola nunca confirma el lote actual.
- [ ] Tests Python en módulos de cola, runner, escritor, servidor, snapshots,
      correcciones y métricas; usar `TemporaryDirectory`, nunca archivos operativos.

### Paso 3 — Corregir el modelo y la migración de la UI

- [ ] Derivar pendientes/confirmados por llamada y versión del contenido. Dejar de
      usar un booleano `done` por Lead como única autoridad.
- [ ] Separar texto histórico visible de evidencia que confirma intentos actuales.
      `applySnapshot` no debe poner done incondicionalmente.
- [ ] Aplicar resultados a su ejecución y conjunto de intentos; ignorar eventos
      antiguos o no asociados para el estado del lote activo. Mantener historial
      consultable con fecha, no badge verde/tiempo de la nueva tanda.
- [ ] Exportar solo intentos elegibles, sin borrar selección por recibir historial.
      Cambios de traducción/contenido para un mismo ID requieren revisión/corrección,
      no agregar la llamada por segunda vez.
- [ ] Versionar almacenamiento local y migrar sin borrar: conservar progreso manual,
      selección, snapshots y borradores; clasificar evidencias antiguas como históricas
      o pendientes de validación. No lanzar bot ni reescribir cola durante la migración.
- [ ] Marca manual de documentado: asociarla a los intentos mostrados en ese momento,
      distinguir declaración del usuario de verificación del bot; futuros intentos
      del mismo Lead no heredan la marca. Copiar al portapapeles no implica guardar.
- [ ] No sobrescribir borradores editados ni perder selección al recargar/limpiar
      documentados/cambiar de vista. Pruebas de regresión para cada acción.

### Paso 4 — Hacer idempotente el runner contra Salesforce

- [ ] Leer el campo actual ANTES de abrir el editor y contrastar IDs exactos de
      llamada con los intentos solicitados. Mantener comparación de IDs como strings.
- [ ] Todos presentes y consistentes: no abrir editor ni pulsar Guardar; registrar
      confirmación `ya_documentado` para esas llamadas y evidencia actual.
- [ ] Algunos presentes: componer solo faltantes, preservando íntegro el historial;
      numerar desde el último INT real de Salesforce.
- [ ] ID vacío/malformado, repetido con contenido contradictorio, o comentario
      manual posiblemente equivalente sin ID: `revision`, sin escritura automática.
      No deducir identidad solo por número INT o cantidad; no borrar comentarios.
- [ ] Duplicados idénticos del mismo call ID en la entrada se procesan una sola vez;
      un ID presente con resultado diferente requiere revisión, no otro INT.
- [ ] Si la lectura falla, nunca interpretar como campo vacío. Mantener controles
      existentes de editor, Guardar activo, esperas y comparación del valor esperado.
- [ ] Confirmar cobertura únicamente tras lectura/verificación exitosa. Guardar el
      snapshot a partir de la misma evidencia verificada o comprobar que una lectura
      adicional coincide; no publicar éxito con un snapshot distinto.
- [ ] No es necesario rediseñar esperas de Lightning para resolver este incidente;
      no reducir controles de persistencia por rendimiento.

### Paso 5 — Congelar tandas y enlazar resultados

- [ ] En `/run`, bajo exclusión mutua con PUT de cola y otras ejecuciones, validar y
      copiar la selección a una cola inmutable identificada por `run_id`.
      El runner procesa esa copia, no el archivo mutable de la UI.
- [ ] Un PUT concurrente no puede alterar una ejecución activa. Especificar rechazo
      explícito o edición de un borrador para la siguiente tanda; nunca mezcla silenciosa.
- [ ] Asociar resultados, snapshots y métricas al mismo `run_id`. Usar escrituras
      atómicas y evitar pérdida de historial entre tandas concurrentes.
- [ ] El polling de resultados no debe reescribir la cola como efecto secundario.
      Evitar doble inicio y carreras de petición, incluso con dos pestañas abiertas.
- [ ] Si guardar/validar la cola falla, `runBot` debe abortar antes de POST `/run`:
      no ejecutar accidentalmente una cola anterior.
- [ ] Mantener endpoints restringidos a localhost, token requerido y rutas internas
      conocidas; no aceptar comandos ni paths arbitrarios del cliente.
- [ ] Conservar uso por CLI y modo file:// según contrato aprobado, adaptando
      explícitamente resultados/importaciones; no arreglar solo el modo HTTP.

### Paso 6 — Integración y validación de no regresión

- [ ] Llamadas ya añadidas manualmente CON IDs: cero escritura. Si no hay IDs,
      revisión explícita antes de decidir; no probar con los 22 afectados reales.
- [ ] Repetir misma tanda/CSV: cero duplicados. CSV con mezcla antigua/nueva:
      solo se agregan nuevas llamadas verificablemente ausentes.
- [ ] Error después de Guardar y antes de resultado local: el reintento lee Salesforce
      y no vuelve a agregar lo que ya persistió.
- [ ] Error/resultado ajeno + snapshot anterior: estado actual no se oculta.
- [ ] Dos pestañas, polling en vuelo, recarga y reinicio del servidor: ninguna mezcla
      de ejecuciones ni borrado de selección. Evitar respuestas de un CSV anterior
      que se apliquen al CSV cargado posteriormente.
- [ ] Métricas separan escritos, ya existentes, revisión y error; tiempos verdes
      solo pertenecen a la ejecución correspondiente, sin heredar valores antiguos.
- [ ] Ejecutar suite completa Python + tests funcionales JS + lint + contratos +
      OpenSpec + `git diff --check`. Una comprobación sintáctica JS no sustituye
      las pruebas funcionales. No debilitar tests de seguridad o privacidad.

Comandos verificados en la configuración de CI al preparar este traspaso:

```powershell
# Desde automation_salesforce, con dependencias del harness disponibles:
python -m unittest discover -s tests -v
python -m ruff check . --select E4,E7,E9,F
python harness.py business-contracts
# Desde la raíz, con CLI disponible:
openspec validate --changes
git diff --check
```

Para Node, el runtime local conocido es
`C:\Users\ax24611\Downloads\_dev\tools\node-v24.21.0-win-x64\node.exe`;
verificar que sigue disponible y documentar el comando de pruebas JS que se adopte.
No instalar dependencias ni alterar configuración del proyecto sin revisar el harness.

### Paso 7 — Distribución y entrega

- [ ] Actualizar fuente y TODOS los módulos runtime necesarios en el paquete, no
      solamente HTML/servidor. Mantener Python embebido, Selenium y `_pth` válidos.
- [ ] Generar ZIP limpio, excluyendo datos operativos, respaldos, perfiles, sesiones,
      logs, CSV, presentaciones y gráficos. No comprimir ciegamente una carpeta usada.
- [ ] Extraer en ubicación nueva con espacios en el path; probar Python portátil,
      `INICIAR.bat`, servidor y misma instancia Edge para Salesforce/app. No ejecutar
      una tanda real ni cerrar el navegador de trabajo para una prueba técnica.
- [ ] Una actualización no debe reemplazar/borrar `queues`, `ui_output`, progreso
      del navegador ni el perfil de `%LOCALAPPDATA%`. Conservar respaldos y forma
      de revertir código sin volver a ejecutar tandas ni deshacer Salesforce.
- [ ] Revisar Graphify por cambios manuales antes de actualizarlo. Reportar pruebas,
      límites y archivos cambiados. No commitear/pushear sin autorización actual.
- [ ] Si se necesita piloto real, acordar una tanda nueva identificada y autorización
      explícita. Los 22 casos manualmente resueltos NO son una tanda de prueba.

### Criterio de terminado

Un Lead con A/B documentadas y C/D nuevas nunca aparece como `guardado` de C/D por
recibir historial de A/B. Una repetición del CSV no duplica llamadas ya guardadas.
La UI distingue historial, escritura verificada y confirmación sin escritura,
preserva selección/progreso y vincula cada estado/métrica a sus llamadas y ejecución.
Tests determinísticos, validación de spec y prueba de paquete deben pasar; registrar
cualquier bloqueo sin afirmar una validación que no se ejecutó.

---

## Material histórico (no usar como estado actual)

> Estado al 2026-09-17. El siguiente agente debe leer este documento, los
> artefactos OpenSpec del cambio activo y los módulos Python antes de tocar
> código. **Con `--auto` el bot pulsa Guardar y verifica releyendo; sin `--auto`
> el flujo sigue siendo supervisado (nunca guarda). Las correcciones solo
> escriben si el hash del campo coincide con la copia base.**

## 1. Cambios OpenSpec

| Cambio | Estado |
|---|---|
| `automatizar-lectura-salesforce` | Implementado y validado manualmente (pendiente solo archivo formal) |
| `escritura-asistida-salesforce` | Implementado; `run_comment_assisted.py` trata un único Lead. Falta prueba manual supervisada (tareas 1.3, 2.3, 3.2–3.4) |
| `ui-leads-ar-lead-qualif` | Archivado (2026-09-16). UI local de la bandeja `AR_LEAD_QUALIF` |
| `documentar-desde-html-supervisado` | Implementado en modo supervisado; absorbido parcialmente por el cambio automático |
| `documentar-automatico-guardado` | **En curso.** `--auto` guarda y verifica; UI con selección/estados/importación; correcciones con hash |

## 2. Flujo del cambio en curso

```text
HTML (vista DOCUMENTAR) → "Exportar cola para bot" → JSON en queues/
python open_persistent_browser.py            # una vez: Edge + login, queda abierto
python run_document_queue.py queues/cola_predictivo_<fecha>.json
  → se adjunta al navegador abierto (sin re-login) o abre uno propio
  → por Lead:
      abre /lightning/r/Lead/{id}/view → lee Otra información → próximo N INT real
      → métricas en consola → PREPARAR / s / q
      → carga el texto por JS en el editor (tabuladores preservados) → verifica
      → Enter tras decisión manual Guardar/Cancelar → siguiente Lead
  → queues/<cola>.resultado.json (preparado/omitido/error, actualizado por Lead)

Con --auto:
  prepara → save_edit_form (solo Guardar del formulario) → reabre el Lead →
  verify_saved_value (igualdad exacta) → 'guardado' | 'error'
  → snapshot privado en ui_output/<cola>.snapshots.json (field_value + sha256)

Correcciones:
  UI "Exportar correcciones" → ui_output/correcciones_*.json
    {lead_id, new_value, base_hash} solo de borradores editados
  python run_corrections.py ui_output/correcciones_*.json
    → relee Otra información; hash != base_hash → 'conflicto' (no escribe)
    → hash == base_hash → reemplaza, Guardar, relee, verifica → 'corregido'
    → actualiza el snapshot privado
```

## 3. Contratos clave

- **Cola JSON** (`buildBotQueue()` en el HTML → `queue_loader.load_queue()`):
  `{generated_at, source_file, leads:[{lead_id, attempts:[{result,date,time,call_id}]}]}`.
  Sin número INT, nombre ni teléfono. Solo Leads no documentados.
- **Numeración:** `next_attempt_number()` lee el último `N INT` real de
  Salesforce; el bot renumera desde ahí. El campo "Último N° en SF" del HTML no
  interviene.
- **Navegador persistente:** `create_driver(..., debugger_address)` se adjunta al
  Edge abierto por `open_persistent_browser.py` (puerto `debugger_address`,
  por defecto `127.0.0.1:9222`) si escucha; si no, abre uno propio.
  `release_driver()` solo cierra el navegador que el propio proceso lanzó.
  `prompt_for_manual_authentication()` detecta sesión activa y salta el login.
- **Composición:** `compose_attempts(historial, next_int, attempts)` →
  `historial.rstrip() + "\n" + líneas "N INT<TAB>resultado<TAB>fecha<TAB>hora<TAB>callId"`.
  Sin línea vacía: los intentos van en líneas consecutivas, como el historial real.
- **Escritura:** `replace_editor_value(driver, editor, texto)` usa
  `SET_EDITOR_VALUE_SCRIPT` (JS `value=` + eventos input/change). **Nunca**
  `send_keys` con `\t`: el TAB mueve el foco. `verify_editor_value` relee el
  control y la falla aborta sin reintentar.
- **Resultados:** `record_result()` deduplica por `lead_id` en
  `<cola>.resultado.json` y se escribe tras cada Lead.

## 4. Archivos del módulo

```
automation_salesforce/
├── browser_factory.py        detect_browser() + create_driver() (Edge visible, perfil dedicado,
│                             adjunción a navegador persistente + release_driver)
├── open_persistent_browser.py abre Edge con perfil dedicado + puerto de depuración; queda abierto
├── salesforce_session.py     config, login/2FA manual (omitido si hay sesión activa), wait_for_lightning_ready
├── local_audit.py            mask_lead_id, create_logger, capture_failure
├── report_reader.py          lectura de la bandeja (filtro AR_LEAD_QUALIF, scroll H/V, dedup por Lead ID)
├── leads_ui.py               genera la tabla HTML local (ui_output/, ignorado)
├── run_leads_ui.py           UI rápida; --completo recorre toda la bandeja
├── comment_reader.py         abre un Lead, lee Otra información, next_attempt_number
├── comment_writer.py         editor inline, compose_*, escritura por JS, verify_editor_value
├── queue_loader.py           valida la cola JSON exportada por el HTML
├── correction_loader.py      valida la cola de correcciones (lead_id, new_value, base_hash)
├── snapshot_store.py         snapshots privados de Otra información (ui_output/, sha256)
├── run_comment_read_only.py  lee Otra información de un Lead
├── run_comment_assisted.py   prepara un único Lead (borrador .txt en queues/)
├── run_document_queue.py     procesa la cola del HTML; --auto guarda y verifica
├── run_corrections.py        aplica correcciones solo si el hash del campo coincide
├── run_read_only.py          smoke de autenticación
├── run_report_read_only.py   instantánea JSON de la bandeja
├── local_report.py           escritura de instantáneas locales
└── tests/                    95 tests, todos sin navegador real
```

## 5. Configuración vigente (`config.json`, local e ignorado)

```json
{
  "browser": "edge",
  "profile_directory": "%LOCALAPPDATA%\\RenaultPredictivo\\edge-profile",
  "salesforce_url": "https://renaultarca.lightning.force.com",
  "report_url": "https://renaultarca.lightning.force.com/lightning/r/Report/00O67000006cstjEAA/view?queryScope=userFolders",
  "timeouts": {"page_load_seconds": 30, "authentication_seconds": 300},
  "screenshot_directory": "screenshots",
  "log_directory": "logs",
  "record_object_api_name": "Lead",
  "queue_directory": "queues",
  "ui_output_directory": "ui_output"
}
```

## 6. Restricciones que se mantienen

- Click automático permitido **solo** en: el lápiz de edición del campo y el
  botón Guardar del formulario de edición (vía `save_edit_form`, solo en
  `--auto` y correcciones). **Nunca** Cancelar, cierre, conversión,
  reasignación ni cambios de estado.
- Las correcciones escriben **solo** si el hash SHA-256 del campo actual
  coincide con `base_hash`; en caso contrario registran `conflicto` sin tocar
  Salesforce.
- **No automatizar 2FA ni credenciales.** Perfil dedicado; login manual.
- **Privacidad:** consola y logs solo métricas e IDs enmascarados. Jamás el
  texto del comentario, nombres, teléfonos ni emails. `config.json`, `logs/`,
  `screenshots/`, `profiles/`, `queues/`, `ui_output/` ignorados por Git.
  Los snapshots y las colas de corrección contienen texto del campo: solo en
  `ui_output/`, nunca en logs ni en `queues/*.resultado.json`.
- El operador ejecuta los runners desde PowerShell (usan `input()`).

## 7. Qué falta

1. Verificación supervisada en `--auto`: tanda pequeña → lote restante con
   aprobación explícita; importar resultado y snapshots en la UI.
2. Prueba supervisada de una corrección real y un conflicto controlado
   (verificar que el flujo manual sigue disponible).
3. Revisar logs/capturas/resultados: sin datos de clientes.
4. `graphify update .`, `openspec validate --changes`, commit autorizado.

## 8. Comandos

```powershell
cd C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce
python -m unittest discover -s tests          # 95/95 esperado
python -m ruff check . --select E4,E7,E9,F
python open_persistent_browser.py              # Edge autenticado persistente (una vez)
python run_leads_ui.py                         # UI de la bandeja (rápido)
python run_leads_ui.py --completo              # recorrido total (lunes)
python run_document_queue.py queues\<cola>.json            # supervisado
python run_document_queue.py --auto queues\<cola>.json     # guarda y verifica
python run_corrections.py ui_output\correcciones_<f>.json  # correcciones con hash
```
