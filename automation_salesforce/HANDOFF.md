# Handoff — automation_salesforce

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
