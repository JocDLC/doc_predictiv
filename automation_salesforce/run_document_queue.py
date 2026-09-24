"""Prepara una cola de documentación en Salesforce, supervisada o automática.

Sin `--auto`: deja el borrador cargado y espera que el operador elija Guardar o
Cancelar a mano en Salesforce antes de continuar. Con `--auto`: pulsa Guardar,
reabre el Lead y verifica que el texto quedó persistido antes de seguir.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException

from browser_factory import create_driver, detect_browser, release_driver
from comment_reader import build_record_url, find_other_information, next_attempt_number
from comment_writer import (
    compose_attempts,
    find_editor_control,
    prepare_other_information,
    save_edit_form,
)
from local_audit import capture_failure, create_logger, mask_lead_id
from queue_loader import load_queue
from salesforce_session import (
    ROOT,
    load_config,
    local_path,
    prompt_for_manual_authentication,
    wait_for_lightning_ready,
)
from snapshot_store import record_snapshot, snapshot_path_for

DEFAULT_QUEUE_DIRECTORY = "queues"
# Entradas explícitas del operador antes de preparar cada borrador.
ACTIONS = {"preparar": "preparar", "s": "omitir", "q": "terminar"}


def queue_directory_from_config(config: dict) -> Path:
    return ROOT / config.get("queue_directory", DEFAULT_QUEUE_DIRECTORY)


def results_path_for(queue_path: str) -> Path:
    """Mantiene los resultados junto a la cola, fuera del repositorio."""
    return Path(queue_path).expanduser().resolve().with_suffix(".resultado.json")


def result_entry(lead_id: str, status: str, next_int: int, attempts_count: int) -> dict:
    return {
        "lead_id": lead_id,
        "status": status,
        "next_int": next_int,
        "attempts": attempts_count,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def record_result(results_path: Path, entry: dict) -> None:
    """Persiste el último estado de cada Lead para poder reanudar la revisión."""
    results = {}
    if results_path.exists():
        try:
            # Un resultado nuevo reemplaza el anterior del mismo Lead, sin duplicarlo.
            for item in json.loads(results_path.read_text(encoding="utf-8")):
                results[item["lead_id"]] = item
        except (json.JSONDecodeError, KeyError, TypeError):
            results = {}
    results[entry["lead_id"]] = entry
    results_path.write_text(
        json.dumps(list(results.values()), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def print_lead_summary(
    lead_id: str,
    previous_length: int,
    next_int: int,
    attempts_count: int,
    prepared_length: int,
) -> None:
    """Muestra solo métricas operativas; nunca imprime el comentario preparado."""
    print(f"Lead ID: {lead_id}")
    print(f"Caracteres previos: {previous_length}")
    print(f"Próximo INT: {next_int}")
    print(f"Intentos nuevos: {attempts_count}")
    print(f"Caracteres finales: {prepared_length}")


def ask_lead_action() -> str:
    """Obliga una elección explícita antes de abrir el editor del Lead."""
    while True:
        answer = input(
            "Escribí PREPARAR para cargar el borrador, 's' para omitir o 'q' para terminar: "
        ).strip().lower()
        if answer in ACTIONS:
            return ACTIONS[answer]
        print("Respuesta no válida.")


def normalize_persisted_text(value: str) -> str:
    """Iguala diferencias de solo-forma entre el texto escrito y el mostrado.

    En modo lectura Salesforce renderiza el campo con whitespace colapsado
    (cada TAB se ve como un espacio), así que la comparación tolera cualquier
    corrida de espacios/tabs como un único separador y unifica saltos de línea.
    """
    lines = str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(" ".join(line.split()) for line in lines).rstrip()


def verify_saved_value(
    driver,
    record_url: str,
    expected: str,
    timeout_seconds: int,
    retries: int = 2,
    delay_seconds: float = 2.0,
) -> tuple[bool, int]:
    """Confirma que Otra información quedó persistida tras el guardado.

    La primera lectura se hace en la misma página: tras Guardar, el campo en
    modo lectura ya muestra el valor persistido, sin costo de recarga. Solo si
    no coincide recarga el registro una vez y reintenta (la recarga puede traer
    datos cacheados apenas se reabre). Devuelve (verificado, longitud del
    último valor leído) para diagnosticar sin exponer el contenido.
    """
    expected_text = normalize_persisted_text(expected)
    persisted_length = -1
    for attempt in range(retries):
        if attempt > 0:
            time.sleep(delay_seconds)
            driver.get(record_url)
            wait_for_lightning_ready(driver, timeout_seconds)
        persisted = find_other_information(driver, timeout_seconds)
        persisted_length = len(persisted)
        if normalize_persisted_text(persisted) == expected_text:
            return True, persisted_length
    return False, persisted_length


def parse_queue_args(argv: list[str]) -> tuple[str, bool]:
    queue_args = [arg for arg in argv if arg != "--auto"]
    return (queue_args[0] if queue_args else "", "--auto" in argv)


def wait_for_manual_decision(driver) -> None:
    """Evita navegar al siguiente Lead mientras el editor actual siga abierto."""
    while True:
        input(
            "Borrador cargado. Revisalo en Salesforce, elegí Guardar o Cancelar "
            "y presioná Enter aquí: "
        )
        if not find_editor_control(driver):
            return
        print("El editor de 'Otra información' sigue abierto. Guardá o cancelá antes de continuar.")


def fail_lead(driver, screenshot_directory, logger, results_path, lead_id, next_int, attempts_count, reason):
    """Registra un fallo sin exponer el texto ni detener el resto de la cola."""
    screenshot = capture_failure(driver, screenshot_directory, "queue_error")
    logger.error(
        "Error procesando Lead: lead=%s captura=%s motivo=%s",
        mask_lead_id(lead_id),
        screenshot.name,
        reason,
    )
    print("No se pudo procesar el Lead. Captura local guardada; revisalo a mano.")
    record_result(results_path, result_entry(lead_id, "error", next_int, attempts_count))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    queue_path, auto_mode = parse_queue_args(argv)
    if not queue_path:
        print("Uso: python run_document_queue.py [--auto] queues/<cola>.json")
        return 2

    config = load_config()
    queue_directory = queue_directory_from_config(config)
    try:
        # Validar antes de abrir Edge evita una sesión innecesaria para una cola inválida.
        leads = load_queue(queue_path, queue_directory)
    except ValueError as error:
        print(f"Cola inválida: {error}")
        return 2

    results_path = results_path_for(queue_path)
    snapshot_path = snapshot_path_for(
        queue_path,
        ROOT / config.get("ui_output_directory", "ui_output"),
    )
    stats = {"preparado": 0, "guardado": 0, "omitido": 0, "error": 0}
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
        for index, lead in enumerate(leads, start=1):
            lead_id = lead["lead_id"]
            attempts = lead["attempts"]
            print(f"\n=== Lead {index}/{len(leads)} ===")
            next_int = 0
            try:
                # Salesforce es la fuente de verdad para la numeración del próximo INT.
                record_url = build_record_url(
                    config["salesforce_url"],
                    lead_id,
                    config.get("record_object_api_name", "Lead"),
                )
                driver.get(record_url)
                wait_for_lightning_ready(driver, timeout_seconds)
                existing_comment = find_other_information(driver, timeout_seconds)
                next_int = next_attempt_number(existing_comment)
                prepared = compose_attempts(existing_comment, next_int, attempts)
            except (ValueError, TimeoutException, WebDriverException) as error:
                stats["error"] += 1
                fail_lead(
                    driver, screenshot_directory, logger, results_path,
                    lead_id, next_int, len(attempts), error,
                )
                continue

            print_lead_summary(
                lead_id, len(existing_comment), next_int, len(attempts), len(prepared)
            )
            if not auto_mode:
                action = ask_lead_action()
                if action == "terminar":
                    print("Cola interrumpida por el operador.")
                    break
                if action == "omitir":
                    stats["omitido"] += 1
                    logger.info("Lead omitido por el operador: lead=%s", mask_lead_id(lead_id))
                    record_result(results_path, result_entry(lead_id, "omitido", next_int, len(attempts)))
                    continue

            try:
                # Solo carga el borrador; Guardar o Cancelar siguen siendo manuales
                # salvo en modo --auto.
                prepare_other_information(driver, prepared, timeout_seconds)
            except (ValueError, TimeoutException, WebDriverException) as error:
                stats["error"] += 1
                fail_lead(
                    driver, screenshot_directory, logger, results_path,
                    lead_id, next_int, len(attempts), error,
                )
                continue

            if auto_mode:
                try:
                    save_edit_form(driver, timeout_seconds)
                    saved, persisted_length = verify_saved_value(
                        driver, record_url, prepared, timeout_seconds
                    )
                except (ValueError, TimeoutException, WebDriverException) as error:
                    stats["error"] += 1
                    fail_lead(
                        driver, screenshot_directory, logger, results_path,
                        lead_id, next_int, len(attempts), error,
                    )
                    continue
                if not saved:
                    stats["error"] += 1
                    fail_lead(
                        driver, screenshot_directory, logger, results_path,
                        lead_id, next_int, len(attempts),
                        ValueError(
                            "El guardado no se verificó al releer el registro "
                            f"(esperados={len(prepared)} leidos={persisted_length})."
                        ),
                    )
                    continue
                stats["guardado"] += 1
                # El snapshot se guarda solo localmente; el resultado no contiene texto.
                record_snapshot(
                    snapshot_path,
                    lead_id,
                    find_other_information(driver, timeout_seconds),
                )
                logger.info(
                    "Lead guardado y verificado: lead=%s proximo_int=%d intentos=%d",
                    mask_lead_id(lead_id),
                    next_int,
                    len(attempts),
                )
                record_result(results_path, result_entry(lead_id, "guardado", next_int, len(attempts)))
                continue

            logger.info(
                "Borrador cargado sin guardado: lead=%s proximo_int=%d intentos=%d",
                mask_lead_id(lead_id),
                next_int,
                len(attempts),
            )
            wait_for_manual_decision(driver)
            stats["preparado"] += 1
            record_result(results_path, result_entry(lead_id, "preparado", next_int, len(attempts)))
    finally:
        # Libera únicamente el driver que este runner creó o al que se adjuntó.
        release_driver(driver)

    print(
        f"\nResumen: {stats['guardado']} guardados, {stats['preparado']} preparados, "
        f"{stats['omitido']} omitidos, {stats['error']} errores."
    )
    print(f"Resultados: {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
