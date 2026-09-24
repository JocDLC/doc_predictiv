from __future__ import annotations

from selenium.common.exceptions import TimeoutException

from browser_factory import create_driver, detect_browser, release_driver
from local_audit import capture_failure, create_logger
from local_report import write_unassigned_leads_report
from report_reader import read_visible_unassigned_leads, report_accessibility_summary
from salesforce_session import (
    ROOT,
    load_config,
    local_path,
    prompt_for_manual_authentication,
    wait_for_lightning_ready,
)


def print_report_summary(visible_row_count: int, leads) -> None:
    identified_leads = [lead for lead in leads if lead.lead_id]
    print(f"Filas visibles: {visible_row_count}")
    print(f"Leads con AR_LEAD_QUALIF: {len(identified_leads)}")
    print("Lead IDs:")
    for lead in identified_leads:
        print(lead.lead_id)


def main() -> None:
    config = load_config()
    log_directory = ROOT / config["log_directory"]
    screenshot_directory = ROOT / config["screenshot_directory"]
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

    try:
        prompt_for_manual_authentication(driver, config)
        driver.get(config["report_url"])
        wait_for_lightning_ready(driver, timeout_seconds)
        visible_row_count, leads = read_visible_unassigned_leads(
            driver,
            timeout_seconds,
            config.get("record_object_api_name", "Lead"),
        )
        report_path = write_unassigned_leads_report(
            visible_row_count,
            leads,
            ROOT / config.get("queue_directory", "queues"),
        )
        logger.info(
            "Lectura de reporte completada: filas_visibles=%d leads_sin_gestion=%d reporte=%s",
            visible_row_count,
            len(leads),
            report_path.name,
        )
        print_report_summary(visible_row_count, leads)
    except TimeoutException:
        screenshot = capture_failure(driver, screenshot_directory, "report_timeout")
        logger.error(
            "Timeout durante la lectura del reporte. Captura: %s. Estructura: %s",
            screenshot.name,
            report_accessibility_summary(driver),
        )
        print("No se pudo leer el reporte dentro del tiempo configurado.")
    except KeyboardInterrupt:
        logger.info("Lectura de reporte interrumpida por el usuario")
        print("Lectura de reporte interrumpida.")
    finally:
        release_driver(driver)


if __name__ == "__main__":
    main()
