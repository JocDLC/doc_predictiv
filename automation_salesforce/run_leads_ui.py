from __future__ import annotations

import sys
import webbrowser

from selenium.common.exceptions import TimeoutException

from browser_factory import create_driver, detect_browser, release_driver
from leads_ui import write_leads_ui
from local_audit import capture_failure, create_logger
from local_report import write_unassigned_leads_report
from report_reader import (
    read_full_report,
    read_visible_unassigned_leads,
    report_accessibility_summary,
)
from salesforce_session import (
    ROOT,
    load_config,
    local_path,
    prompt_for_manual_authentication,
    wait_for_lightning_ready,
)


def scan_mode(arguments: list[str]) -> tuple[str, int]:
    """`--completo` recorre toda la bandeja; por defecto solo lo cargado en pantalla."""
    return ("completo", 80) if "--completo" in arguments else ("rapido", 1)


def read_report(
    driver,
    timeout_seconds: int,
    record_object_api_name: str,
    field_aliases: dict[str, list[str]],
    diagnostics: list[dict[str, object]],
    mode: str,
    vertical_passes: int,
) -> tuple[int, list]:
    """Lee la vista actual por defecto; el recorrido ampliado es explícito."""
    if mode == "rapido":
        return read_visible_unassigned_leads(
            driver,
            timeout_seconds,
            record_object_api_name,
            field_aliases,
            diagnostics,
        )
    return read_full_report(
        driver,
        timeout_seconds,
        record_object_api_name,
        field_aliases,
        diagnostics,
        max_vertical_passes=vertical_passes,
    )


def main() -> None:
    mode, vertical_passes = scan_mode(sys.argv[1:])
    config = load_config()
    logger = create_logger(ROOT / config["log_directory"])
    screenshot_directory = ROOT / config["screenshot_directory"]
    browser, executable = detect_browser(config["browser"])
    driver = create_driver(
        browser,
        executable,
        local_path(config["profile_directory"]),
        config.get("debugger_address", "127.0.0.1:9222"),
    )
    timeout_seconds = config["timeouts"]["page_load_seconds"]

    try:
        prompt_for_manual_authentication(driver, config)
        driver.get(config["report_url"])
        wait_for_lightning_ready(driver, timeout_seconds)
        diagnostics: list[dict[str, object]] = []
        visible_row_count, leads = read_report(
            driver,
            timeout_seconds,
            config.get("record_object_api_name", "Lead"),
            config.get("lead_list_fields", {}),
            diagnostics,
            mode,
            vertical_passes,
        )
        print(f"Modo de lectura: {mode}")
        header_diagnostics = [item for item in diagnostics if "headers" in item]
        logger.info(
            "Diagnóstico de columnas: pasadas=%d encabezados=%s campos_resueltos=%s",
            len(header_diagnostics),
            header_diagnostics[0]["headers"] if header_diagnostics else [],
            sorted({name for item in header_diagnostics for name in item["resolved_fields"]}),
        )
        if not leads:
            row_diagnostics = [item for item in diagnostics if "owner_found" in item]
            logger.warning(
                "Sin Leads detectados. filas_con_propietario=%d filas_con_id=%d estructura=%s diagnostico=%s",
                sum(item["owner_found"] for item in row_diagnostics),
                sum(item["lead_id_found"] for item in row_diagnostics),
                report_accessibility_summary(driver),
                row_diagnostics,
            )
        report_path = write_unassigned_leads_report(
            visible_row_count,
            leads,
            ROOT / config.get("queue_directory", "queues"),
        )
        ui_path = write_leads_ui(
            visible_row_count,
            leads,
            ROOT / config.get("ui_output_directory", "ui_output"),
        )
        logger.info(
            "UI de Leads creada: filas_visibles=%d leads_sin_gestion=%d reporte=%s ui=%s",
            visible_row_count,
            len(leads),
            report_path.name,
            ui_path.name,
        )
        print(f"Filas visibles: {visible_row_count}")
        print(f"Leads con AR_LEAD_QUALIF: {len(leads)}")
        print("La UI local se abre en el navegador predeterminado.")
        webbrowser.open(ui_path.as_uri())
        input("Presioná Enter para cerrar Edge: ")
    except TimeoutException:
        screenshot = capture_failure(driver, screenshot_directory, "leads_ui_timeout")
        logger.error(
            "Timeout al generar la UI. captura=%s estructura=%s",
            screenshot.name,
            report_accessibility_summary(driver),
        )
        print("No se pudo leer el reporte dentro del tiempo configurado.")
    except KeyboardInterrupt:
        logger.info("Generación de UI interrumpida por el usuario")
        print("Generación de UI interrumpida.")
    finally:
        release_driver(driver)


if __name__ == "__main__":
    main()
