from __future__ import annotations

from selenium.common.exceptions import TimeoutException

from browser_factory import create_driver, detect_browser, release_driver
from local_audit import capture_failure, create_logger
from salesforce_session import (
    ROOT,
    load_config,
    local_path,
    prompt_for_manual_authentication,
)


def main() -> None:
    config = load_config()
    log_directory = ROOT / config["log_directory"]
    screenshot_directory = ROOT / config["screenshot_directory"]
    logger = create_logger(log_directory)
    browser, executable = detect_browser(config["browser"])
    profile_directory = local_path(config["profile_directory"])
    print(f"Abriendo {browser.capitalize()} con perfil dedicado: {profile_directory}")
    driver = create_driver(
        browser,
        executable,
        profile_directory,
        config.get("debugger_address", "127.0.0.1:9222"),
    )
    try:
        prompt_for_manual_authentication(driver, config)
        logger.info("Autenticación confirmada en %s", browser)
        print("Autenticación confirmada. El piloto terminó sin leer ni modificar Salesforce.")
        input("Presioná Enter para cerrar el navegador: ")
    except TimeoutException:
        screenshot = capture_failure(driver, screenshot_directory, "authentication_timeout")
        logger.error("No se confirmó autenticación. Captura: %s", screenshot.name)
        print("No se detectó una sesión de Salesforce. Revisá el login o 2FA.")
    except KeyboardInterrupt:
        logger.info("Piloto interrumpido por el usuario")
        print("Piloto interrumpido.")
    finally:
        release_driver(driver)


if __name__ == "__main__":
    main()
