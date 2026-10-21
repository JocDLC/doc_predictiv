from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse

BROWSER_PATHS = {
    "edge": [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ],
    "chrome": [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ],
}


def detect_browser(requested_browser: str) -> tuple[str, Path]:
    candidates = ["edge", "chrome"] if requested_browser == "auto" else [requested_browser]
    for browser in candidates:
        if browser not in BROWSER_PATHS:
            raise ValueError("Navegador inválido. Usá edge, chrome o auto.")
        for executable in BROWSER_PATHS[browser]:
            if executable.is_file():
                return browser, executable
    raise FileNotFoundError(f"No se encontró el navegador solicitado: {requested_browser}")


def debugger_is_listening(debugger_address: str, timeout_seconds: float = 1.0) -> bool:
    host, _, port = debugger_address.rpartition(":")
    try:
        with socket.create_connection((host or "127.0.0.1", int(port)), timeout=timeout_seconds):
            return True
    except (OSError, ValueError):
        return False


def debugger_http_ready(debugger_address: str, timeout_seconds: float = 3.0) -> bool:
    """Confirma que el depurador responda HTTP, no solo acepte el socket.

    Un puerto trabado pasa ``debugger_is_listening`` pero nunca contesta
    ``/json/version``: es el estado que colgaba la creación de la sesión.
    """
    host, _, port = debugger_address.rpartition(":")
    try:
        with urllib.request.urlopen(
            f"http://{host or '127.0.0.1'}:{port}/json/version",
            timeout=timeout_seconds,
        ) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def launch_persistent_browser(
    executable: Path,
    profile_directory: Path,
    debugger_address: str,
    urls: list[str] | None = None,
) -> None:
    """Abre el navegador con el perfil dedicado y puerto de depuración; queda abierto al salir."""
    profile_directory.mkdir(parents=True, exist_ok=True)
    port = debugger_address.rpartition(":")[2]
    subprocess.Popen(
        [
            str(executable),
            f"--user-data-dir={profile_directory}",
            f"--remote-debugging-port={port}",
            "--start-maximized",
            # La pestaña de Salesforce no puede suspenderse ni tener sus
            # timers estrangulados: cuando Edge la "duerme", el CDP deja de
            # responder y el monitor pierde la conexión (navegador_trabado).
            "--disable-features=msEfficiencyMode,msSleepingTabs,msEdgeSleepingTabs",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            # Sin URL propia Edge >=148 abre el NTP online (ntp.msn.com): una
            # pestaña que se queda esperando headers (p. ej. tras el proxy)
            # bloquea la enumeración de targets al crear la sesión CDP.
            *(urls or ["about:blank"]),
        ],
        close_fds=True,
    )


def open_tab_via_debugger(debugger_address: str, url: str, timeout_seconds: float = 5.0) -> bool:
    """Abre una pestaña vía CDP (``/json/new``) dentro del navegador activo.

    Relanzar el ejecutable con la URL puede crear una ventana nueva mientras
    la restauración de sesión todavía corre; por CDP la pestaña siempre cae
    en una ventana ya abierta del navegador dedicado.
    """
    host, _, port = debugger_address.rpartition(":")
    request = urllib.request.Request(
        f"http://{host or '127.0.0.1'}:{port}/json/new?{quote(url, safe='')}",
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return 200 <= response.status < 300
    except (OSError, ValueError):
        return False


def open_url_in_browser(executable: Path, profile_directory: Path, url: str) -> None:
    """Abre una pestaña en la instancia ya corriendo con el perfil dedicado.

    Chromium delega la URL al proceso existente cuando se invoca con el mismo
    ``--user-data-dir``. Es el respaldo cuando el depurador no responde.
    """
    subprocess.Popen(
        [
            str(executable),
            f"--user-data-dir={profile_directory}",
            url,
        ],
        close_fds=True,
    )


def debugger_tab_targets(debugger_address: str, timeout_seconds: float = 3.0) -> list[dict]:
    """Targets tipo página de ``/json/list`` con ``id`` y ``url``.

    El ``id`` del target es el mismo que ChromeDriver usa como window handle
    (a veces prefijado ``CDwindow-``), así permite ubicar una pestaña concreta
    sin tener que activarla.
    """
    host, _, port = debugger_address.rpartition(":")
    try:
        with urllib.request.urlopen(
            f"http://{host or '127.0.0.1'}:{port}/json/list",
            timeout=timeout_seconds,
        ) as response:
            targets = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(targets, list):
        return []
    return [
        {"id": t.get("id"), "url": t.get("url")}
        for t in targets
        if isinstance(t, dict) and t.get("type") == "page" and t.get("url")
    ]


def debugger_tab_urls(debugger_address: str, timeout_seconds: float = 3.0) -> list[str]:
    """URLs de las pestañas abiertas en el navegador depurable.

    ``/json/list`` devuelve todos los targets; solo interesan las pestañas
    reales (``type == "page"``), no workers ni extensiones.
    """
    return [t["url"] for t in debugger_tab_targets(debugger_address, timeout_seconds)]


# Targets desechables que una restauración o un arranque sin URL pueden dejar.
# El NTP online (Edge >=148, ntp.msn.com) puede quedar esperando headers
# detrás del proxy y eso cuelga la creación de la sesión CDP aunque /json
# responda (microsoft/playwright#41093): se cierran antes de cada attach.
STUCK_TARGET_URL_PREFIXES = (
    "edge://newtab",
    "edge://new-tab-page",
    "chrome://newtab",
    "chrome://new-tab-page",
)


def close_stuck_debugger_targets(
    debugger_address: str,
    timeout_seconds: float = 3.0,
    url_prefixes: tuple[str, ...] = STUCK_TARGET_URL_PREFIXES,
) -> list[str]:
    """Cierra vía ``/json/close`` los targets que pueden colgar la sesión.

    Devuelve las URLs cerradas. Solo toca páginas internas desechables
    (NTP): nunca pestañas del usuario ni de la app.
    """
    host, _, port = debugger_address.rpartition(":")
    closed: list[str] = []
    for target in debugger_tab_targets(debugger_address, timeout_seconds):
        url = target["url"]
        if not url.startswith(url_prefixes):
            continue
        for method in ("PUT", "GET"):  # /json/close exige PUT en Chromium reciente
            request = urllib.request.Request(
                f"http://{host or '127.0.0.1'}:{port}/json/close/{target['id']}",
                method=method,
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds):
                    closed.append(url)
                    break
            except (OSError, ValueError):
                continue
    return closed


def wait_for_restored_tabs(
    debugger_address: str,
    timeout_seconds: float = 20.0,
    interval_seconds: float = 0.8,
    stable_reads_required: int = 3,
    min_seconds: float = 5.0,
) -> None:
    """Espera a que el conjunto de pestañas quede estable tras relanzar.

    La restauración de sesión puebla ``/json/list`` después de que
    ``/json/version`` ya responde, y puede tardar varios segundos en traer
    todas las ventanas: deduplicar antes de tiempo abriría la app y
    Salesforce dos veces. Se espera a varias lecturas idénticas no vacías
    y a un tiempo mínimo de gracia.
    """
    last: list[str] | None = None
    stable_reads = 0
    start = time.monotonic()
    deadline = start + timeout_seconds
    while time.monotonic() < deadline:
        current = debugger_tab_urls(debugger_address)
        if current and current == last:
            stable_reads += 1
            if stable_reads >= stable_reads_required and time.monotonic() - start >= min_seconds:
                return
        else:
            stable_reads = 0
            last = current
        time.sleep(interval_seconds)


def _same_site(tab_url: str, target_url: str) -> bool:
    """Mismo host:puerto. Una pestaña de un Lead ya cuenta como Salesforce
    abierto; solo distingue el dominio, no la página concreta."""
    return bool(urlparse(tab_url).netloc) and urlparse(tab_url).netloc == urlparse(target_url).netloc


def open_missing_tabs(
    executable: Path,
    profile_directory: Path,
    debugger_address: str,
    urls: list[str],
) -> list[str]:
    """Abre solo las pestañas que faltan y devuelve las URLs abiertas.

    Consulta las pestañas actuales del navegador dedicado: si la app o
    Salesforce ya están abiertos (cualquier página del mismo host), no se
    duplican. Tras un reinicio con restauración de sesión tampoco repite
    las pestañas que el navegador recuperó solo.
    """
    opened: list[str] = []
    existing = debugger_tab_urls(debugger_address)
    for url in urls:
        if any(_same_site(tab, url) for tab in existing):
            continue
        if not open_tab_via_debugger(debugger_address, url):
            open_url_in_browser(executable, profile_directory, url)
        opened.append(url)
        time.sleep(0.8)
        existing = debugger_tab_urls(debugger_address) or existing
    return opened


def wait_for_debugger(debugger_address: str, timeout_seconds: float = 30.0) -> bool:
    """Espera a que el depurador responda HTTP tras relanzar el navegador."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if debugger_http_ready(debugger_address):
            return True
        time.sleep(0.5)
    return debugger_http_ready(debugger_address)


# Adjuntarse a un navegador sano es instantáneo; un puerto de depuración
# trabado responde /json pero nunca crea la sesión y Selenium colgaba ~120 s
# (la UI solo veía "bot corriendo" sin pestañas). El timeout corto detecta el
# caso rápido y solo aplica a la creación de la sesión.
ATTACH_SESSION_TIMEOUT_SECONDS = 60


def _kill_orphaned_driver_processes() -> None:
    """Libera una creación de sesión colgada cerrando los drivers Chromium."""
    for executable_name in ("msedgedriver.exe", "chromedriver.exe"):
        try:
            subprocess.run(
                ["taskkill", "/IM", executable_name, "/F"],
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            pass


def _create_driver_with_timeout(constructor, options, timeout_seconds: float):
    """Crea el WebDriver en un hilo y abandona si la sesión no se forma.

    Un puerto de depuración trabado deja ``NEW_SESSION`` esperando ~120 s sin
    respuesta. El hilo queda como daemon y al matar el driver huérfano se
    libera solo; el proceso del runner puede continuar y salir limpio.
    """
    result: dict = {}

    def _work() -> None:
        try:
            result["driver"] = constructor(options=options)
        except BaseException as error:  # noqa: BLE001 — se propaga abajo
            result["error"] = error

    thread = threading.Thread(target=_work, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        _kill_orphaned_driver_processes()
        raise RuntimeError(f"La creación de la sesión no respondió en {timeout_seconds} s.")
    if "error" in result:
        raise result["error"]
    return result["driver"]


def create_driver(browser: str, executable: Path, profile_directory: Path, debugger_address: str | None = None):
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions

    options = EdgeOptions() if browser == "edge" else ChromeOptions()
    attached = bool(debugger_address) and debugger_is_listening(debugger_address)
    if debugger_address and not attached:
        # Con el puerto abajo, el driver lanzaría un Edge nuevo sobre el
        # perfil dedicado con --remote-debugging-port=0 y sin las flags
        # anti-suspensión: un navegador fantasma que el reinicio no
        # encuentra y cuyas pestañas se suspenden. El camino correcto es
        # launch_persistent_browser (restart): se falla claro y rápido.
        raise RuntimeError(
            f"El navegador dedicado no está escuchando en {debugger_address}. "
            "Reiniciá el navegador del bot ('Reiniciar navegador del bot' "
            "en la app o INICIAR.bat)."
        )
    if attached:
        options.add_experimental_option("debuggerAddress", debugger_address)
    else:
        profile_directory.mkdir(parents=True, exist_ok=True)
        options.binary_location = str(executable)
        options.add_argument(f"--user-data-dir={profile_directory}")
        options.add_argument("--start-maximized")
    constructor = webdriver.Edge if browser == "edge" else webdriver.Chrome
    if attached:
        # Un NTP online esperando headers tras el proxy cuelga la enumeración
        # de targets de NEW_SESSION: se cierran antes de pedir la sesión.
        close_stuck_debugger_targets(debugger_address)
        try:
            driver = _create_driver_with_timeout(constructor, options, ATTACH_SESSION_TIMEOUT_SECONDS)
        except WebDriverException as error:
            raise RuntimeError(
                "No se pudo conectar al navegador persistente en "
                f"{debugger_address}. Revisá que la ventana dedicada esté abierta."
            ) from error
        except RuntimeError as error:
            raise RuntimeError(
                "No se pudo conectar al navegador persistente en "
                f"{debugger_address} ({ATTACH_SESSION_TIMEOUT_SECONDS} s). El puerto de "
                "depuración parece trabado: reiniciá el navegador dedicado del bot "
                "('Reiniciar navegador del bot' en la app o INICIAR.bat)."
            ) from error
    else:
        driver = constructor(options=options)
    driver.attached_to_persistent_browser = attached
    if attached:
        # El bot trabaja en una pestaña propia para no navegar la pestaña
        # que el operador tenga abierta (por ejemplo la UI local). El handle
        # queda marcado para poder cerrarla aunque el flujo cambie de ventana.
        try:
            driver.switch_to.new_window("tab")
            driver.bot_work_tab_handle = driver.current_window_handle
        except WebDriverException:
            pass
    return driver


def release_driver(driver, close_tab: bool = True) -> None:
    """Libera la sesión de WebDriver sin tumbar el navegador persistente.

    En modo adjunto el navegador no lo creó el driver, así que ``quit()`` solo
    cierra la sesión y termina al chromedriver (verificado: la ventana sigue
    abierta). Sin esto cada tanda deja un chromedriver y una sesión huérfanos
    que acaban trabando el puerto de depuración.

    ``close_tab=False`` deja abierta la pestaña/ventana activa: lo usa el
    monitor, cuya ventana dedicada debe sobrevivir al ciclo para reutilizarla.
    """
    if getattr(driver, "attached_to_persistent_browser", False):
        if close_tab:
            try:
                driver.close()  # pestaña de trabajo que abrió el bot
            except Exception:  # noqa: BLE001 — liberar la sesión importa más
                pass
        try:
            driver.quit()
        except Exception:  # noqa: BLE001
            pass
        return
    driver.quit()
