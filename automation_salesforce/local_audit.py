from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def mask_lead_id(lead_id: str) -> str:
    value = str(lead_id or "")
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def create_logger(log_directory: Path) -> logging.Logger:
    log_directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("salesforce_read_only")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    filename = log_directory / f"read_only_{datetime.now():%Y%m%d}.log"
    handler = logging.FileHandler(filename, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def capture_failure(driver, screenshot_directory: Path, name: str) -> Path:
    screenshot_directory.mkdir(parents=True, exist_ok=True)
    target = screenshot_directory / f"{datetime.now():%Y%m%d_%H%M%S}_{name}.png"
    driver.save_screenshot(str(target))
    return target
