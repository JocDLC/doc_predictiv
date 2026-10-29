"""Servidor local mínimo para que la UI dispare el bot sin usar la terminal.

Escucha solo en ``127.0.0.1`` y exige un token aleatorio por sesión que la UI
lee de ``ui_output/bot_session.json`` con el permiso de carpeta que ya tiene.
Solo permite lanzar el runner de la cola activa: no ejecuta comandos
arbitrarios. Todo queda en la máquina local.
"""

from __future__ import annotations

import base64
import json
import os
import queue as queue_module
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from selenium.common.exceptions import WebDriverException

from browser_factory import (
    close_stuck_debugger_targets,
    create_driver,
    debugger_http_ready,
    debugger_is_listening,
    debugger_tab_targets,
    detect_browser,
    launch_persistent_browser,
    open_missing_tabs,
    release_driver,
    wait_for_debugger,
    wait_for_restored_tabs,
)
from closure_store import validate_close_queue
from country_fields import normalize_country
from distribucion_loader import parse_archivo, validate_distribucion_queue
from lead_monitor import _encargada_activa, run_cycle
from local_audit import mask_lead_id
from monitor_store import (
    MAX_RESULTS,
    PAUSE_FUERA_DE_HORARIO,
    PAUSE_RUN_ACTIVO,
    PAUSE_SESSION_LOST,
    PAUSE_SIN_BANDEJAS,
    STATUS_ERROR,
    STATUS_NO_VERIFICADO,
    STATUS_TOMADO,
    STATUS_TOMADO_POR_OTRO,
    STATE_FILE_NAME,
    clear_results,
    load_state,
    save_state,
    touch_cycle,
    validate_bandejas,
    validate_equipo,
    validate_schedule,
    within_schedule,
)
from queue_loader import load_queue_file

try:
    import msvcrt
except ImportError:  # fuera de Windows no hay lock de instancia
    msvcrt = None

ROOT = Path(__file__).parent


def load_config() -> dict:
    with (ROOT / "config.json").open(encoding="utf-8") as file:
        return json.load(file)


def local_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


SERVER_PORT = 8765
ACTIVE_QUEUE = "cola_activa.json"
ACTIVE_CLOSE_QUEUE = "cola_cierre_activa.json"
ACTIVE_DISTRIBUCION_QUEUE = "cola_distribucion_activa.json"
PARSE_MAX_BYTES = 30 * 1024 * 1024  # body base64 de la BD de leads (~22 MB de archivo)
SESSION_FILE = "bot_session.json"
UI_PAGE = ROOT.parent / "documentador_predictivo.html"
TOKEN_PLACEHOLDER = "__BOT_SERVER_TOKEN__"

# Archivos JSON que la UI lee/escribe a través del servidor. Solo estos nombres,
# siempre dentro de las carpetas operativas: nada de rutas arbitrarias.
API_FILES = {
    "/api/queue": ROOT / "queues" / "cola_activa.json",
    "/api/results": ROOT / "queues" / "cola_activa.resultado.json",
    "/api/metrics": ROOT / "queues" / "cola_activa.metricas.json",
    "/api/snapshots": ROOT / "ui_output" / "cola_activa.snapshots.json",
    "/api/close-queue": ROOT / "queues" / "cola_cierre_activa.json",
    "/api/close-results": ROOT / "queues" / "cola_cierre_activa.resultado.json",
    "/api/distribucion-queue": ROOT / "queues" / "cola_distribucion_activa.json",
    "/api/distribucion-results": ROOT / "queues" / "cola_distribucion_activa.resultado.json",
}
WRITABLE_API = {"/api/queue", "/api/close-queue", "/api/distribucion-queue"}

current_process: subprocess.Popen | None = None
# Identifica qué runner tiene la exclusión mutua: la UI muestra la operación
# activa y el reinicio del navegador se bloquea con cualquiera de las dos.
current_operation: str | None = None
# Serializa el congelado de la cola y el arranque del runner: un PUT o una
# segunda ejecución no pueden mezclarse con la tanda activa.
run_lock = threading.Lock()

# --- Monitor de Bandeja + canal de eventos ------------------------------------
# Si cambia, actualizar el texto fijo "~2 minutos" de documentador_predictivo.html
# (tarjeta de estado y texto explicativo del Monitor). Ver MEMORY.md.
MONITOR_INTERVAL_SECONDS = 120
# Serializa lecturas/escrituras de monitor_state.json entre el hilo del monitor
# y los endpoints de la UI.
monitor_lock = threading.Lock()
cycle_lock = threading.Lock()  # un solo ciclo del monitor a la vez (auto o manual)
monitor_cycle_active = False  # True mientras un ciclo ocupa el navegador
monitor_window_handle = None  # ventana dedicada del monitor (no pisa las del usuario)
monitor_driver = None  # sesión WebDriver del monitor, viva entre ciclos
# La RAM de Edge crece con las horas: reinicio programado del navegador
# dedicado cuando está ocioso (las pestañas se restauran solas).
AUTO_BROWSER_RESTART_SECONDS = 4 * 3600
browser_started_monotonic = time.monotonic()
# Auto-recuperación del navegador trabado: tantos ciclos seguidos sin
# conectar disparan el reinicio automático. El cooldown evita un bucle si
# el wedge sobrevive al reinicio recién hecho (manual, programado o auto).
AUTO_RESTART_AFTER_FAILURES = 3
AUTO_RESTART_COOLDOWN_SECONDS = 300
consecutive_browser_failures = 0
monitor_stop = threading.Event()
# Suscriptores SSE: cada uno es una queue.Queue; broadcast_event los alimenta.
event_subscribers: list[queue_module.Queue] = []
event_subscribers_lock = threading.Lock()
SSE_HEARTBEAT_SECONDS = 25
RUN_STATUS_POLL_SECONDS = 2


def monitor_state_path(config: dict) -> Path:
    return ROOT / config.get("ui_output_directory", "ui_output") / STATE_FILE_NAME


def ui_prefs_path(config: dict) -> Path:
    return ROOT / config.get("ui_output_directory", "ui_output") / "ui_prefs.json"


PREF_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
# Tope razonable para el archivo entero: solo guarda vistas de columnas y
# toggles, no datos.
UI_PREFS_MAX_BYTES = 64 * 1024


def read_ui_prefs(config: dict) -> dict:
    try:
        data = json.loads(ui_prefs_path(config).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_ui_prefs(config: dict, prefs: dict) -> None:
    path = ui_prefs_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(prefs, ensure_ascii=False), encoding="utf-8")
    os.replace(temp_path, path)


def acquire_instance_lock(ui_output_directory: Path):
    """Un solo ``ui_server`` por instalación.

    En Windows ``SO_REUSEADDR`` (activo en ``ThreadingHTTPServer``) permite
    que DOS procesos se bindeen al mismo puerto sin error: cada uno
    tendría su token y las peticiones caerían en cualquiera. El lockfile
    hace que la segunda instancia salga antes de bindear. Devuelve el
    handle abierto (mantenerlo referenciado conserva el lock) o None si
    ya hay otra instancia.
    """
    if msvcrt is None:
        return True  # plataforma sin lock: no bloquear el arranque
    ui_output_directory.mkdir(parents=True, exist_ok=True)
    handle = open(ui_output_directory / ".ui_server.lock", "a+b")
    handle.seek(0)  # el lock cubre el byte 0; en append el cursor queda al final
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return None
    return handle


def load_or_create_token(ui_output_directory: Path) -> str:
    """Token estable entre reinicios: una página abierta no queda vieja.

    Regenerarlo en cada arranque convertía cualquier reinicio (deploy,
    relanzado del guardián) en un 403 silencioso para la UI abierta. El
    token ya vive en ``bot_session.json`` con los permisos de la carpeta,
    así que persistirlo no expone nada nuevo.
    """
    session_path = ui_output_directory / SESSION_FILE
    try:
        saved = json.loads(session_path.read_text(encoding="utf-8"))
        token = str(saved.get("token") or "")
        if token:
            return token
    except (OSError, json.JSONDecodeError):
        pass
    return secrets.token_hex(16)


def _force_clean_exit() -> None:
    """exit(0): convención con el guardián para 'reinicio intencional'.

    ``/api/reload`` lo usa para recargar código sin contarse como caída.
    """
    monitor_stop.set()
    os._exit(0)


def monitor_read_state(config: dict) -> dict:
    with monitor_lock:
        return load_state(monitor_state_path(config))


def monitor_write_state(config: dict, state: dict) -> None:
    with monitor_lock:
        save_state(monitor_state_path(config), state)


def broadcast_event(payload: dict) -> None:
    """Empuja un evento a todas las UI suscritas por SSE."""
    with event_subscribers_lock:
        subscribers = list(event_subscribers)
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(payload)
        except Exception:  # noqa: BLE001 — un suscriptor roto no frena al resto
            pass


def windows_toast(title: str, message: str) -> None:
    """Toast nativo de Windows vía PowerShell; fire-and-forget, sin dependencias.

    ToastText04: título + hasta 3 líneas de cuerpo — una por lead.
    Título y líneas viajan por stdin para evitar problemas de quoting.
    """
    script = (
        "[Console]::InputEncoding=[System.Text.Encoding]::UTF8;"
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications,"
        " ContentType = WindowsRuntime] | Out-Null;"
        "$t=[Windows.UI.Notifications.ToastTemplateType]::ToastText04;"
        "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($t);"
        # Urgente: atraviesa 'No molestar' de Windows (banner + centro).
        "$x.DocumentElement.SetAttribute('scenario','urgent');"
        "$n=$x.GetElementsByTagName('text');"
        "0..3 | ForEach-Object {"
        " $n.Item($_).AppendChild($x.CreateTextNode([Console]::In.ReadLine())) | Out-Null };"
        "$app='{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app)"
        ".Show([Windows.UI.Notifications.ToastNotification]::new($x));"
    )
    try:
        lines = message.split("\n")[:3]
        lines += [""] * (3 - len(lines))
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", script],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",  # los emoji del toast no entran en cp1252
        ).communicate(
            input=f"{title}\n" + "\n".join(lines) + "\n", timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        pass  # el toast es best-effort: nunca debe frenar el ciclo


def _toast_contacto(details: dict) -> str:
    """Método de contacto elegido por el lead, para el toast."""
    pref = str((details or {}).get("preferencia_contacto") or "").strip().lower()
    if "whatsapp" in pref:
        return "💬 WhatsApp"
    if any(key in pref for key in ("llamad", "llamar", "phone", "tel")):
        return "📞 Llamada"
    return ""


def _lead_toast_lines(events: list, pre_results: dict) -> list:
    """Una línea por lead relevante del ciclo.

    ✅ tomado — a quién quedó asignado (el toast no admite color de texto;
    el emoji es el indicador verde/rojo); ❌/⚠️ errores de la toma;
    🔔 detectado nuevo con nombre y bandeja. Los resultados sin
    cambio respecto del ciclo anterior no vuelven a sonar.
    """
    lines = []
    for event in events:
        if event.get("type") != "lead_result":
            continue
        entry = event.get("entry") or {}
        status = event.get("status")
        lead_id = entry.get("lead_id")
        details = entry.get("details") or {}
        nombre = " ".join(
            part
            for part in (
                str(details.get("nombre") or "").strip(),
                str(details.get("apellido") or "").strip(),
            )
            if part
        ) or mask_lead_id(lead_id)
        contacto = _toast_contacto(details)
        extra = f" · {contacto}" if contacto else ""
        changed = lead_id and (pre_results.get(lead_id) or {}).get("status") != status
        if status == STATUS_TOMADO:
            asignado = str(entry.get("asignado_a") or "").strip() or "tu usuario"
            lines.append(f"✅ {nombre} → {asignado}{extra}")
        elif not lead_id or not changed:
            continue
        elif status == STATUS_ERROR:
            lines.append(f"❌ {nombre} — error{extra}")
        elif status == STATUS_NO_VERIFICADO:
            lines.append(f"⚠️ {nombre} — no verificado{extra}")
        elif status == STATUS_TOMADO_POR_OTRO:
            lines.append(f"👤 {nombre} — lo tomó otra persona{extra}")
        else:
            # Detectado nuevo: una línea por lead con nombre y bandeja.
            lines.append(f"🔔 {nombre} — nuevo en {event.get('bandeja')}{extra}")
    return lines


def monitor_tick(config: dict, force: bool = False) -> list[dict]:
    """Un ciclo del monitor bajo el lock: nunca corren dos ciclos a la vez."""
    with cycle_lock:
        _maybe_restart_browser(config)
        return _monitor_cycle(config, force)


def _maybe_restart_browser(config: dict) -> None:
    """Reinicio periódico del navegador dedicado: la RAM de Edge crece con
    las horas de sesión; el reinicio la libera y las pestañas se restauran.
    Solo ocurre ocioso — monitor_tick ya tiene el lock de ciclo y se salta
    si hay una cola de documentación/cierre corriendo."""
    global browser_started_monotonic
    if current_process is not None and current_process.poll() is None:
        return
    if time.monotonic() - browser_started_monotonic < AUTO_BROWSER_RESTART_SECONDS:
        return
    print("[monitor] reinicio programado del navegador (RAM)", flush=True)
    restart_browser(config)


def _note_browser_failure(failed: bool, config: dict) -> None:
    """Cuenta ciclos seguidos con el puerto de depuración trabado y, al
    llegar al umbral, reinicia el navegador dedicado automáticamente.

    Corre dentro del lock de ciclo: el reinicio no pisa otro ciclo ni una
    cola activa (``PAUSE_RUN_ACTIVO`` ni siquiera intenta el attach, así
    que el contador se reinicia y no dispara). El cooldown comparte
    ``browser_started_monotonic`` con los reinicios manual y programado:
    si el navegador se acaba de reiniciar y sigue trabado, no se insiste
    en bucle — queda el pausado visible hasta el próximo intento.
    """
    global consecutive_browser_failures
    consecutive_browser_failures = consecutive_browser_failures + 1 if failed else 0
    if not failed or consecutive_browser_failures < AUTO_RESTART_AFTER_FAILURES:
        return
    if time.monotonic() - browser_started_monotonic < AUTO_RESTART_COOLDOWN_SECONDS:
        return
    print(
        f"[monitor] {consecutive_browser_failures} ciclos sin conectar al navegador: "
        "reinicio automático",
        flush=True,
    )
    consecutive_browser_failures = 0
    try:
        restart_browser(config)
    except Exception as error:  # noqa: BLE001 — el próximo ciclo lo vuelve a intentar
        print(f"[monitor] reinicio automático falló: {error}", flush=True)


def start_manual_check(config: dict) -> bool:
    """Dispara una revisión manual inmediata. False si ya hay un ciclo corriendo."""
    if not cycle_lock.acquire(blocking=False):
        return False

    def run() -> None:
        try:
            _monitor_cycle(config, force=True)
        finally:
            cycle_lock.release()

    threading.Thread(target=run, daemon=True).start()
    return True


def _adopt_restored_monitor_window(driver, debugger_address: str | None, adopt_urls: list[str]) -> str | None:
    """Ubica la ventana del monitor que la restauración de sesión recuperó.

    Tras reiniciar el navegador, el handle guardado ya no existe pero la
    ventana del monitor reaparece en ``/json/list`` con la última URL que
    visitó (un reporte, o un Lead si el ciclo terminó en un Pick Up). El
    ``id`` del target CDP coincide con el window handle de WebDriver (a
    veces con prefijo ``CDwindow-``). ``adopt_urls`` se recorre en orden de
    preferencia y solo se adoptan URLs exactas — nunca una pestaña de
    Salesforce que el usuario haya abierto a mano con otra página.
    """
    if not debugger_address or not adopt_urls:
        return None
    url_to_target = {target["url"]: target["id"] for target in debugger_tab_targets(debugger_address)}
    work_tab = getattr(driver, "bot_work_tab_handle", None)
    for url in adopt_urls:
        target_id = url_to_target.get(url)
        if not target_id:
            continue
        for handle in driver.window_handles:
            if handle != work_tab and handle.removeprefix("CDwindow-") == target_id:
                return handle
    return None


def _close_tab_without_focus(driver, handle: str, debugger_address: str | None) -> bool:
    """Cierra una pestaña por CDP (``Target.closeTarget``) sin activarla.

    La vía clásica ``switch_to.window`` + ``close`` dispara
    ``Page.bringToFront`` y le roba el foco de Windows al usuario cada
    ciclo — el problema reportado en notebooks de una sola pantalla.
    """
    if not debugger_address:
        return False
    target_id = handle.removeprefix("CDwindow-")
    try:
        for target in debugger_tab_targets(debugger_address):
            if target.get("id") == target_id:
                driver.execute_cdp_cmd("Target.closeTarget", {"targetId": target_id})
                return True
    except (WebDriverException, AttributeError, KeyError, TypeError):
        pass
    return False


def ensure_monitor_window(
    driver,
    adopt_urls: list[str] | None = None,
    debugger_address: str | None = None,
) -> str:
    """Devuelve la ventana dedicada del monitor, activa solo si hace falta.

    El ciclo navega con ``driver.get`` sobre la ventana seleccionada: con una
    ventana propia el usuario puede seguir usando las demás pestañas del
    navegador del bot mientras el monitor trabaja. La ventana se crea una
    sola vez y se reutiliza entre ciclos; si el navegador se reinició, se
    adopta la ventana restaurada por la sesión en vez de abrir una duplicada.
    La pestaña en blanco que abre ``create_driver`` al adjuntarse se cierra
    para no acumularlas.

    Foco de Windows: cada ``switch_to.window`` dispara ``Page.bringToFront``
    y saca la ventana al frente — en notebooks de una pantalla era cansador.
    Por eso el switch solo se hace cuando el handle activo NO es el del
    monitor, y las pestañas auxiliares se cierran por CDP sin activarlas.
    """
    global monitor_window_handle
    work_tab = getattr(driver, "bot_work_tab_handle", None)
    if not (monitor_window_handle and monitor_window_handle in driver.window_handles):
        adopted = _adopt_restored_monitor_window(driver, debugger_address, adopt_urls or [])
        monitor_window_handle = adopted
    if monitor_window_handle and monitor_window_handle in driver.window_handles:
        if driver.current_window_handle != monitor_window_handle:
            driver.switch_to.window(monitor_window_handle)
    else:
        try:
            driver.switch_to.new_window("window")
        except WebDriverException:
            driver.switch_to.new_window("tab")
        monitor_window_handle = driver.current_window_handle
        # La ventana tiene que quedar visible (minimizada la grilla virtual
        # de Salesforce no renderiza), pero no maximizada tapando el trabajo.
        try:
            driver.set_window_rect(x=60, y=60, width=1150, height=760)
        except WebDriverException:
            pass
    if work_tab and work_tab != monitor_window_handle and work_tab in driver.window_handles:
        if not _close_tab_without_focus(driver, work_tab, debugger_address):
            try:
                driver.switch_to.window(work_tab)
                driver.close()
            except WebDriverException:
                pass
        # Tras cerrar pestañas el handle activo puede quedar huérfano; solo
        # se vuelve al monitor si el switch es realmente necesario.
        try:
            on_monitor = driver.current_window_handle == monitor_window_handle
        except WebDriverException:
            on_monitor = False
        if not on_monitor:
            driver.switch_to.window(monitor_window_handle)
    return monitor_window_handle


def _merge_cycle_state(config: dict, state: dict, pre_results: dict) -> dict:
    """Estado a persistir al cerrar un ciclo.

    El ciclo lee el estado al arrancar y corre decenas de segundos: escribir
    ese dict completo pisaría cambios hechos por el usuario mientras tanto
    (toggle, modo prueba, bandejas, franjas, "Limpiar lista"). Se relee el
    disco y solo se aplican los campos que el ciclo produjo: ciclo/pausa,
    ``monitor_url`` y las entradas de resultados nuevas o actualizadas.
    """
    fresh = monitor_read_state(config)
    fresh["last_cycle_at"] = state.get("last_cycle_at")
    fresh["paused_reason"] = state.get("paused_reason")
    if state.get("monitor_url"):
        fresh["monitor_url"] = state["monitor_url"]
    if state.get("bot_owner"):
        fresh["bot_owner"] = state["bot_owner"]
    disk_results = {r.get("lead_id"): r for r in fresh.get("results", []) if r.get("lead_id")}
    order = [r.get("lead_id") for r in fresh.get("results", []) if r.get("lead_id")]
    for result in state.get("results", []):
        lead_id = result.get("lead_id")
        # Sin cambio respecto del inicio del ciclo: si el usuario la limpió,
        # no se resucita. Nuevas o actualizadas sí se registran.
        if lead_id and result != pre_results.get(lead_id) and disk_results.get(lead_id) != result:
            if lead_id not in disk_results:
                order.append(lead_id)
            disk_results[lead_id] = result
    fresh["results"] = [disk_results[lead_id] for lead_id in order][-MAX_RESULTS:]
    return fresh


def _monitor_driver(config: dict, browser: str, executable: Path, debugger_address: str):
    """Sesión WebDriver reutilizada entre ciclos del monitor.

    Cada attach cuesta una ``NEW_SESSION`` y levanta un chromedriver; ~60
    por hora contribuían a trabar el puerto de depuración. Una sesión viva
    se sondea con ``current_url`` y solo se recrea cuando dejó de
    responder.
    """
    global monitor_driver
    if monitor_driver is not None:
        try:
            _ = monitor_driver.current_url
            return monitor_driver
        except Exception:  # noqa: BLE001 — sesión muerta: se descarta y recrea
            _drop_monitor_driver()
    monitor_driver = create_driver(
        browser, executable, local_path(config["profile_directory"]), debugger_address
    )
    return monitor_driver


def _drop_monitor_driver() -> None:
    """Descarta la sesión persistente (navegador reiniciado o sesión muerta)."""
    global monitor_driver
    driver, monitor_driver = monitor_driver, None
    if driver is not None:
        release_driver(driver, close_tab=False)


def _turno_propio_activo(state: dict, bandejas: set | None = None) -> bool:
    """La franja del monitor (del usuario logueado) cubre ahora. Vacía NO
    cuenta: los leads solo se toman dentro de franjas configuradas.
    ``bandejas`` exige además que la franja cubra alguna de esas bandejas
    — una franja sin bandejas tildadas vale para todas."""
    schedule = state.get("schedule")
    if not schedule:
        return False
    return within_schedule(schedule, bandeja=bandejas)


def _bandeja_codes_disponibles(state: dict) -> set:
    """Bandejas utilizables por una franja: habilitadas Y con link de
    reporte. La validación de bandejas ya exige link para habilitar, pero
    el chequeo de URL blinda estados viejos o escritos a mano."""
    return {
        b.get("code")
        for b in state.get("bandejas") or []
        if b.get("enabled") and b.get("url")
    }


def _franjas_con_bandeja_no_disponible(state: dict, franjas: list) -> set:
    """Códigos de bandeja que las franjas pretenden cubrir pero que no
    están disponibles: una franja solo puede cargarse sobre bandejas
    habilitadas con link."""
    return {
        code for slot in franjas for code in slot.get("bandejas") or []
    } - _bandeja_codes_disponibles(state)


def _any_turno_activo(state: dict) -> bool:
    """Alguna franja permite tomar leads: la del monitor (a nombre del
    usuario logueado) o la de una persona del equipo cuya franja cubra
    alguna bandeja habilitada. Una franja sin cobertura sobre las bandejas
    encendidas —propia o de equipo— no habilita la toma en ellas.
    """
    enabled_codes = _bandeja_codes_disponibles(state)
    if _turno_propio_activo(state, enabled_codes or None):
        return True
    if not enabled_codes:
        # Sin bandejas encendidas el pause sin_bandejas decide después.
        return _encargada_activa(state.get("equipo")) is not None
    return _encargada_activa(state.get("equipo"), bandeja=enabled_codes) is not None


def _monitor_cycle(config: dict, force: bool = False) -> list[dict]:
    """Cuerpo del ciclo. ``force`` ignora el toggle (revisión manual) pero
    las franjas se respetan siempre: sin turno vigente el ciclo corre en
    modo prueba — lista ``detectado`` sin tocar el lead."""
    state = monitor_read_state(config)
    pre_results = {r.get("lead_id"): r for r in state.get("results", []) if r.get("lead_id")}
    if not force and not state["enabled"]:
        return []
    turno_activo = _any_turno_activo(state)
    pause_reason = None
    if current_process is not None and current_process.poll() is None:
        pause_reason = PAUSE_RUN_ACTIVO
    elif not force and not turno_activo:
        pause_reason = PAUSE_FUERA_DE_HORARIO
    elif not any(b["enabled"] for b in state["bandejas"]):
        pause_reason = PAUSE_SIN_BANDEJAS
    if pause_reason:
        touch_cycle(state, pause_reason)
        monitor_write_state(config, state)
        return []
    if force and not turno_activo:
        # Revisión manual sin turno vigente: nunca toca leads — corre en
        # modo prueba y los lista como `detectado` (reprocesables cuando
        # una franja quede activa). No se persiste el flag.
        state["solo_listar"] = True
    timeout_seconds = int(config.get("timeouts", {}).get("page_load_seconds", 30))
    driver = None
    global monitor_cycle_active
    try:
        monitor_cycle_active = True
        broadcast_event({"type": "monitor", "status": "cycle_start"})
        browser, executable = detect_browser(config["browser"])
        debugger_address = config.get("debugger_address", "127.0.0.1:9222")
        driver = _monitor_driver(config, browser, executable, debugger_address)
        # monitor_url primero: tras un Pick Up la ventana queda en el Lead,
        # no en el reporte — es la pista más precisa para adoptarla.
        adopt_urls = [state["monitor_url"]] if state.get("monitor_url") else []
        adopt_urls += [b["url"] for b in state["bandejas"] if b.get("enabled") and b.get("url")]
        ensure_monitor_window(driver, adopt_urls=adopt_urls, debugger_address=debugger_address)
        # diag_dir: screenshots de "sin_panel" van a ui_output para revisión.
        diag_dir = ROOT / config.get("ui_output_directory", "ui_output")
        events = run_cycle(driver, config, state, timeout_seconds, diag_dir=diag_dir)
        # La URL final (reporte o Lead tras un Pick Up) identifica la ventana
        # si el navegador se reinicia y la restauración la recupera.
        if getattr(driver, "current_url", None):
            state["monitor_url"] = driver.current_url
        touch_cycle(state)
        _note_browser_failure(False, config)
    except Exception as error:  # noqa: BLE001 — un ciclo fallido espera al siguiente
        reason = (
            "navegador_trabado"
            if "navegador" in str(error) or "depuraci" in str(error)
            else f"error:{type(error).__name__}"
        )
        touch_cycle(state, reason)
        print(f"[monitor] ciclo falló ({reason}): {error}", flush=True)
        events = [{"type": "cycle_error", "error": type(error).__name__, "reason": reason}]
        _note_browser_failure(reason == "navegador_trabado", config)
    finally:
        monitor_cycle_active = False
        broadcast_event({"type": "monitor", "status": "cycle_end"})
        # Sin release_driver: la sesión del monitor sobrevive entre ciclos.
        # Si falló en este ciclo, el próximo la sondea y la recrea.
    if any(e.get("type") == PAUSE_SESSION_LOST for e in events):
        touch_cycle(state, PAUSE_SESSION_LOST)
    monitor_write_state(config, _merge_cycle_state(config, state, pre_results))
    # Toast nativo: una línea por lead — ✅ a quién quedó asignado,
    # ❌/⚠️ si hubo error, 🔔 detectados nuevos — con el método de
    # contacto elegido cuando el lead lo declara. Sin cambio no re-suena.
    lines = _lead_toast_lines(events, pre_results)
    if lines and state.get("notificar", True):
        shown = lines if len(lines) <= 3 else lines[:2] + [f"… y {len(lines) - 2} lead(s) más"]
        windows_toast("Monitor de Bandeja", "\n".join(shown))
    for event in events:
        if event.get("type") == "lead_result":
            entry = event.get("entry") or {}
            print(
                f"[monitor] {event.get('bandeja')} lead {mask_lead_id(entry.get('lead_id'))}"
                f" -> {event.get('status')}"
                + (f" (finalización: {entry['finalizacion']})" if entry.get("finalizacion") else ""),
                flush=True,
            )
        elif event.get("type") == "bandeja_error":
            # Hoy solo iba por SSE: sin log la bandeja caída era invisible.
            print(
                f"[monitor] {event.get('bandeja')} bandeja_error: {event.get('error')}",
                flush=True,
            )
        elif event.get("type") == "bandeja_scan":
            # Resumen de la lectura: si "sin asignar" queda en 0 con filas
            # visibles, los propietarios vistos delatan un nombre de cola
            # mal configurado (o que la bandeja no tiene QUALIF ahora).
            owners = ", ".join(event.get("owners_seen") or [])
            skipped = event.get("skipped_status")
            print(
                f"[monitor] {event.get('bandeja')} bandeja: {event.get('rows')} filas, "
                f"{event.get('unassigned')} sin asignar ({event.get('unassigned_owner')})"
                + (f" | propietarios vistos: {owners}" if not event.get("unassigned") and owners else "")
                + (f" | {skipped} omitidos por estado" if skipped else ""),
                flush=True,
            )
        broadcast_event({"type": "monitor", **event})
    return events


def monitor_loop(config: dict, stop: threading.Event) -> None:
    """Un tick por intervalo hasta que el servidor se detenga."""
    interval = float(config.get("monitor_interval_seconds") or MONITOR_INTERVAL_SECONDS)
    while not stop.wait(interval):
        monitor_tick(config)


def run_status_watcher(stop: threading.Event) -> None:
    """Emite un evento cuando un run de documentación/cierre termina.

    Reemplaza el polling de la UI: el estado del bot llega por SSE en el momento
    del cambio en vez de releerse cada pocos segundos.
    """
    was_running = current_process is not None and current_process.poll() is None
    while not stop.wait(RUN_STATUS_POLL_SECONDS):
        running = current_process is not None and current_process.poll() is None
        if was_running and not running:
            broadcast_event(
                {
                    "type": "run_finished",
                    "operation": current_operation,
                    "exit_code": None if current_process is None else current_process.returncode,
                }
            )
        was_running = running


def app_version() -> str:
    """Versión de la app: única fuente ``APP_VERSION`` en la página principal."""
    try:
        match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', UI_PAGE.read_text(encoding="utf-8"))
    except OSError:
        match = None
    return match.group(1) if match else "desconocida"


def freeze_queue(active_path: Path, frozen_path: Path, run_id: str) -> Path:
    """Copia una cola activa a un archivo inmutable identificado por ``run_id``.

    El runner trabaja sobre esa copia: un ``PUT`` posterior solo prepara el
    borrador de la próxima tanda sin alterar la ejecución en curso.
    """
    try:
        payload = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    frozen = {
        **payload,
        "run_id": run_id,
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    frozen_path.write_text(json.dumps(frozen, indent=2, ensure_ascii=False), encoding="utf-8")
    return frozen_path


def freeze_active_queue(queue_directory: Path, run_id: str) -> Path:
    """Congela la cola de documentación activa (``cola_activa.json``)."""
    return freeze_queue(queue_directory / ACTIVE_QUEUE, queue_directory / f"{run_id}.json", run_id)


def freeze_active_close_queue(queue_directory: Path, run_id: str) -> Path:
    """Congela la cola de cierre activa (``cola_cierre_activa.json``)."""
    return freeze_queue(
        queue_directory / ACTIVE_CLOSE_QUEUE,
        queue_directory / f"cierre_{run_id}.json",
        run_id,
    )


def freeze_active_distribucion_queue(queue_directory: Path, run_id: str) -> Path:
    """Congela la cola de distribución activa (``cola_distribucion_activa.json``)."""
    return freeze_queue(
        queue_directory / ACTIVE_DISTRIBUCION_QUEUE,
        queue_directory / f"distribucion_{run_id}.json",
        run_id,
    )


def find_listening_pid(port: str) -> str | None:
    """Devuelve el PID que escucha en el puerto local indicado, si existe."""
    try:
        output = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3].upper() == "LISTENING" and parts[1].endswith(f":{port}"):
            return parts[4]
    return None


def dedicated_profile_pids(profile_directory: Path) -> list[str]:
    """PIDs de msedge.exe/chrome.exe corriendo con el ``--user-data-dir`` dedicado.

    Cubre el caso de un navegador del perfil vivo pero sin escuchar el puerto
    esperado (p. ej. uno lanzado por WebDriver con ``--remote-debugging-port=0``):
    la búsqueda por puerto no lo ve y el reinicio quedaría con dos instancias
    sobre el mismo perfil (el segundo arranque falla por el lock).
    """
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -and ($_.Name -eq 'msedge.exe' -or $_.Name -eq 'chrome.exe') } | "
        "ForEach-Object { \"$($_.ProcessId)|$($_.CommandLine)\" }"
    )
    try:
        output = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    needle = os.path.normcase(os.path.normpath(str(profile_directory)))
    pids = []
    marker = re.compile(r"--user-data-dir=(?:\"([^\"]+)\"|'([^']+)'|(\S+))")
    for line in output.splitlines():
        pid_text, _, command_line = line.partition("|")
        match = marker.search(command_line)
        if not match:
            continue
        raw_profile = next(group for group in match.groups() if group)
        profile = os.path.normcase(os.path.normpath(raw_profile.strip()))
        if profile == needle and pid_text.strip().isdigit():
            pids.append(pid_text.strip())
    return pids


def _attach_session_once(config: dict, debugger_address: str) -> str:
    """Una sonda de adjunte: ``ok``, ``transient`` o ``wedged``.

    El timeout de 15 s de ``create_driver`` es la señal real de puerto
    trabado (``/json`` responde pero la sesión nunca se crea). Los demás
    errores —un driver anterior cerrándose o la página cargando— son
    transitorios y ameritan un reintento antes de reiniciar el navegador.
    """
    try:
        browser, executable = detect_browser(config["browser"])
        driver = create_driver(
            browser,
            executable,
            local_path(config["profile_directory"]),
            debugger_address,
        )
    except RuntimeError as error:
        return "wedged" if "trabado" in str(error) else "transient"
    except Exception:  # noqa: BLE001 — cualquier fallo de adjunte cuenta como transitorio
        return "transient"
    release_driver(driver)
    return "ok"


def debugger_session_attachable(config: dict, debugger_address: str) -> bool:
    """Sonda real: que el puerto responda HTTP no basta. Cuando el depurador
    se traba, ``/json`` contesta pero Selenium nunca logra crear la sesión.

    Solo el timeout de sesión marca el puerto como trabado de inmediato; un
    fallo rápido se reintenta una vez para no reiniciar el navegador por un
    error transitorio.
    """
    outcome = _attach_session_once(config, debugger_address)
    if outcome == "ok":
        return True
    if outcome == "wedged":
        return False
    time.sleep(2.0)
    return _attach_session_once(config, debugger_address) == "ok"


def restart_browser(config: dict) -> None:
    """Reinicia el navegador del perfil dedicado: cierra el que escucha en el
    puerto de depuración y lo vuelve a abrir. Las pestañas de la app y de
    Salesforce se abren solo si faltan: si el navegador restauró su sesión,
    no se duplican."""
    global monitor_window_handle, browser_started_monotonic
    browser_started_monotonic = time.monotonic()
    debugger_address = config.get("debugger_address", "127.0.0.1:9222")
    port = debugger_address.rpartition(":")[2]
    # La sesión persistente y el handle de ventana apuntan al navegador que
    # se va a matar: se descartan antes para que el próximo ciclo recree.
    _drop_monitor_driver()
    monitor_window_handle = None
    _, executable = detect_browser(config["browser"])
    profile_directory = local_path(config["profile_directory"])
    pid = find_listening_pid(port)
    # Sin proceso en el puerto puede seguir vivo un Edge del perfil lanzado
    # con --remote-debugging-port=0: hay que tumbarlo por su user-data-dir
    # o el relanzamiento falla sobre el mismo perfil.
    pids = [pid] if pid else dedicated_profile_pids(profile_directory)
    for target_pid in pids:
        subprocess.run(
            ["taskkill", "/PID", target_pid, "/T", "/F"],
            capture_output=True,
            timeout=30,
        )
    if pids:
        deadline = time.monotonic() + 15
        while debugger_is_listening(debugger_address) and time.monotonic() < deadline:
            time.sleep(0.5)
    subprocess.run(["taskkill", "/IM", "msedgedriver.exe", "/F"], capture_output=True)
    launch_persistent_browser(executable, profile_directory, debugger_address)
    if not wait_for_debugger(debugger_address):
        # Sin este log el reinicio "exitoso" que no levanta el puerto era
        # invisible: el loop repetía navegador_trabado sin explicar por qué.
        print(
            f"[monitor] reinicio: el navegador no abrió el puerto de depuración "
            f"({debugger_address}). Revisar que Edge del perfil dedicado abra a mano.",
            flush=True,
        )
        return
    # /json/version responde antes de que la restauración de sesión pueble
    # las pestañas: sin esta espera se abrirían la app y Salesforce duplicadas.
    wait_for_restored_tabs(debugger_address)
    # Primera pestaña la app (lo que el operador necesita ver) y Salesforce al lado.
    urls = [f"http://127.0.0.1:{SERVER_PORT}/", config["salesforce_url"]]
    open_missing_tabs(executable, profile_directory, debugger_address, urls)
    # El relanzamiento usa about:blank como URL inicial (sin URL Edge abre
    # el NTP online que cuelga la sesión): queda sobrando cuando la
    # restauración recupera las pestañas. Se cierra solo si queda otra
    # pestaña viva — cerrar la última tumbaría el navegador entero.
    targets = debugger_tab_targets(debugger_address)
    if any(t["url"] != "about:blank" for t in targets):
        close_stuck_debugger_targets(debugger_address, url_prefixes=("about:blank",))


def write_session_file(ui_output_directory: Path, port: int, token: str) -> Path:
    """Publica puerto y token donde la UI puede leerlos (carpeta ya vinculada)."""
    ui_output_directory.mkdir(parents=True, exist_ok=True)
    session_path = ui_output_directory / SESSION_FILE
    session_path.write_text(
        json.dumps({"port": port, "token": token}, indent=2),
        encoding="utf-8",
    )
    return session_path


def make_handler(token: str, config: dict | None = None):
    class BotRequestHandler(BaseHTTPRequestHandler):
        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            # Sin el token de la sesión ninguna otra página local puede disparar el bot.
            return self.headers.get("X-Bot-Token") == token

        def do_OPTIONS(self) -> None:  # preflight CORS para el header del token
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "X-Bot-Token, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, PUT")
            self.end_headers()

        def _serve_ui_page(self) -> None:
            if not UI_PAGE.is_file():
                self._send(404, {"error": "no se encontró documentador_predictivo.html"})
                return
            html = UI_PAGE.read_text(encoding="utf-8").replace(TOKEN_PLACEHOLDER, token)
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_api_file(self) -> None:
            target = API_FILES[urlparse(self.path).path]
            try:
                payload = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = []
            self._send(200, payload if isinstance(payload, (list, dict)) else [])

        def _query_token(self) -> str:
            return (parse_qs(urlparse(self.path).query).get("token") or [""])[0]

        def _serve_events(self) -> None:
            """SSE: EventSource no manda headers, el token llega por query."""
            if self._query_token() != token:
                self._send(403, {"error": "token inválido o ausente"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            subscriber: queue_module.Queue = queue_module.Queue()
            with event_subscribers_lock:
                event_subscribers.append(subscriber)
            try:
                self.wfile.write(b": conectado\n\n")
                self.wfile.flush()
                while True:
                    try:
                        payload = subscriber.get(timeout=SSE_HEARTBEAT_SECONDS)
                    except queue_module.Empty:
                        payload = None
                    line = (
                        b": ping\n\n"
                        if payload is None
                        else b"data: " + json.dumps(payload, ensure_ascii=False).encode() + b"\n\n"
                    )
                    self.wfile.write(line)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with event_subscribers_lock:
                    if subscriber in event_subscribers:
                        event_subscribers.remove(subscriber)

        def _monitor_payload(self) -> dict:
            state = monitor_read_state(config or load_config())
            return {
                "enabled": state["enabled"],
                "solo_listar": state["solo_listar"],
                "enviar_whatsapp": state["enviar_whatsapp"],
                "notificar": state.get("notificar", True),
                "paused_reason": state["paused_reason"],
                "last_cycle_at": state["last_cycle_at"],
                "cycle_running": monitor_cycle_active,
                "bot_running": current_process is not None and current_process.poll() is None,
                "bandejas": state["bandejas"],
                "schedule": state["schedule"],
                "equipo": state.get("equipo", []),
                "results": state["results"][-50:],
            }

        def do_GET(self) -> None:
            route = urlparse(self.path).path
            if route in ("/", "/index.html"):
                self._serve_ui_page()
                return
            if route == "/api/events":
                self._serve_events()
                return
            if route == "/api/monitor":
                if not self._authorized():
                    self._send(403, {"error": "token inválido o ausente"})
                    return
                self._send(200, self._monitor_payload())
                return
            if route == "/api/ui-prefs":
                if not self._authorized():
                    self._send(403, {"error": "token inválido o ausente"})
                    return
                self._send(200, {"prefs": read_ui_prefs(config or load_config())})
                return
            if route == "/status":
                running = current_process is not None and current_process.poll() is None
                self._send(
                    200,
                    {
                        "running": running,
                        "operation": current_operation if running else None,
                        "exit_code": None if running or current_process is None else current_process.returncode,
                        "monitor_cycle": monitor_cycle_active,
                        "version": app_version(),
                    },
                )
                return
            if route in API_FILES:
                if not self._authorized():
                    self._send(403, {"error": "token inválido o ausente"})
                    return
                self._read_api_file()
                return
            if route == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            self._send(404, {"error": "ruta desconocida"})

        def _read_json_body(self) -> dict | None:
            try:
                body_length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(body_length).decode("utf-8"))
            except (ValueError, json.JSONDecodeError):
                self._send(400, {"error": "JSON inválido"})
                return None
            return payload

        def do_PUT(self) -> None:
            route = urlparse(self.path).path
            if route == "/api/ui-prefs":
                # Preferencias de UI (vista de columnas, toggles): persisten
                # del lado del servidor para que sigan al usuario aunque
                # cambie de navegador o el perfil borre el localStorage.
                if not self._authorized():
                    self._send(403, {"error": "token inválido o ausente"})
                    return
                payload = self._read_json_body()
                if payload is None:
                    return
                incoming = payload.get("prefs") if isinstance(payload, dict) else None
                if not isinstance(incoming, dict):
                    self._send(400, {"error": "se esperaba un objeto 'prefs'"})
                    return
                bad_keys = [key for key in incoming if not isinstance(key, str) or not PREF_KEY_PATTERN.match(key)]
                if bad_keys:
                    self._send(400, {"error": f"claves de preferencia inválidas: {bad_keys[:3]}"})
                    return
                cfg = config or load_config()
                prefs = read_ui_prefs(cfg)
                prefs.update(incoming)
                try:
                    serialized = json.dumps(prefs, ensure_ascii=False)
                except (TypeError, ValueError):
                    self._send(400, {"error": "valores no serializables"})
                    return
                if len(serialized.encode("utf-8")) > UI_PREFS_MAX_BYTES:
                    self._send(413, {"error": "preferencias demasiado grandes"})
                    return
                write_ui_prefs(cfg, prefs)
                self._send(200, {"status": "guardado"})
                return
            if route in ("/api/monitor/config", "/api/monitor/schedule", "/api/monitor/equipo"):
                if not self._authorized():
                    self._send(403, {"error": "token inválido o ausente"})
                    return
                payload = self._read_json_body()
                if payload is None:
                    return
                if not isinstance(payload, dict):
                    self._send(400, {"error": "se esperaba un objeto JSON"})
                    return
                cfg = config or load_config()
                state = monitor_read_state(cfg)
                try:
                    if route == "/api/monitor/config":
                        state["bandejas"] = validate_bandejas(payload.get("bandejas"))
                    elif route == "/api/monitor/equipo":
                        equipo = validate_equipo(payload.get("equipo"))
                        franjas = [slot for member in equipo for slot in member["franjas"]]
                        sin_bandeja = next(
                            (f"{m['nombre']} {s['start']}–{s['end']}"
                             for m in equipo for s in m["franjas"] if not s["bandejas"]),
                            None,
                        )
                        if sin_bandeja:
                            raise ValueError(f"Cada franja debe indicar al menos una bandeja ({sin_bandeja}).")
                        missing = _franjas_con_bandeja_no_disponible(state, franjas)
                        if missing:
                            raise ValueError(
                                f"Franjas apuntan a bandejas no disponibles: {', '.join(sorted(missing))}."
                            )
                        state["equipo"] = equipo
                    else:
                        schedule = validate_schedule(payload.get("schedule"))
                        sin_bandeja = next(
                            (f"{s['start']}–{s['end']}" for s in schedule if not s["bandejas"]),
                            None,
                        )
                        if sin_bandeja:
                            raise ValueError(f"Cada franja debe indicar al menos una bandeja ({sin_bandeja}).")
                        missing = _franjas_con_bandeja_no_disponible(state, schedule)
                        if missing:
                            raise ValueError(
                                f"Franjas apuntan a bandejas no disponibles: {', '.join(sorted(missing))}."
                            )
                        state["schedule"] = schedule
                except ValueError as error:
                    self._send(400, {"error": str(error)})
                    return
                monitor_write_state(cfg, state)
                broadcast_event({"type": "monitor_state", "equipo": state["equipo"]})
                self._send(200, {"status": "guardado"})
                return
            if route not in WRITABLE_API:
                self._send(404, {"error": "ruta desconocida"})
                return
            if not self._authorized():
                self._send(403, {"error": "token inválido o ausente"})
                return
            payload = self._read_json_body()
            if payload is None:
                return
            if not isinstance(payload, dict) or not isinstance(payload.get("leads"), list):
                self._send(400, {"error": "se esperaba un objeto con la lista 'leads'"})
                return
            try:
                # El modo de país se congela en la cola: se rechaza de entrada
                # cualquier valor que los runners no puedan interpretar.
                normalize_country(payload.get("country"))
            except ValueError as error:
                self._send(400, {"error": str(error)})
                return
            if urlparse(self.path).path == "/api/close-queue":
                try:
                    validate_close_queue(payload)
                except ValueError as error:
                    self._send(400, {"error": str(error)})
                    return
            elif urlparse(self.path).path == "/api/distribucion-queue":
                try:
                    validate_distribucion_queue(payload)
                except ValueError as error:
                    self._send(400, {"error": str(error)})
                    return
            target = API_FILES[urlparse(self.path).path]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            response = {"status": "guardada", "leads": len(payload["leads"])}
            if urlparse(self.path).path == "/api/distribucion-queue":
                # Advertencia (no bloqueo): un monitor activo puede tomar los
                # mismos leads de la bandeja mientras corre el lote.
                try:
                    response["monitor_activo"] = bool(monitor_read_state(config or load_config()).get("enabled"))
                except (OSError, ValueError):
                    response["monitor_activo"] = False
            self._send(200, response)

        def do_POST(self) -> None:
            global current_process
            route = urlparse(self.path).path
            if not self._authorized():
                self._send(403, {"error": "token inválido o ausente"})
                return
            if route == "/api/distribucion/parse":
                # El archivo de la BD de leads se parsea en memoria y nunca
                # se persiste: la respuesta trae hojas/encabezados/filas.
                body_length = int(self.headers.get("Content-Length") or 0)
                if body_length > PARSE_MAX_BYTES:
                    self._send(413, {"error": "archivo demasiado grande"})
                    return
                payload = self._read_json_body()
                if not isinstance(payload, dict):
                    return
                filename = str(payload.get("filename") or "").strip()
                content_b64 = payload.get("content_b64")
                if not filename or not isinstance(content_b64, str) or not content_b64:
                    self._send(400, {"error": "se esperaba filename y content_b64"})
                    return
                try:
                    parsed = parse_archivo(filename, base64.b64decode(content_b64, validate=True))
                except ValueError as error:
                    self._send(400, {"error": str(error)})
                    return
                self._send(200, parsed)
                return
            if route == "/api/monitor/clear-results":
                if not cycle_lock.acquire(blocking=False):
                    self._send(409, {"error": "hay una revision del monitor en curso; reintenta al finalizar"})
                    return
                try:
                    cfg = config or load_config()
                    state = monitor_read_state(cfg)
                    removed = clear_results(state)
                    monitor_write_state(cfg, state)
                finally:
                    cycle_lock.release()
                broadcast_event({"type": "monitor", "status": "results_cleared"})
                self._send(200, {"status": "lista limpiada", "removed": removed})
                return
            if route == "/api/monitor/toggle":
                cfg = config or load_config()
                state = monitor_read_state(cfg)
                enabled = None
                if int(self.headers.get("Content-Length") or 0):
                    body = self._read_json_body()
                    if body is None:
                        return
                    enabled = body.get("enabled") if isinstance(body, dict) else None
                state["enabled"] = not state["enabled"] if enabled is None else bool(enabled)
                monitor_write_state(cfg, state)
                broadcast_event({"type": "monitor_state", "enabled": state["enabled"]})
                self._send(200, {"enabled": state["enabled"]})
                return
            if route == "/api/monitor/dry-run":
                cfg = config or load_config()
                state = monitor_read_state(cfg)
                solo_listar = None
                if int(self.headers.get("Content-Length") or 0):
                    body = self._read_json_body()
                    if body is None:
                        return
                    solo_listar = body.get("solo_listar") if isinstance(body, dict) else None
                state["solo_listar"] = not state["solo_listar"] if solo_listar is None else bool(solo_listar)
                monitor_write_state(cfg, state)
                broadcast_event({"type": "monitor_state", "solo_listar": state["solo_listar"]})
                self._send(200, {"solo_listar": state["solo_listar"]})
                return
            if route == "/api/monitor/whatsapp":
                cfg = config or load_config()
                state = monitor_read_state(cfg)
                enviar = None
                if int(self.headers.get("Content-Length") or 0):
                    body = self._read_json_body()
                    if body is None:
                        return
                    enviar = body.get("enviar_whatsapp") if isinstance(body, dict) else None
                state["enviar_whatsapp"] = not state["enviar_whatsapp"] if enviar is None else bool(enviar)
                monitor_write_state(cfg, state)
                broadcast_event({"type": "monitor_state", "enviar_whatsapp": state["enviar_whatsapp"]})
                self._send(200, {"enviar_whatsapp": state["enviar_whatsapp"]})
                return
            if route == "/api/monitor/notify":
                # Activa/pausa el toast nativo de Windows (el aviso gris del
                # navegador duplicaba este toast y se eliminó de la UI).
                cfg = config or load_config()
                state = monitor_read_state(cfg)
                notificar = None
                if int(self.headers.get("Content-Length") or 0):
                    body = self._read_json_body()
                    if body is None:
                        return
                    notificar = body.get("notificar") if isinstance(body, dict) else None
                state["notificar"] = not state["notificar"] if notificar is None else bool(notificar)
                monitor_write_state(cfg, state)
                broadcast_event({"type": "monitor_state", "notificar": state["notificar"]})
                self._send(200, {"notificar": state["notificar"]})
                return
            if route == "/api/monitor/notify-test":
                windows_toast(
                    "Monitor de Bandeja — prueba",
                    "Si ves este aviso, las notificaciones de Windows funcionan.",
                )
                self._send(200, {"ok": True})
                return
            if route == "/api/monitor/check":
                # Revisión manual: corre ya, sin importar toggle ni franja horaria.
                if start_manual_check(config or load_config()):
                    self._send(202, {"status": "revision en curso"})
                else:
                    self._send(409, {"error": "ya hay una revision en curso"})
                return
            if route == "/api/reload":
                # Reinicio intencional: el proceso sale con 0 y el guardián
                # lo relanza al instante sin contarlo como caída. Sirve para
                # recargar código recién sincronizado sin taskkill.
                self._send(200, {"status": "reiniciando el servidor"})
                threading.Timer(0.4, _force_clean_exit).start()
                return
            if route == "/api/restart-browser":
                if current_process is not None and current_process.poll() is None:
                    self._send(409, {"error": "el bot está corriendo; esperá a que termine"})
                    return
                if monitor_cycle_active:
                    self._send(
                        409,
                        {"error": "el monitor está revisando las bandejas; esperá a que termine el ciclo"},
                    )
                    return
                self._send(202, {"status": "reiniciando el navegador del bot"})
                threading.Thread(target=restart_browser, args=(config or load_config(),), daemon=True).start()
                return
            if route not in ("/run", "/run-close", "/run-distribucion"):
                self._send(404, {"error": "ruta desconocida"})
                return
            with run_lock:
                if current_process is not None and current_process.poll() is None:
                    self._send(409, {"status": "ya esta corriendo", "operation": current_operation})
                    return
                if monitor_cycle_active:
                    self._send(
                        409,
                        {
                            "error": "El Monitor de Bandeja está revisando Salesforce en este "
                            "momento. Esperá unos segundos a que termine el ciclo y reintentá."
                        },
                    )
                    return
                cfg = config or load_config()
                debugger_address = cfg.get("debugger_address", "127.0.0.1:9222")
                if not debugger_is_listening(debugger_address):
                    self._send(
                        503,
                        {
                            "error": "El navegador dedicado del bot no está abierto. "
                            "Abrilo con INICIAR.bat o el botón "
                            "'Reiniciar navegador del bot' y volvé a intentar.",
                        },
                    )
                    return
                # Un puerto trabado puede responder /json y aun así colgar la
                # sesión de Selenium: la sonda es la prueba decisiva. Si falla
                # se reinicia el navegador dedicado una sola vez, todavía sin
                # tocar ningún Lead; si tampoco revive, se rechaza la tanda.
                if not (debugger_http_ready(debugger_address) and debugger_session_attachable(cfg, debugger_address)):
                    restart_browser(cfg)
                    if not (
                        debugger_http_ready(debugger_address) and debugger_session_attachable(cfg, debugger_address)
                    ):
                        self._send(
                            503,
                            {
                                "error": "El puerto de depuración del navegador dedicado "
                                "quedó trabado y el reinicio automático no lo recuperó. "
                                "Cerrá la ventana del bot y abrila con INICIAR.bat.",
                            },
                        )
                        return
                queue_directory = ROOT / "queues"
                queue_directory.mkdir(parents=True, exist_ok=True)
                run_id = "run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + secrets.token_hex(3)
                if route == "/run-close":
                    started = self._start_close_run(cfg, queue_directory, run_id)
                elif route == "/run-distribucion":
                    started = self._start_distribucion_run(cfg, queue_directory, run_id)
                else:
                    started = self._start_document_run(cfg, queue_directory, run_id)
                if not started:
                    # La respuesta de error ya la envió el helper.
                    return
            queue_name = {
                "/run-close": ACTIVE_CLOSE_QUEUE,
                "/run-distribucion": ACTIVE_DISTRIBUCION_QUEUE,
            }.get(route, ACTIVE_QUEUE)
            self._send(202, {"status": "iniciado", "queue": queue_name, "run_id": run_id})

        def _start_document_run(self, cfg: dict, queue_directory: Path, run_id: str) -> bool:
            global current_process, current_operation
            try:
                frozen_path = freeze_active_queue(queue_directory, run_id)
            except OSError:
                self._send(500, {"error": "no se pudo congelar la cola activa"})
                return False
            try:
                load_queue_file(str(frozen_path), queue_directory)
            except (OSError, ValueError):
                self._send(400, {"error": "Cola de documentación vacía o inválida. Revisá los intentos pendientes."})
                return False
            current_operation = "documentacion"
            current_process = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "run_document_queue.py"),
                    "--auto",
                    "--run-id",
                    run_id,
                    "--results",
                    str(queue_directory / "cola_activa.resultado.json"),
                    "--snapshots",
                    str(ROOT / cfg.get("ui_output_directory", "ui_output") / "cola_activa.snapshots.json"),
                    "--metrics",
                    str(queue_directory / "cola_activa.metricas.json"),
                    str(frozen_path),
                ],
                cwd=str(ROOT),
            )
            return True

        def _start_close_run(self, cfg: dict, queue_directory: Path, run_id: str) -> bool:
            global current_process, current_operation
            active_path = queue_directory / ACTIVE_CLOSE_QUEUE
            try:
                validate_close_queue(json.loads(active_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ValueError) as error:
                self._send(400, {"error": f"Cola de cierre inválida: {error}"})
                return False
            try:
                frozen_path = freeze_active_close_queue(queue_directory, run_id)
            except OSError:
                self._send(500, {"error": "no se pudo congelar la cola de cierre"})
                return False
            current_operation = "cierre"
            current_process = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "run_close_queue.py"),
                    "--auto",
                    "--run-id",
                    run_id,
                    "--results",
                    str(queue_directory / "cola_cierre_activa.resultado.json"),
                    str(frozen_path),
                ],
                cwd=str(ROOT),
            )
            return True

        def _start_distribucion_run(self, cfg: dict, queue_directory: Path, run_id: str) -> bool:
            global current_process, current_operation
            active_path = queue_directory / ACTIVE_DISTRIBUCION_QUEUE
            try:
                validate_distribucion_queue(json.loads(active_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ValueError) as error:
                self._send(400, {"error": f"Cola de distribución inválida: {error}"})
                return False
            try:
                frozen_path = freeze_active_distribucion_queue(queue_directory, run_id)
            except OSError:
                self._send(500, {"error": "no se pudo congelar la cola de distribución"})
                return False
            current_operation = "distribucion"
            current_process = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "run_distribucion_queue.py"),
                    "--auto",
                    "--run-id",
                    run_id,
                    "--results",
                    str(queue_directory / "cola_distribucion_activa.resultado.json"),
                    str(frozen_path),
                ],
                cwd=str(ROOT),
            )
            return True

        def log_message(self, *_args) -> None:
            pass

    return BotRequestHandler


def main() -> int:
    config = load_config()
    ui_output_directory = ROOT / config.get("ui_output_directory", "ui_output")
    instance_lock = acquire_instance_lock(ui_output_directory)
    if instance_lock is None:
        # En Windows dos servidores podrían bindear el mismo puerto
        # (SO_REUSEADDR): el lock evita esa convivencia antes del bind.
        print("Ya hay un servidor del bot corriendo; esta instancia cierra.")
        return 0
    token = load_or_create_token(ui_output_directory)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", SERVER_PORT), make_handler(token, config))
    except OSError:
        print(f"El puerto {SERVER_PORT} ya está en uso por otro proceso; esta instancia cierra.")
        return 0
    session_path = write_session_file(ui_output_directory, SERVER_PORT, token)
    print(f"Servidor del bot en http://127.0.0.1:{SERVER_PORT} (solo localhost).")
    print(f"Sesión para la UI: {session_path}")
    print("La UI dispara el bot con el botón 'Ejecutar bot'. Ctrl+C para salir.")
    monitor_thread = threading.Thread(target=monitor_loop, args=(config, monitor_stop), daemon=True)
    watcher_thread = threading.Thread(target=run_status_watcher, args=(monitor_stop,), daemon=True)
    monitor_thread.start()
    watcher_thread.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        monitor_stop.set()
        _drop_monitor_driver()
        if current_process is not None and current_process.poll() is None:
            print("Deteniendo el bot en curso...")
            current_process.terminate()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
