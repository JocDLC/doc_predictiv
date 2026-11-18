"""Runner del laboratorio WhatsApp (modo prueba y modo real).

Orquesta, para cada lead de la cola congelada:

- verifica identidad (URL), sesión, país Argentina y preferencia WhatsApp;
- en ``prueba``: lee el historial, calcula la línea de intento prevista y
  comprueba el botón Send To Whatsapp — nunca escribe ni pulsa;
- en ``real``: conserva el historial, agrega ``N INT Se envía WhatsApp …``
  (N = max(INT)+1) en ``Otra información``, verifica persistencia tras
  recarga, reserva el clic en el diario y confirma por toast positivo.

El diario SQLite (``laboratory_store``) hace reanudable la tanda: los estados
terminal/ambiguos se omiten y un ``stop`` solicitado por la UI se respeta
antes de cada lead. Cada resultado lleva ``stage_seconds`` para la
comparación Selenium/agent-browser.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from selenium.common.exceptions import WebDriverException

from agent_browser import AgentBrowserUnavailable, make_agent_browser
from browser_factory import create_driver, detect_browser
from comment_reader import OTHER_INFORMATION_LABELS, next_attempt_number
from comment_writer import compose_other_information
from laboratory_browser import SeleniumLabBrowser, normalize_persisted_text
from laboratory_contracts import (
    BLOCK_CAMPO_ILEGIBLE,
    BLOCK_ID_INVALIDO,
    BLOCK_PREFERENCIA,
    BLOCK_PAIS_NO_AR,
    BLOCK_SESION,
    BLOCK_SIN_BOTON,
    BLOCK_YA_ENVIADO,
    STATUS_APTO,
    STATUS_AUDIT_DISCREPANCIA,
    STATUS_AUDIT_OK,
    STATUS_AUDIT_SIN_RESERVA,
    STATUS_BLOQUEADO,
    STATUS_DOC_ERROR,
    STATUS_ENVIADO,
    STATUS_ERROR,
    STATUS_NO_ELEGIBLE,
    STATUS_OMITIDO,
    STATUS_WA_ERROR,
    STATUS_WA_NO_CONFIRMADO,
    is_argentina,
    validate_laboratory_queue,
    wants_whatsapp,
    whatsapp_attempt_line,
)
from laboratory_metrics import summarize_laboratory_results, write_metrics
from laboratory_store import (
    SEND_BLOQUEADO,
    SEND_CONFIRMADO,
    SEND_INDETERMINADO,
    SEND_NO_CONFIRMADO,
    STAGE_DOC_CONFIRMADA,
    STAGE_DOC_PREPARADA,
    STAGE_TERMINAL,
    STAGE_VERIFICADO,
    LaboratoryStore,
    store_path_for,
)
from local_audit import capture_failure, create_logger, mask_lead_id
from run_document_queue import new_run_id, output_override, parse_queue_args
from salesforce_session import local_path, load_config

ROOT = Path(__file__).parent
FIELD_RENDER_WAIT_SECONDS = 10
# El toast depende de la integración servidor-side: latencia real medida
# 1.8s–11.3s; 15s cortaba envíos válidos. 45s solo se agota en fallos reales.
WA_TOAST_WAIT_SECONDS = 45

# Etiquetas del país y la preferencia en la ficha (desde lead_list_fields).


def record_result(results_path: Path, entry: dict) -> None:
    """Append atómico por línea: la UI lee resultados parciales en vivo."""
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_results(results_path: Path) -> list[dict]:
    if not results_path.exists():
        return []
    entries = []
    for line in results_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def eligibility_block(lead: dict) -> str | None:
    """Elegibilidad según la BD cargada, igual que el Monitor lee la bandeja.

    El país vacío se interpreta como Argentina (DEFAULT_COUNTRY histórico);
    la preferencia debe pedir WhatsApp. Se chequea ANTES de abrir la ficha:
    un lead no elegible ni siquiera se navega.
    """
    pais = str(lead.get("pais") or "")
    if pais and not is_argentina(pais):
        return f"{BLOCK_PAIS_NO_AR}:{pais}"
    preferencia = str(lead.get("preferencia") or "")
    if not wants_whatsapp(preferencia):
        return f"{BLOCK_PREFERENCIA}:{preferencia or 'vacío'}"
    return None


def make_browser(engine: str, config: dict):
    """Crea el adaptador del motor pedido sobre el navegador dedicado."""
    if engine == "agent_browser":
        return make_agent_browser(config)
    browser_name, executable = detect_browser(config["browser"])
    driver = create_driver(
        browser_name,
        executable,
        local_path(config["profile_directory"]),
        config.get("debugger_address", "127.0.0.1:9222"),
    )
    return SeleniumLabBrowser(driver, config)


def stage_timer():
    """Acumulador de segundos por etapa para la métrica comparativa."""
    stages: dict[str, float] = {}
    last = time.monotonic()

    def mark(stage: str) -> None:
        nonlocal last
        now = time.monotonic()
        stages[stage] = round(stages.get(stage, 0.0) + (now - last), 2)
        last = now

    return stages, mark


def result_entry(
    lead: dict,
    engine: str,
    status: str,
    run_id: str,
    started_at: float,
    *,
    detail: str = "",
    stages: dict | None = None,
    attempt_line: str = "",
) -> dict:
    entry = {
        "lead_id": lead["lead_id"],
        "engine": engine,
        "status": status,
        "run_id": run_id,
        "elapsed_seconds": round(time.monotonic() - started_at, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if lead.get("nombre"):
        entry["nombre"] = lead["nombre"]
    if detail:
        entry["detail"] = detail
    if stages:
        entry["stage_seconds"] = stages
    if attempt_line:
        entry["attempt_line"] = attempt_line
    return entry


def verify_lead(
    browser,
    lead: dict,
    config: dict,
) -> dict:
    """Modo prueba: lee todo lo necesario sin escribir ni pulsar.

    Devuelve {status, detail, stages, attempt_line?, evidence}.
    """
    stages, mark = stage_timer()
    ineligible = eligibility_block(lead)
    if ineligible:
        return {"status": STATUS_NO_ELEGIBLE, "detail": ineligible, "stages": stages}
    browser.open_record(lead["lead_id"])
    mark("navigation")
    if not browser.is_authenticated():
        return {"status": STATUS_BLOQUEADO, "detail": BLOCK_SESION, "stages": stages}
    opened_id = browser.current_record_id()
    if opened_id != lead["lead_id"]:
        return {"status": STATUS_BLOQUEADO, "detail": BLOCK_ID_INVALIDO, "stages": stages}

    existing = browser.wait_field_text(OTHER_INFORMATION_LABELS, FIELD_RENDER_WAIT_SECONDS)
    mark("eligibility_read")
    if existing is None:
        return {
            "status": STATUS_BLOQUEADO,
            "detail": f"{BLOCK_CAMPO_ILEGIBLE}:otra informacion",
            "stages": stages,
        }
    button = browser.whatsapp_button_present()
    mark("button_check")
    if not button:
        return {"status": STATUS_BLOQUEADO, "detail": BLOCK_SIN_BOTON, "stages": stages}
    next_int = next_attempt_number(existing)
    return {
        "status": STATUS_APTO,
        "detail": "",
        "stages": stages,
        "attempt_line": whatsapp_attempt_line(next_int),
        "evidence": {"next_int": next_int, "history_length": len(existing)},
    }


def send_for_lead(
    browser,
    lead: dict,
    config: dict,
    store: LaboratoryStore,
    campaign_id: str,
) -> dict:
    """Modo real: documenta el intento y envía WhatsApp, con checkpoints."""
    stages, mark = stage_timer()
    lead_id = lead["lead_id"]
    ineligible = eligibility_block(lead)
    if ineligible:
        return {"status": STATUS_NO_ELEGIBLE, "detail": ineligible, "stages": stages}
    browser.open_record(lead_id)
    mark("navigation")
    if not browser.is_authenticated():
        return {"status": STATUS_BLOQUEADO, "detail": BLOCK_SESION, "stages": stages}
    opened_id = browser.current_record_id()
    if opened_id != lead_id:
        return {"status": STATUS_BLOQUEADO, "detail": BLOCK_ID_INVALIDO, "stages": stages}

    existing = browser.wait_field_text(OTHER_INFORMATION_LABELS, FIELD_RENDER_WAIT_SECONDS)
    mark("eligibility_read")
    if existing is None:
        return {
            "status": STATUS_BLOQUEADO,
            "detail": f"{BLOCK_CAMPO_ILEGIBLE}:otra informacion",
            "stages": stages,
        }

    # Plan persistido: si la operación ya tenía línea reservada (reanudación)
    # se conserva; si el historial cambió, se renumera antes del Save.
    operation = store.get_operation(campaign_id, lead_id)
    if operation and operation.get("attempt_line"):
        next_int = int(operation["next_int"])
        attempt_line = str(operation["attempt_line"])
    else:
        next_int = next_attempt_number(existing)
        attempt_line = whatsapp_attempt_line(next_int)
        operation = store.begin_operation(campaign_id, lead_id, browser.engine, next_int, attempt_line, existing)
        attempt_line = str(operation["attempt_line"])
        next_int = int(operation["next_int"])
    store.advance(campaign_id, lead_id, STAGE_VERIFICADO)

    # Relectura del historial: detecta ediciones concurrentes entre la
    # verificación y la escritura. Si cambió, renumera con el nuevo máximo.
    current = browser.wait_field_text(OTHER_INFORMATION_LABELS, FIELD_RENDER_WAIT_SECONDS)
    if current is None:
        return {"status": STATUS_DOC_ERROR, "detail": BLOCK_CAMPO_ILEGIBLE, "stages": stages}
    if normalize_persisted_text(current) != normalize_persisted_text(existing):
        recomputed = next_attempt_number(current)
        if recomputed != next_int:
            next_int = recomputed
            attempt_line = whatsapp_attempt_line(next_int)
            store.update_plan(campaign_id, lead_id, next_int, attempt_line, current)
        existing = current
    body = attempt_line.split(" INT ", 1)[1] if " INT " in attempt_line else attempt_line
    prepared = compose_other_information(existing, next_int, body)
    mark("doc_prepare")

    store.advance(campaign_id, lead_id, STAGE_DOC_PREPARADA)
    browser.write_and_save_field(
        OTHER_INFORMATION_LABELS,
        "Otra información",
        prepared,
        int(config.get("timeouts", {}).get("page_load_seconds", 30)),
    )
    # Verificación sin recarga: Lightning muestra el valor nuevo solo cuando
    # el save respondió OK. Leer el campo en UI ES la verificación — recargar
    # antes de tiempo podía abortar un guardado aún en vuelo.
    persisted = None
    save_deadline = time.monotonic() + int(config.get("timeouts", {}).get("save_verify_seconds", 15))
    while time.monotonic() < save_deadline:
        persisted = browser.field_text(OTHER_INFORMATION_LABELS)
        if persisted is not None and normalize_persisted_text(persisted) == normalize_persisted_text(prepared):
            break
        time.sleep(1.0)
    mark("doc_save_verify")
    if persisted is None or normalize_persisted_text(persisted) != normalize_persisted_text(prepared):
        store.advance(
            campaign_id,
            lead_id,
            STAGE_TERMINAL,
            doc_status="error_verificacion",
            send_status=SEND_BLOQUEADO,
            review_reason="el valor no quedó persistido tras el guardado",
        )
        return {"status": STATUS_DOC_ERROR, "detail": "verificacion_fallida", "stages": stages}
    store.advance(campaign_id, lead_id, STAGE_DOC_CONFIRMADA, doc_status="confirmada")

    # Precheck del botón ANTES de reservar: un lead sin botón no reserva clic.
    if not browser.whatsapp_button_present():
        store.advance(
            campaign_id,
            lead_id,
            STAGE_TERMINAL,
            send_status=SEND_BLOQUEADO,
            review_reason=BLOCK_SIN_BOTON,
        )
        return {"status": STATUS_DOC_ERROR, "detail": BLOCK_SIN_BOTON, "stages": stages}

    # Observador con baseline ANTES de reservar y clicar: captura los textos
    # toast-like ya visibles para descartar señales ajenas o antiguas.
    armed = browser.arm_whatsapp_observation()
    # Reserva atómica (etapa + send_reservations) ANTES del clic: si el
    # proceso muere acá el lead queda indeterminado y jamás se reenvía.
    store.reserve_send_click(campaign_id, lead_id)
    # Revalidación de identidad tras la recarga de verificación.
    if browser.current_record_id() != lead_id:
        store.advance(
            campaign_id,
            lead_id,
            STAGE_TERMINAL,
            send_status=SEND_INDETERMINADO,
            review_reason=f"{BLOCK_ID_INVALIDO}:post_recarga",
        )
        return {"status": STATUS_WA_ERROR, "detail": BLOCK_ID_INVALIDO, "stages": stages}
    click = browser.guarded_click_whatsapp(lead_id)
    mark("send_click")
    if click != "clicked":
        store.advance(
            campaign_id,
            lead_id,
            STAGE_TERMINAL,
            send_status=SEND_INDETERMINADO,
            review_reason=click,
        )
        return {"status": STATUS_WA_ERROR, "detail": click, "stages": stages}
    evidence = browser.collect_whatsapp_evidence(WA_TOAST_WAIT_SECONDS)
    mark("send_confirm")
    browser.dispose_whatsapp_observation()
    outcome = str(evidence.get("outcome") or "no_confirmado")
    reason = str(evidence.get("reason") or "sin_senal")
    journal_evidence = {
        "confirmation": evidence,
        "observation": armed,
        "click": click,
        "expected_lead_id": lead_id,
    }
    if outcome == "confirmado":
        browser.close_whatsapp_toast()
        store.advance(
            campaign_id,
            lead_id,
            STAGE_TERMINAL,
            send_status=SEND_CONFIRMADO,
            evidence=journal_evidence,
        )
        return {"status": STATUS_ENVIADO, "stages": stages, "attempt_line": attempt_line}
    send_status = SEND_INDETERMINADO if outcome == "indeterminado" else SEND_NO_CONFIRMADO
    store.advance(
        campaign_id,
        lead_id,
        STAGE_TERMINAL,
        send_status=send_status,
        review_reason=reason,
        evidence=journal_evidence,
    )
    return {
        "status": STATUS_WA_NO_CONFIRMADO,
        # Sin señal alguna el envío queda ambiguo: revisión humana, sin retry.
        "detail": "verificar_manual" if reason == "sin_senal" else reason,
        "stages": stages,
        "attempt_line": attempt_line,
    }


def audit_lead(browser, lead: dict, config: dict, store: LaboratoryStore) -> dict:
    """Modo auditoría (solo lectura): verifica que la línea reservada en el
    diario aparezca exactamente una vez en ``Otra información`` de la ficha."""
    stages, mark = stage_timer()
    lead_id = lead["lead_id"]
    operation = store.latest_operation_for_lead(lead_id)
    if not operation or not operation.get("attempt_line"):
        return {"status": STATUS_AUDIT_SIN_RESERVA, "detail": "", "stages": stages}
    attempt_line = str(operation["attempt_line"])
    browser.open_record(lead_id)
    mark("navigation")
    if not browser.is_authenticated():
        return {"status": STATUS_BLOQUEADO, "detail": BLOCK_SESION, "stages": stages}
    if browser.current_record_id() != lead_id:
        return {"status": STATUS_BLOQUEADO, "detail": BLOCK_ID_INVALIDO, "stages": stages}
    persisted = browser.wait_field_text(OTHER_INFORMATION_LABELS, FIELD_RENDER_WAIT_SECONDS)
    mark("eligibility_read")
    if persisted is None:
        return {
            "status": STATUS_BLOQUEADO,
            "detail": f"{BLOCK_CAMPO_ILEGIBLE}:otra informacion",
            "stages": stages,
        }
    expected = normalize_persisted_text(attempt_line)
    count = sum(1 for line in persisted.splitlines() if normalize_persisted_text(line) == expected)
    if count == 1:
        return {"status": STATUS_AUDIT_OK, "detail": "", "stages": stages, "attempt_line": attempt_line}
    return {
        "status": STATUS_AUDIT_DISCREPANCIA,
        "detail": f"ocurrencias:{count}",
        "stages": stages,
        "attempt_line": attempt_line,
    }


def run_queue(queue_path: str, run_id: str, results_path: Path, metrics_path: Path) -> int:
    config = load_config()
    queue_directory = Path(config["queue_directory"]).resolve()
    if not queue_directory.is_absolute():
        queue_directory = (ROOT / config["queue_directory"]).resolve()
    payload = json.loads(Path(queue_path).read_text(encoding="utf-8"))
    queue = validate_laboratory_queue(payload)
    leads = queue["leads"]
    mode = queue["mode"]
    campaign_id = queue["campaign_id"]

    ui_output = ROOT / config.get("ui_output_directory", "ui_output")
    from urllib.parse import urlparse

    org_source = urlparse(str(config.get("salesforce_url") or "")).netloc
    store = LaboratoryStore(store_path_for(ui_output), org_source=org_source)
    store.ensure_campaign(campaign_id, queue["source_file"], queue["dataset_id"])
    store.register_run(run_id, campaign_id, mode, queue["engine"])

    logger = create_logger(ROOT / config["log_directory"])
    screenshot_directory = ROOT / config["screenshot_directory"]

    # Resultados por run (JSONL): el archivo de "cola activa" sigue como
    # alias para la UI, pero cada run conserva su propio historial.
    run_results_path = results_path.with_name(f"laboratorio_{run_id}.resultado.jsonl")
    run_metrics_path = metrics_path.with_name(f"laboratorio_{run_id}.metricas.json")

    def emit(entry: dict) -> None:
        record_result(results_path, entry)
        if run_results_path != results_path:
            record_result(run_results_path, entry)

    engines: dict[str, object] = {}
    unavailable_engines: set[str] = set()
    cycle_started = time.monotonic()
    stats: dict[str, int] = {}
    stopped = False

    def browser_for(engine: str):
        if engine not in engines:
            engines[engine] = make_browser(engine, config)
        return engines[engine]

    try:
        for lead in leads:
            if store.stop_requested(run_id):
                stopped = True
                break
            blocked, reason = store.is_blocked(campaign_id, lead["lead_id"])
            if mode == "real" and blocked:
                entry = result_entry(
                    lead,
                    lead["engines"][0],
                    STATUS_OMITIDO,
                    run_id,
                    time.monotonic(),
                    detail=f"{BLOCK_YA_ENVIADO}:{reason}",
                )
                emit(entry)
                stats[entry["status"]] = stats.get(entry["status"], 0) + 1
                continue
            for engine in lead["engines"]:
                if engine in unavailable_engines:
                    continue
                started_at = time.monotonic()
                try:
                    browser = browser_for(engine)
                    if mode == "auditoria":
                        outcome = audit_lead(browser, lead, config, store)
                    elif mode == "prueba":
                        outcome = verify_lead(browser, lead, config)
                    else:
                        outcome = send_for_lead(
                            browser,
                            lead,
                            config,
                            store,
                            campaign_id,
                        )
                    entry = result_entry(
                        lead,
                        engine,
                        outcome["status"],
                        run_id,
                        started_at,
                        detail=outcome.get("detail", ""),
                        stages=outcome.get("stages"),
                        attempt_line=outcome.get("attempt_line", ""),
                    )
                except AgentBrowserUnavailable as error:
                    unavailable_engines.add(engine)
                    entry = result_entry(
                        lead,
                        engine,
                        STATUS_ERROR,
                        run_id,
                        started_at,
                        detail=f"agent_browser_no_disponible:{error}",
                    )
                except (ValueError, TimeoutError, WebDriverException, RuntimeError) as error:
                    try:
                        browser = engines.get(engine)
                        driver = getattr(browser, "driver", None)
                        if driver is not None:
                            capture_failure(driver, screenshot_directory, "laboratorio")
                    except Exception:  # noqa: BLE001
                        pass
                    logger.error(
                        "Laboratorio falló: lead=%s engine=%s motivo=%s",
                        mask_lead_id(lead["lead_id"]),
                        engine,
                        type(error).__name__,
                    )
                    entry = result_entry(
                        lead,
                        engine,
                        STATUS_ERROR,
                        run_id,
                        started_at,
                        detail=type(error).__name__,
                    )
                emit(entry)
                stats[entry["status"]] = stats.get(entry["status"], 0) + 1
                print(
                    f"[laboratorio] {engine} lead {mask_lead_id(lead['lead_id'])} -> {entry['status']}",
                    flush=True,
                )
            if store.stop_requested(run_id):
                stopped = True
                break
    finally:
        for engine, browser in engines.items():
            try:
                browser.release()
            except Exception:  # noqa: BLE001
                pass

    final_status = "detenido" if stopped else "completado"
    store.finish_run(run_id, final_status)
    # Las métricas se computan sobre el archivo del run (no el alias activo):
    # corridas históricas nunca se mezclan ni se pisan.
    summary = summarize_laboratory_results(read_results(run_results_path), time.monotonic() - cycle_started)
    write_metrics(metrics_path, summary)
    if run_metrics_path != metrics_path:
        write_metrics(run_metrics_path, summary)
    print("\nResumen del laboratorio:")
    for status, count in sorted(stats.items()):
        print(f"  {status}: {count}")
    print(f"Resultados: {results_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    queue_path, _auto, options = parse_queue_args(argv)
    if not queue_path:
        print(
            "Uso: python run_laboratory_queue.py [--auto] [--run-id <id>] "
            "[--results <path>] [--metrics <path>] queues/laboratorio_<run>.json"
        )
        return 2
    config = load_config()
    queue_directory = (ROOT / config["queue_directory"]).resolve()
    try:
        results_path = output_override(options.get("results", ""), queue_directory, "resultados")
        metrics_path = output_override(options.get("metrics", ""), queue_directory, "metricas")
    except ValueError as error:
        print(str(error))
        return 2
    run_id = options.get("run_id") or new_run_id()
    results_path = results_path or Path(queue_path).with_suffix(".resultado.json")
    metrics_path = metrics_path or Path(queue_path).with_suffix(".metricas.json")
    return run_queue(queue_path, run_id, results_path, metrics_path)


if __name__ == "__main__":
    sys.exit(main())
