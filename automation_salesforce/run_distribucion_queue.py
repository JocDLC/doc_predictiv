"""Distribuye un lote de Leads hacia las personas destino indicadas en la cola.

La UI local guarda ``queues/cola_distribucion.json`` con los pares
``lead_id``/``persona`` ya revisados en la vista previa y el servidor lanza
este runner desatendido (sin input de consola). Por cada Lead se abre el
registro y se lee el propietario:

- ya es el destino → ``ya_asignado`` (idempotente, sin tocar);
- es una cola excluida (``SKIP_OWNERS``: frío/exportados) → ``cola_excluida``;
- es la cola de ingreso (``unassigned_owner`` de las bandejas del monitor,
  ej. ``AR_LEAD_QUALIF``) → Pick Up + guardado best-effort del panel
  "Contact Client" y ``reassign_owner``;
- cualquier otro propietario → ``reassign_owner`` directo al destino.

El runner nunca escribe en ``Otra información`` ni en otros campos: solo
cambia el propietario, verificado por relectura. Los resultados quedan en
``cola_distribucion.resultado.json`` junto a la cola.

Con ``modo: "prueba"`` en la cola corre ``simulate_one_lead``: mismo
recorrido de lectura y clasificación, y para los leads que se reasignarían
abre el modal "Cambiar propietario" solo para verificar que el nombre
destino existe en el lookup — siempre lo cancela. Nunca pulsa Pick Up ni
confirma nada: los estados salen con prefijo ``prueba_``.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException

from browser_factory import create_driver, detect_browser, release_driver
from closure_store import record_result
from distribucion_loader import load_distribucion_queue
from lead_closure import normalized_key
from lead_monitor import (
    OWNER_VERIFY_TIMEOUT_SECONDS,
    POLL_SECONDS,
    _reread_owner_after_refresh,
    open_record,
    owner_is_unassigned,
    press_pick_up,
    read_record_owner,
    reassign_owner,
    save_contact_panel_if_present,
    verify_persona_option,
    wait_record_owner,
)
from local_audit import capture_failure, create_logger, mask_lead_id
from monitor_store import BANDEJA_CODES, STATE_FILE_NAME, default_unassigned_owner, load_state
from productivity_metrics import round_elapsed_seconds
from run_document_queue import new_run_id, output_override, parse_queue_args, queue_directory_from_config
from salesforce_session import ROOT, is_authenticated, load_config, local_path

# Colas fuera de la distribución: leads ya en frío o exportados a otros canales.
# Colas de frío/export: el lead ya fue gestionado por otro canal — nunca se
# reasigna, solo se lista como ``cola_excluida`` (listas viejas incluidas).
SKIP_OWNERS = (
    "AR_LEAD_COLD",
    "AR_LEAD_EXPORT_GETLEAD",
    "AR_LEAD_LEADIT_EXPORT",
    "MX_LEAD_COLD",
    "MX_LEAD_EXPORT_GETLEAD",
    "CO_LEAD_COLD",
    "CO_LEAD_EXPORT_GETLEAD",
)

STATUS_REASIGNADO = "reasignado"
STATUS_YA_ASIGNADO = "ya_asignado"
STATUS_COLA_EXCLUIDA = "cola_excluida"
STATUS_PICKUP_ERROR = "pickup_error"
STATUS_INACCESIBLE = "lead_inaccesible"
STATUS_ERROR = "error"

# Estados de la simulación (modo prueba): nada se escribe en Salesforce.
STATUS_PRUEBA_YA_ASIGNADO = "prueba_ok:ya_asignado"
STATUS_PRUEBA_COLA_EXCLUIDA = "prueba_ok:cola_excluida"
STATUS_PRUEBA_REASIGNAR = "prueba_ok:reasignar"
STATUS_PRUEBA_PICKUP_Y_REASIGNAR = "prueba_ok:pickup_y_reasignar"
STATUS_PRUEBA_NOMBRE_NO_ENCONTRADO = "prueba_nombre_no_encontrado"
STATUS_PRUEBA_INACCESIBLE = "prueba_inaccesible"
STATUS_PRUEBA_ERROR = "prueba_error"


def _same_person(first: str, second: str) -> bool:
    """Match por nombre normalizado en ambos sentidos (como ``_encargada_para_lead``)."""
    a = normalized_key(first or "")
    b = normalized_key(second or "")
    return bool(a and b) and (a in b or b in a)


def _owner_in(owner: str, candidates) -> bool:
    return any(owner_is_unassigned(owner, candidate) for candidate in candidates)


def _wait_owner_out_of_queue(driver, queue_owners, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        owner = read_record_owner(driver)
        if owner and not _owner_in(owner, queue_owners):
            return True
        time.sleep(POLL_SECONDS)
    return False


def _ingreso_owners(config: dict) -> list[str]:
    """Colas de ingreso = ``unassigned_owner`` de las bandejas del monitor;
    sin estado todavía, los defaults por código de bandeja."""
    state_path = ROOT / config.get("ui_output_directory", "ui_output") / STATE_FILE_NAME
    try:
        state = load_state(state_path)
    except (OSError, ValueError):
        state = {}
    owners = [b["unassigned_owner"] for b in state.get("bandejas") or [] if b.get("unassigned_owner")]
    return owners or [default_unassigned_owner(code) for code in BANDEJA_CODES]


def _result_entry(
    lead_id: str,
    persona: str,
    status: str,
    run_id: str,
    started_at: float,
    propietario: str = "",
    detail: str = "",
    modo: str = "",
) -> dict:
    entry = {
        "lead_id": lead_id,
        "persona": persona,
        "status": status,
        "run_id": run_id,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_seconds": round_elapsed_seconds(time.monotonic() - started_at),
    }
    if modo:
        entry["modo"] = modo
    if propietario:
        entry["propietario_observado"] = propietario
    if detail:
        entry["detalle"] = detail
    return entry


def distribute_one_lead(
    driver,
    lead: dict[str, str],
    config: dict,
    ingreso_owners: list[str],
    results_path: Path,
    screenshot_directory: Path,
    logger,
    run_id: str,
) -> dict:
    """Resuelve el propietario de un lead y lo deja en la persona destino."""
    lead_id = lead["lead_id"]
    persona = lead["persona"]
    timeout_seconds = config["timeouts"]["page_load_seconds"]
    started_at = time.monotonic()

    def record(status: str, propietario: str = "", detail: str = "") -> dict:
        entry = _result_entry(lead_id, persona, status, run_id, started_at, propietario, detail, modo="real")
        record_result(results_path, entry)
        return entry

    try:
        open_record(driver, config, lead_id, timeout_seconds)
    except (TimeoutException, WebDriverException) as error:
        capture_failure(driver, screenshot_directory, "distribucion")
        logger.error("Lead inaccesible: lead=%s motivo=%s", mask_lead_id(lead_id), type(error).__name__)
        return record(STATUS_INACCESIBLE, detail=type(error).__name__)

    owner = wait_record_owner(driver)
    if not owner:
        return record(STATUS_INACCESIBLE, detail="propietario_ilegible")
    if _same_person(owner, persona):
        return record(STATUS_YA_ASIGNADO, propietario=owner)
    if _owner_in(owner, SKIP_OWNERS):
        return record(STATUS_COLA_EXCLUIDA, propietario=owner)
    if _owner_in(owner, ingreso_owners):
        if press_pick_up(driver) != "clicked":
            return record(STATUS_PICKUP_ERROR, propietario=owner, detail="sin_boton_pickup")
        if not _wait_owner_out_of_queue(driver, ingreso_owners, OWNER_VERIFY_TIMEOUT_SECONDS):
            owner = _reread_owner_after_refresh(driver, timeout_seconds)
            if not owner or _owner_in(owner, ingreso_owners):
                return record(STATUS_PICKUP_ERROR, propietario=owner, detail="propietario_no_cambio")
        # El panel "Contact Client" post-pickup se guarda best-effort sin
        # escribir marcas: la distribución no documenta comentarios.
        save_contact_panel_if_present(driver, timeout_seconds)
    outcome = reassign_owner(driver, persona, timeout_seconds)
    return record(outcome, propietario=owner)


def _format_lookup_diag(diagnostics: dict) -> str:
    """Resumen de lo que el lookup mostraba cuando el nombre no apareció."""
    if not diagnostics:
        return ""
    opciones = " / ".join(str(o) for o in diagnostics.get("options") or []) or "ninguna"
    return f"input: {diagnostics.get('inputValue')!r} · opciones vistas: {opciones}"


def simulate_one_lead(
    driver,
    lead: dict[str, str],
    config: dict,
    ingreso_owners: list[str],
    results_path: Path,
    screenshot_directory: Path,
    logger,
    run_id: str,
) -> dict:
    """Simula la distribución de un lead sin escribir nada en Salesforce.

    Mismo recorrido que ``distribute_one_lead``: abre el registro, lee el
    propietario y clasifica la acción que haría la corrida real. Para los
    leads que se reasignarían verifica además que el nombre destino existe
    en el lookup del modal "Cambiar propietario" —que siempre se cancela—.
    NUNCA pulsa Pick Up ni confirma el modal: los estados llevan prefijo
    ``prueba_`` para distinguirlos de una corrida real.
    """
    lead_id = lead["lead_id"]
    persona = lead["persona"]
    timeout_seconds = config["timeouts"]["page_load_seconds"]
    started_at = time.monotonic()

    def record(status: str, propietario: str = "", detail: str = "") -> dict:
        entry = _result_entry(lead_id, persona, status, run_id, started_at, propietario, detail, modo="prueba")
        record_result(results_path, entry)
        return entry

    try:
        open_record(driver, config, lead_id, timeout_seconds)
    except (TimeoutException, WebDriverException) as error:
        capture_failure(driver, screenshot_directory, "distribucion")
        logger.error("Lead inaccesible: lead=%s motivo=%s", mask_lead_id(lead_id), type(error).__name__)
        return record(STATUS_PRUEBA_INACCESIBLE, detail=type(error).__name__)

    owner = wait_record_owner(driver)
    if not owner:
        return record(STATUS_PRUEBA_INACCESIBLE, detail="propietario_ilegible")
    if _same_person(owner, persona):
        return record(STATUS_PRUEBA_YA_ASIGNADO, propietario=owner)
    if _owner_in(owner, SKIP_OWNERS):
        return record(STATUS_PRUEBA_COLA_EXCLUIDA, propietario=owner)

    # Tanto la cola de ingreso como otro propietario reasignarían: la
    # simulación solo verifica que el nombre destino existe en el lookup.
    # ``diagnostics`` vuelca qué mostraba el desplegable si la opción no
    # aparece — el dato que explica un "nombre no encontrado".
    diagnostics: dict = {}
    outcome = verify_persona_option(driver, persona, timeout_seconds, diagnostics)
    if outcome == "reasignacion_error:opcion":
        detail = _format_lookup_diag(diagnostics)
        return record(STATUS_PRUEBA_NOMBRE_NO_ENCONTRADO, propietario=owner, detail=detail)
    if outcome != "opcion_ok":
        paso = outcome.split(":", 1)[-1]
        return record(f"{STATUS_PRUEBA_ERROR}:{paso}", propietario=owner)
    if _owner_in(owner, ingreso_owners):
        return record(STATUS_PRUEBA_PICKUP_Y_REASIGNAR, propietario=owner)
    return record(STATUS_PRUEBA_REASIGNAR, propietario=owner)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    queue_path, _auto_mode, options = parse_queue_args(argv)
    if not queue_path:
        print("Uso: python run_distribucion_queue.py [--auto] [--run-id <id>] queues/<distribucion>.json")
        return 2

    config = load_config()
    queue_directory = queue_directory_from_config(config)
    try:
        queue_file = load_distribucion_queue(queue_path, queue_directory)
        leads = queue_file["leads"]
        modo = queue_file["modo"]
        results_path = output_override(options.get("results", ""), queue_directory, "resultados")
    except ValueError as error:
        print(f"Cola de distribución inválida: {error}")
        return 2

    results_path = results_path or Path(queue_path).expanduser().resolve().with_suffix(".resultado.json")
    run_id = options.get("run_id") or queue_file["run_id"] or new_run_id()
    ingreso_owners = _ingreso_owners(config)
    stats: dict[str, int] = {}
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
        # Runner desatendido: sin sesión aborta con mensaje claro.
        driver.get(config["salesforce_url"])
        if not is_authenticated(driver):
            print(
                "No hay sesión activa de Salesforce en el navegador del bot. "
                "Iniciá sesión (con 2FA) en la pestaña de Salesforce y volvé a intentar."
            )
            return 1
        process_lead = simulate_one_lead if modo == "prueba" else distribute_one_lead
        etiqueta = "Simulación" if modo == "prueba" else "Distribución"
        for index, lead in enumerate(leads, start=1):
            print(f"\n=== {etiqueta} {index}/{len(leads)} ===")
            started_at = time.monotonic()
            try:
                entry = process_lead(
                    driver,
                    lead,
                    config,
                    ingreso_owners,
                    results_path,
                    screenshot_directory,
                    logger,
                    run_id,
                )
            except (ValueError, TimeoutException, WebDriverException) as error:
                capture_failure(driver, screenshot_directory, "distribucion")
                logger.error(
                    "Distribución fallida: lead=%s motivo=%s",
                    mask_lead_id(lead["lead_id"]),
                    type(error).__name__,
                )
                entry = _result_entry(
                    lead["lead_id"],
                    lead["persona"],
                    f"{STATUS_PRUEBA_ERROR}:excepcion" if modo == "prueba" else STATUS_ERROR,
                    run_id,
                    started_at,
                    detail=type(error).__name__,
                    modo=modo,
                )
                record_result(results_path, entry)
            stats[entry["status"]] = stats.get(entry["status"], 0) + 1
            print(f"Resultado: {entry['status']}")
    finally:
        release_driver(driver)

    print(f"\nResumen de {etiqueta.lower()}:")
    for status, count in sorted(stats.items()):
        print(f"  {status}: {count}")
    print(f"Resultados: {results_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
