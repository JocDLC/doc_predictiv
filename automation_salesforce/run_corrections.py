"""Aplica correcciones locales de ``Otra información`` de forma segura.

Por cada corrección de la cola el bot reabre el Lead, relee el campo y
compara su hash con ``base_hash`` (el valor que la UI tenía confirmado):

- coincide → reemplaza el campo, pulsa Guardar y verifica releyendo;
- no coincide → marca ``conflicto`` y no toca Salesforce.

Nunca escribe sin que el hash coincida. El login y el 2FA son manuales.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from selenium.common.exceptions import TimeoutException, WebDriverException

from browser_factory import create_driver, detect_browser, release_driver
from comment_reader import build_record_url, find_other_information
from comment_writer import prepare_other_information, save_edit_form
from correction_loader import load_corrections
from local_audit import capture_failure, create_logger, mask_lead_id
from run_document_queue import (
    record_result,
    results_path_for,
    verify_saved_value,
)
from salesforce_session import (
    ROOT,
    load_config,
    local_path,
    prompt_for_manual_authentication,
    wait_for_lightning_ready,
)
from snapshot_store import content_hash, record_snapshot, snapshot_path_for


def correction_entry(lead_id: str, status: str) -> dict:
    return {
        "lead_id": lead_id,
        "status": status,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("Uso: python run_corrections.py ui_output/<correcciones>.json")
        return 2

    corrections_path = argv[0]
    config = load_config()
    try:
        # Validar antes de abrir Edge evita una sesión innecesaria.
        corrections = load_corrections(corrections_path)
    except ValueError as error:
        print(f"Cola de correcciones inválida: {error}")
        return 2

    results_path = results_path_for(corrections_path)
    ui_output_directory = ROOT / config.get("ui_output_directory", "ui_output")
    snapshot_path = snapshot_path_for(corrections_path, ui_output_directory)
    stats = {"corregido": 0, "conflicto": 0, "error": 0}
    logger = create_logger(ROOT / config["log_directory"])
    screenshot_directory = ROOT / config["screenshot_directory"]
    browser, executable = detect_browser(config["browser"])
    profile_directory = local_path(config["profile_directory"])
    driver = create_driver(
        browser,
        executable,
        profile_directory,
        config.get("debugger_address", "127.0.0.1:9222"),
    )
    if getattr(driver, "attached_to_persistent_browser", False):
        print("Conectado al navegador persistente abierto.")
    timeout_seconds = config["timeouts"]["page_load_seconds"]

    try:
        prompt_for_manual_authentication(driver, config)
        for index, correction in enumerate(corrections, start=1):
            lead_id = correction["lead_id"]
            print(f"\n=== Corrección {index}/{len(corrections)} ===")
            print(f"Lead ID: {lead_id}")
            record_url = build_record_url(
                config["salesforce_url"],
                lead_id,
                config.get("record_object_api_name", "Lead"),
            )
            try:
                # Salesforce manda: solo se escribe si el valor actual sigue
                # siendo el que la UI confirmó (mismo hash).
                driver.get(record_url)
                wait_for_lightning_ready(driver, timeout_seconds)
                current_value = find_other_information(driver, timeout_seconds)
            except (ValueError, TimeoutException, WebDriverException) as error:
                stats["error"] += 1
                screenshot = capture_failure(driver, screenshot_directory, "correccion_error")
                logger.error(
                    "Error leyendo Lead para corrección: lead=%s captura=%s motivo=%s",
                    mask_lead_id(lead_id), screenshot.name, error,
                )
                print("No se pudo leer el Lead. Captura local guardada.")
                record_result(results_path, correction_entry(lead_id, "error"))
                continue

            if content_hash(current_value) != correction["base_hash"]:
                # Alguien o algo cambió el campo desde la copia base: no se toca.
                stats["conflicto"] += 1
                logger.warning(
                    "Conflicto de corrección (hash distinto, sin escritura): lead=%s",
                    mask_lead_id(lead_id),
                )
                print("Conflicto: el campo cambió desde la copia base. No se modificó Salesforce.")
                record_result(results_path, correction_entry(lead_id, "conflicto"))
                continue

            try:
                prepare_other_information(driver, correction["new_value"], timeout_seconds)
                save_edit_form(driver, timeout_seconds)
                saved, persisted_length = verify_saved_value(
                    driver, record_url, correction["new_value"], timeout_seconds
                )
                if not saved:
                    raise ValueError(
                        "La corrección no se verificó al releer el registro "
                        f"(esperados={len(correction['new_value'])} leidos={persisted_length})."
                    )
            except (ValueError, TimeoutException, WebDriverException) as error:
                stats["error"] += 1
                screenshot = capture_failure(driver, screenshot_directory, "correccion_error")
                logger.error(
                    "Error aplicando corrección: lead=%s captura=%s motivo=%s",
                    mask_lead_id(lead_id), screenshot.name, error,
                )
                print("No se pudo aplicar la corrección. Captura local guardada.")
                record_result(results_path, correction_entry(lead_id, "error"))
                continue

            stats["corregido"] += 1
            # El snapshot confirmado se actualiza solo localmente.
            record_snapshot(
                snapshot_path,
                lead_id,
                find_other_information(driver, timeout_seconds),
            )
            logger.info("Corrección aplicada y verificada: lead=%s", mask_lead_id(lead_id))
            print("Corregido y verificado.")
            record_result(results_path, correction_entry(lead_id, "corregido"))
    finally:
        release_driver(driver)

    print(
        f"\nResumen: {stats['corregido']} corregidos, "
        f"{stats['conflicto']} conflictos, {stats['error']} errores."
    )
    print(f"Resultados: {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
