from __future__ import annotations

import os
from pathlib import Path

from selenium import webdriver
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


def create_driver(browser: str, executable: Path, profile_directory: Path):
    profile_directory.mkdir(parents=True, exist_ok=True)
    if browser == "edge":
        options = EdgeOptions()
        options.binary_location = str(executable)
        options.add_argument(f"--user-data-dir={profile_directory}")
        options.add_argument("--start-maximized")
        return webdriver.Edge(options=options)
    options = ChromeOptions()
    options.binary_location = str(executable)
    options.add_argument(f"--user-data-dir={profile_directory}")
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)
