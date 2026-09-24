from __future__ import annotations

from selenium.common.exceptions import TimeoutException, WebDriverException

from browser_factory import create_driver, detect_browser, release_driver
from comment_reader import build_record_url, find_other_information, next_attempt_number
from comment_writer import (
    compose_other_information,
    load_draft_body,
    prepare_other_information,
)
from local_audit import capture_failure, create_logger, mask_lead_id
from salesforce_session import (
    ROOT,
    load_config,
    local_path,
    prompt_for_manual_authentication,
    wait_for_lightning_ready,
)

DEFAULT_QUEUE_DIRECTORY = "queues"


def queue_directory_from_config(config: dict):
    return ROOT / config.get("queue_directory", DEFAULT_QUEUE_DIRECTORY)


def print_preparation_summary(
    lead_id: str,
    previous_length: int,
    next_int: int,
    prepared_length: int,
) -> None:
    print(f"Lead ID: {lead_id}")
    print(f"Caracteres previos: {previous_length}")
    print(f"Próximo INT: {next_int}")
    print(f"Caracteres preparados: {prepared_length}")


def confirm_preparation() -> bool:
    confirmation = input(
        "Se abrirá y completará únicamente 'Otra información', sin guardar. "
        "Escribí PREPARAR para continuar: "
    )
    return confirmation.strip() == "PREPARAR"


def main() -> None:
    config = load_config()
    log_directory = ROOT / config["log_directory"]
    screenshot_directory = ROOT / config["screenshot_directory"]
    queue_directory = queue_directory_from_config(config)
    logger = create_logger(log_directory)
    browser, executable = detect_browser(config["browser"])
    profile_directory = local_path(config["profile_directory"])
    driver = create_driver(
        browser,
        executable,
        profile_directory,
        config.get("debugger_address", "127.0.0.1:9222"),
    )
    timeout_seconds = config["timeouts"]["page_load_seconds"]
    lead_id = ""

    try:
        prompt_for_manual_authentication(driver, config)
        lead_id = input("Ingresá el Lead ID a preparar: ").strip()
        draft_path = input("Ingresá la ruta del borrador local dentro de queues/: ").strip()
        draft_body = load_draft_body(draft_path, queue_directory)
        record_url = build_record_url(
            config["salesforce_url"],
            lead_id,
            config.get("record_object_api_name", "Lead"),
        )
        driver.get(record_url)
        wait_for_lightning_ready(driver, timeout_seconds)
        existing_comment = find_other_information(driver, timeout_seconds)
        next_int = next_attempt_number(existing_comment)
        prepared_comment = compose_other_information(
            existing_comment,
            next_int,
            draft_body,
        )
        print_preparation_summary(
            lead_id,
            len(existing_comment),
            next_int,
            len(prepared_comment),
        )
        if not confirm_preparation():
            logger.info(
                "Preparación cancelada antes de editar: lead=%s proximo_int=%d",
                mask_lead_id(lead_id),
                next_int,
            )
            print("Preparación cancelada. Salesforce no fue modificado.")
            return

        prepare_other_information(driver, prepared_comment, timeout_seconds)
        logger.info(
            "Borrador cargado sin guardado automático: lead=%s caracteres_previos=%d proximo_int=%d caracteres_preparados=%d",
            mask_lead_id(lead_id),
            len(existing_comment),
            next_int,
            len(prepared_comment),
        )
        input(
            "Borrador cargado. Revisalo en Salesforce y elegí manualmente Guardar o Cancelar. "
            "Cuando termines, presioná Enter aquí: "
        )
        print("La decisión de guardar o cancelar fue exclusivamente manual.")
    except ValueError as error:
        logger.warning("Preparación rechazada: lead=%s motivo=%s", mask_lead_id(lead_id), error)
        print(f"No se pudo preparar el borrador: {error}")
    except (TimeoutException, WebDriverException):
        screenshot = capture_failure(driver, screenshot_directory, "assisted_preparation_error")
        logger.error(
            "Error al preparar Otra información: lead=%s captura=%s",
            mask_lead_id(lead_id),
            screenshot.name,
        )
        print("No se pudo preparar el borrador. Se guardó una captura local de diagnóstico.")
    finally:
        release_driver(driver)


if __name__ == "__main__":
    main()
