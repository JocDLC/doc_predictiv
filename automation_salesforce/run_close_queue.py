"""Cierra un lote de Leads en Salesforce con el motivo elegido por el auxiliar.

Cierre en dos hitos verificables por Lead:
1. ``Guardar`` del trío Comentario/Cualificación/Sub-Cualificación → estado
   ``Cerrado`` (hito intermedio ``conversion_pendiente``).
2. ``Convert Lead → Yes`` → propietario ``AR_LEAD_COLD`` →
   ``cerrado_verificado``.

No hay mínimo de intentos: el auxiliar decide cuándo cerrar. Si la sesión de
Salesforce no está activa el runner aborta sin esperar input de consola (el
servidor lo lanza desatendido).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException

from browser_factory import create_driver, detect_browser, release_driver
from closure_store import (
    closure_result_entry,
    load_close_queue_file,
    record_result,
    results_path_for,
)
from comment_reader import build_record_url, find_field_text, find_field_value, is_duplicate_lead
from comment_writer import prepare_other_information, save_edit_form
from country_fields import ARGENTINA, field_display, field_labels, normalize_country
from lead_closure import (
    CLOSED_STATE,
    COMMENT_FIELD_LABELS,
    QUALIFICATION_FIELD_LABELS,
    STATUS_ALREADY_CLOSED,
    STATUS_CONVERSION_PENDING,
    STATUS_CONVERSION_UNVERIFIED,
    STATUS_ERROR,
    STATUS_REVIEW,
    STATUS_VERIFIED,
    SUBQUALIFICATION_FIELD_LABELS,
    confirm_conversion,
    contract_text,
    convert_lead,
    edit_form_matches,
    is_final_closed,
    motive_line_present,
    normalized_value,
    open_qualification_edit,
    read_closure_state,
    reason_contract,
    select_picklist_option,
    set_comentario,
    subqualification_options,
    verify_persisted_fields,
)
from local_audit import capture_failure, create_logger, mask_lead_id
from productivity_metrics import metrics_path_for, summarize_results, write_metrics
from run_document_queue import new_run_id, output_override, parse_queue_args, queue_directory_from_config
from salesforce_session import (
    ROOT,
    is_authenticated,
    load_config,
    local_path,
    wait_for_lightning_ready,
)
from snapshot_store import content_hash

OPTION_KEYS = ("--run-id", "--results", "--metrics")


def fail_lead(
    driver,
    screenshot_directory,
    logger,
    results_path,
    lead_id: str,
    reason_code: str,
    run_id: str,
    reason,
    elapsed_seconds: float | None = None,
    stage_seconds: dict[str, float] | None = None,
    status: str = STATUS_ERROR,
    country: str = "",
) -> dict:
    """Registra un fallo/revisión sin exponer datos ni detener el resto."""
    screenshot = capture_failure(driver, screenshot_directory, "close_error")
    reason_text = f"{type(reason).__name__}: {reason}" if isinstance(reason, Exception) else str(reason)
    logger.error(
        "Cierre no completado: lead=%s captura=%s motivo=%s",
        mask_lead_id(lead_id),
        screenshot.name,
        reason_text,
    )
    entry = closure_result_entry(
        lead_id,
        status,
        reason_code,
        run_id,
        elapsed_seconds,
        stage_seconds,
        extra={"country": country} if country else None,
    )
    record_result(results_path, entry)
    return entry


def persist_and_verify(
    driver,
    record_url: str,
    contract: dict[str, object],
    preserved_hash: str,
    timeout_seconds: int,
    motive_labels: tuple[str, ...] = (),
    motive_check=None,
    preserved_labels: tuple[str, ...] = (),
) -> tuple[bool, int]:
    """Guarda el formulario y confirma campos + estado + el campo preservado.

    ``motive_labels``/``motive_check`` verifican el campo del motivo según el
    país y ``preserved_labels`` protege el campo de intentos, que el cierre no
    debe tocar. Devuelve (ok, recargas). Si Guardar vence esperando el cierre
    del editor, recarga el registro y comprueba el valor persistido en vez de
    declarar error a ciegas (misma recuperación que la documentación).
    """
    reloads = 0
    motive_labels = motive_labels or COMMENT_FIELD_LABELS
    preserved_labels = preserved_labels or motive_labels

    def fields_saved() -> bool:
        return verify_persisted_fields(driver, contract, motive_labels, motive_check)

    try:
        save_edit_form(driver, timeout_seconds)
    except (TimeoutException, WebDriverException):
        reloads += 1
        driver.get(record_url)
        wait_for_lightning_ready(driver, timeout_seconds)
        if not fields_saved():
            raise
    for _ in range(2):
        if not fields_saved():
            reloads += 1
            time.sleep(2.0)
            driver.get(record_url)
            wait_for_lightning_ready(driver, timeout_seconds)
            continue
        state = read_closure_state(driver, motive_labels or COMMENT_FIELD_LABELS)
        if normalized_value(state["estado"]) != CLOSED_STATE:
            continue
        try:
            preserved_after = content_hash(find_field_value(driver, timeout_seconds, preserved_labels))
        except (TimeoutException, WebDriverException):
            preserved_after = ""
        return preserved_after == preserved_hash, reloads
    return False, reloads


def append_closure_motive(
    driver,
    record_url: str,
    motive_labels: tuple[str, ...],
    motive_literal: str,
    timeout_seconds: int,
    display_name: str,
) -> str:
    """Agrega el motivo al final del campo conservando el texto previo.

    Es el paso Colombia/México: el literal se anexa a ``Otra información`` sin
    reemplazar nada. Devuelve el texto completo esperado; si el motivo ya
    figura como línea propia, devuelve el texto actual sin escribir de nuevo.
    """
    current = find_field_value(driver, timeout_seconds, motive_labels)
    if motive_line_present(current, motive_literal):
        return current
    expected = (f"{current.rstrip()}\n{motive_literal}").strip()
    prepare_other_information(
        driver,
        expected,
        timeout_seconds,
        labels=motive_labels,
        display_name=display_name,
    )
    try:
        save_edit_form(driver, timeout_seconds)
    except (TimeoutException, WebDriverException):
        # La persistencia pudo completar igual: se relee en vez de reintentar a ciegas.
        driver.get(record_url)
        wait_for_lightning_ready(driver, timeout_seconds)
        persisted = find_field_text(driver, motive_labels)
        if normalized_value(persisted) != normalized_value(expected):
            raise
    for _ in range(2):
        persisted = find_field_text(driver, motive_labels)
        if normalized_value(persisted) == normalized_value(expected):
            return expected
        time.sleep(2.0)
        driver.get(record_url)
        wait_for_lightning_ready(driver, timeout_seconds)
    raise ValueError(f"El motivo no quedó persistido en {display_name}.")


def close_one_lead(
    driver,
    lead: dict[str, str],
    config: dict,
    results_path: Path,
    screenshot_directory: Path,
    logger,
    run_id: str,
    country: str = ARGENTINA,
) -> dict:
    """Ejecuta el cierre completo de un Lead y devuelve su entrada de resultado."""
    lead_id = lead["lead_id"]
    contract = reason_contract(lead["reason"])
    reason_code = lead["reason"]
    country = normalize_country(country)
    # Argentina: motivo en Comentario, intentos en Otra información.
    # Colombia/México: motivo agregado en Otra información, intentos en Comentario.
    motive_labels = field_labels(country, "closure")
    motive_display = field_display(country, "closure")
    attempts_labels = field_labels(country, "attempts")
    motive_literal = contract_text(contract, "comentario")
    timeout_seconds = config["timeouts"]["page_load_seconds"]
    record_url = build_record_url(
        config["salesforce_url"],
        lead_id,
        config.get("record_object_api_name", "Lead"),
    )
    stage_seconds: dict[str, float] = {}
    lead_started_at = time.monotonic()

    verify_reloads = 0

    def motive_satisfied(field_text: str) -> bool:
        """Argentina exige el literal exacto; Colombia/México lo acepta como
        línea agregada porque el campo conserva el texto previo."""
        if country == ARGENTINA:
            return normalized_value(field_text) == normalized_value(motive_literal)
        return motive_line_present(field_text, motive_literal)

    def fail(reason, status=STATUS_ERROR):
        return fail_lead(
            driver,
            screenshot_directory,
            logger,
            results_path,
            lead_id,
            reason_code,
            run_id,
            reason,
            elapsed_seconds=time.monotonic() - lead_started_at,
            stage_seconds=stage_seconds,
            status=status,
            country=country,
        )

    def record(status: str) -> dict:
        entry = closure_result_entry(
            lead_id,
            status,
            reason_code,
            run_id,
            time.monotonic() - lead_started_at,
            stage_seconds,
            verify_reloads,
            extra={"country": country},
        )
        record_result(results_path, entry)
        return entry

    # --- Lectura previa y clasificación -------------------------------------
    stage_started_at = time.monotonic()
    driver.get(record_url)
    wait_for_lightning_ready(driver, timeout_seconds)
    stage_seconds["navigation"] = time.monotonic() - stage_started_at

    stage_started_at = time.monotonic()
    state = read_closure_state(driver, motive_labels)
    stage_seconds["state_read"] = time.monotonic() - stage_started_at
    if not normalized_value(state.get("estado")) or not normalized_value(state.get("propietario")):
        return fail(ValueError("No se pudo confirmar el estado y propietario antes del cierre."), STATUS_REVIEW)

    # Lecturas antiguas sin clave "motivo" equivalen al esquema Argentina.
    motive_text = state.get("motivo", state["comentario"])

    # La marca de duplicado puede estar en cualquiera de los dos campos.
    if is_duplicate_lead(state["comentario"]) or is_duplicate_lead(motive_text):
        logger.info("Lead duplicado, cierre omitido: lead=%s", mask_lead_id(lead_id))
        return record(STATUS_REVIEW)
    if is_final_closed(state) and motive_satisfied(motive_text):
        return record(STATUS_ALREADY_CLOSED)

    # Si ya quedó Cerrado con el motivo pedido pero sin la conversión, retoma
    # solo Convert Lead → Yes; con otro motivo o estado incompatible, revisión.
    fields_saved = normalized_value(state["estado"]) == CLOSED_STATE and motive_satisfied(motive_text)
    if normalized_value(state["estado"]) == CLOSED_STATE and not fields_saved:
        return record(STATUS_REVIEW)
    if fields_saved and not verify_persisted_fields(driver, contract, motive_labels, motive_satisfied):
        return record(STATUS_REVIEW)

    # --- Escritura del motivo y guardado del formulario ---------------------
    preserved_hash = ""
    if not fields_saved:
        # El campo de intentos no se toca: su hash antes/después lo garantiza.
        try:
            preserved_hash = content_hash(find_field_value(driver, timeout_seconds, attempts_labels))
        except (TimeoutException, WebDriverException):
            preserved_hash = ""
        try:
            stage_started_at = time.monotonic()
            if country != ARGENTINA:
                # Colombia/México: el motivo se anexa a Otra información en su
                # propio editor, conservando el texto previo del campo.
                expected_motive = append_closure_motive(
                    driver,
                    record_url,
                    motive_labels,
                    motive_literal,
                    timeout_seconds,
                    motive_display,
                )
                def motive_check(text: str) -> bool:
                    return normalized_value(text) == normalized_value(expected_motive)
            else:
                motive_check = None
            # Texto del campo de intentos que el formulario debe conservar
            # intacto (en Colombia/México el editor de Comentario lo muestra).
            attempts_before_text = find_field_text(driver, attempts_labels)
            for attempt in range(2):
                open_qualification_edit(driver, timeout_seconds)
                if country == ARGENTINA:
                    set_comentario(driver, motive_literal, timeout_seconds)

                    def form_field_ok() -> bool:
                        return edit_form_matches(driver, contract)
                else:

                    def form_field_ok() -> bool:
                        return edit_form_matches(
                            driver,
                            contract,
                            COMMENT_FIELD_LABELS,
                            attempts_before_text,
                        )
                select_picklist_option(
                    driver,
                    QUALIFICATION_FIELD_LABELS,
                    contract_text(contract, "cualificacion"),
                    timeout_seconds,
                )
                # Sub-Cualificación depende de la Cualificación elegida.
                select_picklist_option(
                    driver,
                    SUBQUALIFICATION_FIELD_LABELS,
                    subqualification_options(contract),
                    timeout_seconds,
                )
                # Un re-render asíncrono de Lightning puede limpiar el
                # formulario: si los valores no quedaron, reintentar una vez.
                if form_field_ok():
                    break
                if attempt == 0:
                    driver.get(record_url)
                    wait_for_lightning_ready(driver, timeout_seconds)
            if not form_field_ok():
                raise ValueError("Los valores del motivo no quedaron en el formulario de edición.")
            stage_seconds["fields_edit"] = time.monotonic() - stage_started_at
        except (ValueError, TimeoutException, WebDriverException) as error:
            return fail(error)

        try:
            stage_started_at = time.monotonic()
            saved, verify_reloads = persist_and_verify(
                driver,
                record_url,
                contract,
                preserved_hash,
                timeout_seconds,
                motive_labels=motive_labels,
                motive_check=motive_check,
                preserved_labels=attempts_labels,
            )
            stage_seconds["save_verify"] = time.monotonic() - stage_started_at
        except (ValueError, TimeoutException, WebDriverException) as error:
            return fail(error)
        if not saved:
            return fail(ValueError("Los campos no quedaron persistidos o el estado no pasó a Cerrado."))
        # Hito intermedio persistido: campos guardados y estado Cerrado.
        record(STATUS_CONVERSION_PENDING)

    # --- Conversión -----------------------------------------------------------
    try:
        stage_started_at = time.monotonic()
        convert_lead(driver, timeout_seconds)
        stage_seconds["convert_click"] = time.monotonic() - stage_started_at
        confirm_conversion(driver, timeout_seconds)
        stage_seconds["convert_confirm"] = time.monotonic() - stage_started_at
    except (ValueError, TimeoutException, WebDriverException) as error:
        # El guardado ya se verificó: no repetir el formulario.
        return fail(error, status=STATUS_CONVERSION_PENDING)

    # --- Verificación final ---------------------------------------------------
    # La conversión recarga la página y el propietario cambia de forma asíncrona.
    # Esperar el resultado definitivo sin recargar continuamente la vista.
    try:
        time.sleep(3.0)
        driver.get(record_url)
        wait_for_lightning_ready(driver, timeout_seconds)
        final_state = read_closure_state(driver, motive_labels)
        deadline = time.monotonic() + timeout_seconds
        last_reload = time.monotonic()
        max_attempts = max(3, timeout_seconds)
        attempts = 0
        while attempts < max_attempts and time.monotonic() < deadline and not is_final_closed(final_state):
            attempts += 1
            if normalized_value(final_state.get("estado")) == CLOSED_STATE:
                # El estado ya persistió: esperar la actualización del propietario.
                time.sleep(2.0)
                final_state = read_closure_state(driver, motive_labels)
            elif time.monotonic() - last_reload >= 4.0:
                # La página sigue cargando o incompleta: una recarga acotada.
                driver.get(record_url)
                wait_for_lightning_ready(driver, timeout_seconds)
                final_state = read_closure_state(driver, motive_labels)
                last_reload = time.monotonic()
            else:
                time.sleep(1.0)
                final_state = read_closure_state(driver, motive_labels)
    except (TimeoutException, WebDriverException) as error:
        return fail(error, status=STATUS_CONVERSION_UNVERIFIED)

    if is_final_closed(final_state):
        logger.info(
            "Lead cerrado y verificado: lead=%s motivo=%s",
            mask_lead_id(lead_id),
            reason_code,
        )
        return record(STATUS_VERIFIED)
    if normalized_value(final_state["estado"]) == CLOSED_STATE:
        return fail(
            ValueError("Estado Cerrado pero propietario no verificado como AR_LEAD_COLD."),
            status=STATUS_CONVERSION_UNVERIFIED,
        )
    return fail(
        ValueError("La conversión no produjo el estado Cerrado esperado."),
        status=STATUS_CONVERSION_UNVERIFIED,
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    queue_path, auto_mode, options = parse_queue_args(argv)
    if not queue_path:
        print("Uso: python run_close_queue.py [--auto] [--run-id <id>] queues/<cierre>.json")
        return 2

    config = load_config()
    queue_directory = queue_directory_from_config(config)
    try:
        queue_file = load_close_queue_file(queue_path, queue_directory)
        leads = queue_file["leads"]
        results_path = output_override(options.get("results", ""), queue_directory, "resultados")
        metrics_path = output_override(options.get("metrics", ""), queue_directory, "métricas")
    except ValueError as error:
        print(f"Cola de cierre inválida: {error}")
        return 2

    results_path = results_path or results_path_for(queue_path)
    metrics_path = metrics_path or metrics_path_for(results_path)
    run_id = options.get("run_id") or queue_file["run_id"] or new_run_id()
    # El modo de país quedó congelado en la cola: el campo del motivo se
    # deriva de él y no puede cambiar a mitad de la ejecución.
    country = normalize_country(queue_file["country"])
    stats: dict[str, int] = {}
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

    try:
        # El runner es desatendido: sin sesión activa aborta con mensaje claro
        # en vez de quedar colgado esperando un input de consola imposible.
        driver.get(config["salesforce_url"])
        if not is_authenticated(driver):
            print(
                "No hay sesión activa de Salesforce en el navegador del bot. "
                "Iniciá sesión (con 2FA) en la pestaña de Salesforce y volvé a intentar."
            )
            return 1
        batch_started_at = time.monotonic()
        for index, lead in enumerate(leads, start=1):
            print(f"\n=== Cierre {index}/{len(leads)} ===")
            try:
                entry = close_one_lead(
                    driver,
                    lead,
                    config,
                    results_path,
                    screenshot_directory,
                    logger,
                    run_id,
                    country=country,
                )
            except (ValueError, TimeoutException, WebDriverException) as error:
                entry = fail_lead(
                    driver,
                    screenshot_directory,
                    logger,
                    results_path,
                    lead["lead_id"],
                    lead["reason"],
                    run_id,
                    error,
                    country=country,
                )
            stats[entry["status"]] = stats.get(entry["status"], 0) + 1
            batch_results.append(entry)
            print(f"Resultado: {entry['status']}")
    finally:
        release_driver(driver)

    if auto_mode:
        write_metrics(metrics_path, summarize_results(batch_results, time.monotonic() - batch_started_at))
    print("\nResumen de cierre:")
    for status, count in sorted(stats.items()):
        print(f"  {status}: {count}")
    print(f"Resultados: {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
