from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

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


def launch_persistent_browser(executable: Path, profile_directory: Path, debugger_address: str) -> None:
    """Abre el navegador con el perfil dedicado y puerto de depuración; queda abierto al salir."""
    profile_directory.mkdir(parents=True, exist_ok=True)
    port = debugger_address.rpartition(":")[2]
    subprocess.Popen(
        [
            str(executable),
            f"--user-data-dir={profile_directory}",
            f"--remote-debugging-port={port}",
            "--start-maximized",
        ],
        close_fds=True,
    )


def create_driver(browser: str, executable: Path, profile_directory: Path, debugger_address: str | None = None):
    options = EdgeOptions() if browser == "edge" else ChromeOptions()
    attached = bool(debugger_address) and debugger_is_listening(debugger_address)
    if attached:
        options.add_experimental_option("debuggerAddress", debugger_address)
    else:
        profile_directory.mkdir(parents=True, exist_ok=True)
        options.binary_location = str(executable)
        options.add_argument(f"--user-data-dir={profile_directory}")
        options.add_argument("--start-maximized")
    driver = webdriver.Edge(options=options) if browser == "edge" else webdriver.Chrome(options=options)
    driver.attached_to_persistent_browser = attached
    if attached:
        # El bot trabaja en una pestaña propia para no navegar la pestaña
        # que el operador tenga abierta (por ejemplo la UI local).
        try:
            driver.switch_to.new_window("tab")
        except WebDriverException:
            pass
    return driver


def release_driver(driver) -> None:
    """Cierra el navegador solo si lo abrió este proceso; si está adjunto, lo deja abierto."""
    if getattr(driver, "attached_to_persistent_browser", False):
        return
    driver.quit()
