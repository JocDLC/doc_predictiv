from __future__ import annotations

from selenium.common.exceptions import TimeoutException

from browser_factory import create_driver, detect_browser
from comment_reader import (
    build_record_url,
    find_other_information,
    next_attempt_number,
    other_information_structure_summary,
)
from local_audit import capture_failure, create_logger, mask_lead_id
from salesforce_session import (
    ROOT,
    load_config,
    local_path,
    prompt_for_manual_authentication,
    wait_for_lightning_ready,
)


def print_comment_summary(
    lead_id: str,
    field_found: bool,
    comment_length: int,
    next_int: int,
) -> None:
    print(f"Lead ID: {lead_id}")
    print(f"Campo 'Otra información' encontrado: {'sí' if field_found else 'no'}")
    print(f"Cantidad de caracteres: {comment_length}")
    print(f"Próximo INT: {next_int}")


def main() -> None:
    config = load_config()
    log_directory = ROOT / config["log_directory"]
    screenshot_directory = ROOT / config["screenshot_directory"]
    logger = create_logger(log_directory)
    browser, executable = detect_browser(config["browser"])
    profile_directory = local_path(config["profile_directory"])
    driver = create_driver(browser, executable, profile_directory)
    timeout_seconds = config["timeouts"]["page_load_seconds"]
    lead_id = ""

    try:
        prompt_for_manual_authentication(driver, config)
        lead_id = input("Ingresá el Lead ID a revisar: ").strip()
        record_url = build_record_url(
            config["salesforce_url"],
            lead_id,
            config.get("record_object_api_name", "Lead"),
        )
        driver.get(record_url)
        wait_for_lightning_ready(driver, timeout_seconds)
        comment = find_other_information(driver, timeout_seconds)
        next_int = next_attempt_number(comment)
        if not comment:
            screenshot = capture_failure(
                driver,
                screenshot_directory,
                "other_information_empty",
            )
            logger.warning(
                "Campo Otra información encontrado sin texto. captura=%s estructura=%s",
                screenshot.name,
                other_information_structure_summary(driver),
            )
        logger.info(
            "Lectura de Otra información: lead=%s campo_encontrado=True caracteres=%d proximo_int=%d",
            mask_lead_id(lead_id),
            len(comment),
            next_int,
        )
        print_comment_summary(lead_id, True, len(comment), next_int)
    except ValueError as error:
        logger.warning("Lead ID inválido: lead=%s", mask_lead_id(lead_id))
        print(f"No se pudo iniciar la lectura: {error}")
    except TimeoutException:
        screenshot = capture_failure(driver, screenshot_directory, "other_information_timeout")
        logger.error(
            "Timeout al leer Otra información: lead=%s captura=%s",
            mask_lead_id(lead_id),
            screenshot.name,
        )
        print("No se pudo localizar 'Otra información' dentro del tiempo configurado.")
    except KeyboardInterrupt:
        logger.info("Lectura de Otra información interrumpida por el usuario")
        print("Lectura de Otra información interrumpida.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
