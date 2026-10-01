from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from browser_factory import (
    debugger_is_listening,
    detect_browser,
    launch_persistent_browser,
    open_url_in_browser,
)

ROOT = Path(__file__).parent
DEFAULT_DEBUGGER_ADDRESS = "127.0.0.1:9222"
DEFAULT_APP_URL = "http://127.0.0.1:8765/"


def load_config() -> dict:
    with (ROOT / "config.json").open(encoding="utf-8") as file:
        return json.load(file)


def local_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def main() -> int:
    parser = argparse.ArgumentParser(description="Abre el navegador persistente del bot con Salesforce y la app.")
    parser.add_argument("--app-url", default=DEFAULT_APP_URL)
    parser.add_argument("--no-app", action="store_true", help="No abrir la pestaña de la app")
    args = parser.parse_args()

    config = load_config()
    debugger_address = config.get("debugger_address", DEFAULT_DEBUGGER_ADDRESS)
    urls = [config["salesforce_url"]]
    if not args.no_app:
        urls.append(args.app_url)

    browser, executable = detect_browser(config["browser"])
    profile_directory = local_path(config["profile_directory"])
    if debugger_is_listening(debugger_address):
        for url in urls:
            open_url_in_browser(executable, profile_directory, url)
        print(f"Ya había un navegador en {debugger_address}; se abrieron las pestañas allí.")
    else:
        launch_persistent_browser(executable, profile_directory, debugger_address, urls)
        print(f"{browser.capitalize()} abierto con el perfil dedicado en {debugger_address}.")
    print("Pestaña 1: Salesforce — iniciá sesión y completá 2FA si te lo pide.")
    print("Pestaña 2: la app del Documentador Predictivo.")
    print("Dejá esta ventana abierta mientras trabajás; el bot se conecta a ella.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
