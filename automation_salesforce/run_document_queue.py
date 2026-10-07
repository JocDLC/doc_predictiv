"""Prepara una cola de documentación en Salesforce, supervisada o automática.

Sin `--auto`: deja el borrador cargado y espera que el operador elija Guardar o
Cancelar a mano en Salesforce antes de continuar. Con `--auto`: pulsa Guardar,
reabre el Lead y verifica que el texto quedó persistido antes de seguir.
"""

from __future__ import annotations

import json
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException

from attempt_identity import partition_attempts
from browser_factory import create_driver, detect_browser, release_driver
from comment_reader import (
    OTHER_INFORMATION_LABELS,
    build_record_url,
    find_field_text,
    find_field_value,
    find_other_information,
    is_duplicate_lead,
    next_attempt_number,
)

from comment_writer import (
    compose_attempts,
    find_editor_control,
    prepare_other_information,
    save_edit_form,
)
from country_fields import field_display, field_key, field_labels, normalize_country
from local_audit import capture_failure, create_logger, mask_lead_id
from productivity_metrics import (
    metrics_path_for,
    round_elapsed_seconds,
    summarize_results,
    write_metrics,
)
from queue_loader import load_queue_file
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


def result_entry(
    lead_id: str,
    status: str,
    next_int: int,
    attempts_count: int,
    elapsed_seconds: float | None = None,
    stage_seconds: dict[str, float] | None = None,
    verify_reloads: int = 0,
    extra: dict | None = None,
) -> dict:
    entry = {
        "lead_id": lead_id,
        "status": status,
        "next_int": next_int,
        "attempts": attempts_count,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if extra:
        entry.update(extra)
    if elapsed_seconds is not None:
        entry["elapsed_seconds"] = round_elapsed_seconds(elapsed_seconds)
    if stage_seconds:
        entry["stage_seconds"] = {stage: round_elapsed_seconds(duration) for stage, duration in stage_seconds.items()}
    if verify_reloads:
        entry["verify_reloads"] = verify_reloads
    return entry


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
        answer = (
            input("Escribí PREPARAR para cargar el borrador, 's' para omitir o 'q' para terminar: ").strip().lower()
        )
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
    labels: tuple[str, ...] = (),
) -> tuple[bool, int]:
    """Confirma que el campo de intentos quedó persistido tras el guardado.

    La primera lectura se hace en la misma página: tras Guardar, el campo en
    modo lectura ya muestra el valor persistido, sin costo de recarga. Solo si
    no coincide recarga el registro una vez y reintenta (la recarga puede traer
    datos cacheados apenas se reabre). Devuelve (verificado, longitud del
    último valor leído, recargas de respaldo usadas) para diagnosticar sin
    exponer el contenido.
    """
    expected_text = normalize_persisted_text(expected)
    persisted_length = -1
    reloads = 0
    for attempt in range(retries):
        if attempt > 0:
            reloads += 1
            time.sleep(delay_seconds)
            driver.get(record_url)
            wait_for_lightning_ready(driver, timeout_seconds)
        persisted = (
            find_other_information(driver, timeout_seconds)
            if not labels
            else find_field_value(driver, timeout_seconds, labels)
        )
        persisted_length = len(persisted)
        if normalize_persisted_text(persisted) == expected_text:
            return True, persisted_length, reloads
    return False, persisted_length, reloads


OPTION_ARGS = ("--run-id", "--results", "--snapshots", "--metrics")


def parse_queue_args(argv: list[str]) -> tuple[str, bool, dict[str, str]]:
    """Admite ``--auto``, ``--run-id`` y rutas de salida sobreescritas.

    Las rutas opcionales permiten que el servidor ejecute una copia inmutable
    de la cola mientras los artefactos activos siguen recibiendo el progreso
    en vivo para el polling de la UI.
    """
    auto_mode = "--auto" in argv
    options: dict[str, str] = {}
    positional: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--auto":
            index += 1
            continue
        if arg in OPTION_ARGS and index + 1 < len(argv):
            options[arg[2:].replace("-", "_")] = argv[index + 1]
            index += 2
            continue
        if not arg.startswith("--"):
            positional.append(arg)
        index += 1
    return (positional[0] if positional else "", auto_mode, options)


def output_override(value: str, base_directory: Path, label: str) -> Path | None:
    """Valida que una ruta de salida alternativa siga dentro de su carpeta."""
    if not value:
        return None
    candidate = Path(value).expanduser().resolve()
    if candidate.parent != base_directory.resolve():
        raise ValueError(f"La ruta de {label} debe estar dentro de {base_directory.name}.")
    return candidate


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{stamp}_{secrets.token_hex(3)}"


def wait_for_manual_decision(driver, labels: tuple[str, ...] = (), display_name: str = "Otra información") -> None:
    """Evita navegar al siguiente Lead mientras el editor actual siga abierto."""
    while True:
        input("Borrador cargado. Revisalo en Salesforce, elegí Guardar o Cancelar y presioná Enter aquí: ")
        if not find_editor_control(driver, labels or OTHER_INFORMATION_LABELS):
            return
        print(f"El editor de '{display_name}' sigue abierto. Guardá o cancelá antes de continuar.")


def fail_lead(
    driver,
    screenshot_directory,
    logger,
    results_path,
    lead_id,
    next_int,
    attempts_count,
    reason,
    elapsed_seconds: float | None = None,
    stage_seconds: dict[str, float] | None = None,
    verify_reloads: int = 0,
    extra: dict | None = None,
) -> dict:
    """Registra un fallo sin exponer el texto ni detener el resto de la cola."""
    screenshot = capture_failure(driver, screenshot_directory, "queue_error")
    # Las excepciones de Selenium suelen tener mensaje vacío ("Message:"); el
    # tipo (TimeoutException, StaleElementReference…) es lo que diagnostica.
    reason_text = (
        f"{type(reason).__name__}: {reason}" if isinstance(reason, Exception) else str(reason)
    )
    logger.error(
        "Error procesando Lead: lead=%s captura=%s motivo=%s",
        mask_lead_id(lead_id),
        screenshot.name,
        reason_text,
    )
    print("No se pudo procesar el Lead. Captura local guardada; revisalo a mano.")
    entry = result_entry(
        lead_id,
        "error",
        next_int,
        attempts_count,
        elapsed_seconds,
        stage_seconds,
        verify_reloads,
        extra,
    )
    record_result(results_path, entry)
    return entry


def lead_context(run_id: str, source_file: str, attempts: list[dict[str, str]]) -> dict:
    """Identidad de la tanda para cada resultado: qué llamadas se pidieron."""
    return {
        "run_id": run_id,
        "source_file": source_file,
        "request_call_ids": [attempt["call_id"] for attempt in attempts if attempt.get("call_id")],
        "documented_call_ids": [],
        "added_call_ids": [],
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    queue_path, auto_mode, options = parse_queue_args(argv)
    if not queue_path:
        print("Uso: python run_document_queue.py [--auto] [--run-id <id>] queues/<cola>.json")
        return 2

    config = load_config()
    queue_directory = queue_directory_from_config(config)
    ui_output_directory = ROOT / config.get("ui_output_directory", "ui_output")
    try:
        # Validar antes de abrir Edge evita una sesión innecesaria para una cola inválida.
        queue_file = load_queue_file(queue_path, queue_directory)
        leads = queue_file["leads"]
        results_path = output_override(options.get("results", ""), queue_directory, "resultados")
        snapshot_path = output_override(options.get("snapshots", ""), ui_output_directory, "snapshots")
        metrics_path = output_override(options.get("metrics", ""), queue_directory, "métricas")
    except ValueError as error:
        print(f"Cola inválida: {error}")
        return 2

    results_path = results_path or results_path_for(queue_path)
    snapshot_path = snapshot_path or snapshot_path_for(queue_path, ui_output_directory)
    run_id = options.get("run_id") or queue_file["run_id"] or new_run_id()
    source_file = queue_file["source_file"]
    # El modo de país viene congelado en la cola y decide el campo físico.
    country = normalize_country(queue_file["country"])
    attempt_labels = field_labels(country, "attempts")
    attempt_display = field_display(country, "attempts")
    attempt_field_key = field_key(country, "attempts")
    closure_labels = field_labels(country, "closure")

    def read_attempts(current_driver, timeout):
        # El camino histórico (Otra información) queda intacto para Argentina.
        if not attempt_labels or attempt_labels == OTHER_INFORMATION_LABELS:
            return find_other_information(current_driver, timeout)
        return find_field_value(current_driver, timeout, attempt_labels)
    stats = {
        "preparado": 0,
        "guardado": 0,
        "parcial": 0,
        "ya_documentado": 0,
        "revision": 0,
        "duplicado": 0,
        "omitido": 0,
        "error": 0,
    }
    batch_results: list[dict] = []
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

    def fail(extra=None, **kwargs):
        return fail_lead(driver, screenshot_directory, logger, results_path, extra=extra, **kwargs)

    try:
        prompt_for_manual_authentication(driver, config)
        batch_started_at = time.monotonic()
        for index, lead in enumerate(leads, start=1):
            lead_id = lead["lead_id"]
            attempts = lead["attempts"]
            context = lead_context(run_id, source_file, attempts)
            context["country"] = country
            print(f"\n=== Lead {index}/{len(leads)} ===")
            next_int = 0
            stage_seconds: dict[str, float] = {}
            lead_started_at = time.monotonic()
            try:
                # Salesforce es la fuente de verdad para la numeración del próximo INT.
                record_url = build_record_url(
                    config["salesforce_url"],
                    lead_id,
                    config.get("record_object_api_name", "Lead"),
                )
                stage_started_at = time.monotonic()
                driver.get(record_url)
                wait_for_lightning_ready(driver, timeout_seconds)
                stage_seconds["navigation"] = time.monotonic() - stage_started_at
                stage_started_at = time.monotonic()
                # La marca "Lead duplicado" puede quedar en cualquiera de los
                # dos campos según el país; se revisan ambos sin espera.
                duplicate = is_duplicate_lead(find_field_text(driver, closure_labels))
                stage_seconds["comment_check"] = time.monotonic() - stage_started_at
                if not duplicate:
                    stage_started_at = time.monotonic()
                    existing_comment = read_attempts(driver, timeout_seconds)
                    stage_seconds["field_read"] = time.monotonic() - stage_started_at
                    duplicate = is_duplicate_lead(existing_comment)
                if duplicate:
                    stats["duplicado"] += 1
                    duplicate_entry = result_entry(
                        lead_id,
                        "duplicado",
                        next_int,
                        len(attempts),
                        time.monotonic() - lead_started_at if auto_mode else None,
                        stage_seconds if auto_mode else None,
                        extra=context,
                    )
                    record_result(results_path, duplicate_entry)
                    if auto_mode:
                        batch_results.append(duplicate_entry)
                    logger.info("Lead duplicado omitido: lead=%s", mask_lead_id(lead_id))
                    print("Lead marcado como duplicado; no se documenta automáticamente.")
                    continue
                next_int = next_attempt_number(existing_comment)
                # Solo se escriben los call_id ausentes; los ya presentes y los
                # ambiguos (sin call_id con campo cargado) no se duplican.
                missing_attempts, present_ids, unverifiable = partition_attempts(existing_comment, attempts)
                context["documented_call_ids"] = list(present_ids)
            except (ValueError, TimeoutException, WebDriverException) as error:
                stats["error"] += 1
                failure_entry = fail(
                    lead_id=lead_id,
                    next_int=next_int,
                    attempts_count=len(attempts),
                    reason=error,
                    elapsed_seconds=time.monotonic() - lead_started_at if auto_mode else None,
                    stage_seconds=stage_seconds if auto_mode else None,
                    extra=context,
                )
                if auto_mode:
                    batch_results.append(failure_entry)
                continue

            if not missing_attempts and not unverifiable:
                stats["ya_documentado"] += 1
                entry = result_entry(
                    lead_id,
                    "ya_documentado",
                    next_int,
                    len(attempts),
                    time.monotonic() - lead_started_at if auto_mode else None,
                    stage_seconds if auto_mode else None,
                    extra=context,
                )
                record_result(results_path, entry)
                record_snapshot(
                snapshot_path,
                lead_id,
                existing_comment,
                run_id,
                field=attempt_field_key,
                country=country,
            )
                if auto_mode:
                    batch_results.append(entry)
                logger.info(
                    "Lead ya documentado: lead=%s intentos=%d",
                    mask_lead_id(lead_id),
                    len(attempts),
                )
                print("Ya documentado en Salesforce; no se escribe nada.")
                continue

            if unverifiable and not missing_attempts:
                stats["revision"] += 1
                entry = result_entry(
                    lead_id,
                    "revision",
                    next_int,
                    len(attempts),
                    time.monotonic() - lead_started_at if auto_mode else None,
                    stage_seconds if auto_mode else None,
                    extra=context,
                )
                record_result(results_path, entry)
                if auto_mode:
                    batch_results.append(entry)
                logger.info(
                    "Lead a revisión por identidad ambigua: lead=%s",
                    mask_lead_id(lead_id),
                )
                print("Identidad ambigua (intento sin call_id sobre campo no vacío); se deja para revisión.")
                continue

            prepared = compose_attempts(existing_comment, next_int, missing_attempts)
            print_lead_summary(lead_id, len(existing_comment), next_int, len(missing_attempts), len(prepared))
            if not auto_mode:
                action = ask_lead_action()
                if action == "terminar":
                    print("Cola interrumpida por el operador.")
                    break
                if action == "omitir":
                    stats["omitido"] += 1
                    logger.info("Lead omitido por el operador: lead=%s", mask_lead_id(lead_id))
                    record_result(
                        results_path,
                        result_entry(lead_id, "omitido", next_int, len(attempts), extra=context),
                    )
                    continue

            try:
                # Solo carga el borrador; Guardar o Cancelar siguen siendo manuales
                # salvo en modo --auto.
                stage_started_at = time.monotonic()
                prepare_other_information(
                    driver,
                    prepared,
                    timeout_seconds,
                    labels=attempt_labels,
                    display_name=attempt_display,
                )
                stage_seconds["editor"] = time.monotonic() - stage_started_at
            except (ValueError, TimeoutException, WebDriverException) as error:
                stats["error"] += 1
                failure_entry = fail(
                    lead_id=lead_id,
                    next_int=next_int,
                    attempts_count=len(attempts),
                    reason=error,
                    elapsed_seconds=time.monotonic() - lead_started_at if auto_mode else None,
                    stage_seconds=stage_seconds if auto_mode else None,
                    extra=context,
                )
                if auto_mode:
                    batch_results.append(failure_entry)
                continue

            if auto_mode:
                verify_reloads = 0
                try:
                    stage_started_at = time.monotonic()
                    save_edit_form(driver, timeout_seconds)
                    stage_seconds["save_settle"] = time.monotonic() - stage_started_at
                    stage_started_at = time.monotonic()
                    saved, persisted_length, verify_reloads = verify_saved_value(
                        driver, record_url, prepared, timeout_seconds, labels=attempt_labels
                    )
                    stage_seconds["verification"] = time.monotonic() - stage_started_at
                except (ValueError, TimeoutException, WebDriverException) as error:
                    # El editor puede quedar cargando aunque el guardado haya
                    # terminado: recargar el registro descarta el formulario
                    # trabado y confirma el valor persistido antes de declarar
                    # error (evita falsos errores por lentitud de Salesforce).
                    stage_seconds["save_settle"] = time.monotonic() - stage_started_at
                    stage_started_at = time.monotonic()
                    try:
                        driver.get(record_url)
                        wait_for_lightning_ready(driver, timeout_seconds)
                        persisted = read_attempts(driver, timeout_seconds)
                        persisted_length = len(persisted)
                        saved = normalize_persisted_text(persisted) == normalize_persisted_text(prepared)
                    except (ValueError, TimeoutException, WebDriverException):
                        saved = False
                    stage_seconds["verification"] = time.monotonic() - stage_started_at
                    if not saved:
                        stats["error"] += 1
                        batch_results.append(
                            fail(
                                lead_id=lead_id,
                                next_int=next_int,
                                attempts_count=len(attempts),
                                reason=error,
                                elapsed_seconds=time.monotonic() - lead_started_at,
                                stage_seconds=stage_seconds,
                                extra=context,
                            )
                        )
                        continue
                if not saved:
                    stats["error"] += 1
                    batch_results.append(
                        fail(
                            lead_id=lead_id,
                            next_int=next_int,
                            attempts_count=len(attempts),
                            reason=ValueError(
                                "El guardado no se verificó al releer el registro "
                                f"(esperados={len(prepared)} leidos={persisted_length})."
                            ),
                            elapsed_seconds=time.monotonic() - lead_started_at,
                            stage_seconds=stage_seconds,
                            verify_reloads=verify_reloads,
                            extra=context,
                        )
                    )
                    continue
                written_ids = [attempt["call_id"] for attempt in missing_attempts if attempt.get("call_id")]
                context["documented_call_ids"] = list(present_ids) + written_ids
                context["added_call_ids"] = written_ids
                final_status = "parcial" if unverifiable else "guardado"
                stats[final_status] += 1
                # El snapshot se guarda solo localmente; el resultado no contiene texto.
                stage_started_at = time.monotonic()
                record_snapshot(
                    snapshot_path,
                    lead_id,
                    read_attempts(driver, timeout_seconds),
                    run_id,
                    context["documented_call_ids"],
                    field=attempt_field_key,
                    country=country,
                )
                stage_seconds["snapshot"] = time.monotonic() - stage_started_at
                logger.info(
                    "Lead %s y verificado: lead=%s proximo_int=%d intentos=%d",
                    final_status,
                    mask_lead_id(lead_id),
                    next_int,
                    len(attempts),
                )
                saved_entry = result_entry(
                    lead_id,
                    final_status,
                    next_int,
                    len(attempts),
                    time.monotonic() - lead_started_at,
                    stage_seconds,
                    verify_reloads,
                    context,
                )
                record_result(results_path, saved_entry)
                batch_results.append(saved_entry)
                continue

            logger.info(
                "Borrador cargado sin guardado: lead=%s proximo_int=%d intentos=%d",
                mask_lead_id(lead_id),
                next_int,
                len(missing_attempts),
            )
            wait_for_manual_decision(driver, attempt_labels, attempt_display)
            stats["preparado"] += 1
            record_result(
                results_path,
                result_entry(lead_id, "preparado", next_int, len(attempts), extra=context),
            )
    finally:
        # Libera únicamente el driver que este runner creó o al que se adjuntó.
        release_driver(driver)

    metrics_path = metrics_path or metrics_path_for(results_path)
    if auto_mode:
        write_metrics(
            metrics_path,
            summarize_results(batch_results, time.monotonic() - batch_started_at),
        )
    print(
        f"\nResumen: {stats['guardado']} guardados, {stats['parcial']} parciales, "
        f"{stats['ya_documentado']} ya documentados, {stats['revision']} en revisión, "
        f"{stats['duplicado']} duplicados, {stats['preparado']} preparados, "
        f"{stats['omitido']} omitidos, {stats['error']} errores."
    )
    print(f"Resultados: {results_path}")
    if auto_mode:
        print(f"Métricas: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
