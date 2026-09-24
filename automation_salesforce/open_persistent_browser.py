from __future__ import annotations

from browser_factory import (
    debugger_is_listening,
    detect_browser,
    launch_persistent_browser,
)
from salesforce_session import load_config, local_path

DEFAULT_DEBUGGER_ADDRESS = "127.0.0.1:9222"


def main() -> int:
    config = load_config()
    debugger_address = config.get("debugger_address", DEFAULT_DEBUGGER_ADDRESS)
    if debugger_is_listening(debugger_address):
        print(f"Ya hay un navegador persistente escuchando en {debugger_address}.")
        return 0
    browser, executable = detect_browser(config["browser"])
    launch_persistent_browser(executable, local_path(config["profile_directory"]), debugger_address)
    print(f"{browser.capitalize()} abierto con el perfil dedicado en {debugger_address}.")
    print("Iniciá sesión en Salesforce una sola vez y dejá esta ventana abierta.")
    print("Los runners se conectarán a ella automáticamente mientras siga abierta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
