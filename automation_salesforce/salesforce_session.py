from __future__ import annotations

import json
import os
from pathlib import Path

from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).parent


def load_config() -> dict:
    with (ROOT / "config.json").open(encoding="utf-8") as file:
        return json.load(file)


def local_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def wait_for_authentication(driver, timeout_seconds: int) -> None:
    WebDriverWait(driver, timeout_seconds).until(
        lambda current_driver: "lightning.force.com" in current_driver.current_url
        and "login" not in current_driver.current_url.lower()
    )


def wait_for_lightning_ready(driver, timeout_seconds: int) -> None:
    WebDriverWait(driver, timeout_seconds).until(
        lambda current_driver: current_driver.execute_script("return document.readyState") == "complete"
    )


def prompt_for_manual_authentication(driver, config: dict) -> None:
    driver.get(config["salesforce_url"])
    input("Iniciá sesión y completá 2FA manualmente. Cuando veas Salesforce, presioná Enter aquí: ")
    wait_for_authentication(driver, config["timeouts"]["authentication_seconds"])
