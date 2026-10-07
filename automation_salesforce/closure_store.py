"""Cola y resultados de cierre de Leads, separados de la documentación.

La cola activa vive en ``queues/cola_cierre_activa.json`` y se congela por
ejecución en ``queues/cierre_<run_id>.json``. Los resultados van a
``queues/cola_cierre_activa.resultado.json`` y nunca contienen contenido de
campos ni datos de clientes.

Contrato de la cola::

    {
      "operation": "close_leads",
      "generated_at": "...",
      "country": "argentina | colombia_mexico",
      "leads": [{"lead_id": "00Q...", "reason": "ilocalizable"}]
    }

Contrato de cada resultado::

    {"lead_id": "...", "status": "cerrado_verificado", "reason": "...",
     "run_id": "...", "at": "...", "elapsed_seconds": 1.2,
     "stage_seconds": {...}, "verify_reloads": 0}
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from comment_reader import SALESFORCE_ID_PATTERN
from country_fields import normalize_country
from lead_closure import CLOSURE_REASONS
from productivity_metrics import round_elapsed_seconds

CLOSE_QUEUE_OPERATION = "close_leads"


def _validate_close_lead(lead: object, lead_index: int) -> dict[str, str]:
    if not isinstance(lead, dict):
        raise ValueError(f"Lead {lead_index} de la cola de cierre no es un objeto válido.")  # noqa: TRY004
    lead_id = str(lead.get("lead_id") or "").strip()
    if not SALESFORCE_ID_PATTERN.fullmatch(lead_id):
        raise ValueError(f"Lead {lead_index} tiene un Lead ID inválido.")
    reason = str(lead.get("reason") or "").strip()
    if reason not in CLOSURE_REASONS:
        raise ValueError(f"Lead {lead_index} tiene un motivo de cierre inválido.")
    return {"lead_id": lead_id, "reason": reason}


def validate_close_queue(payload: object) -> list[dict[str, str]]:
    """Valida el objeto de la cola de cierre y devuelve los Leads.

    El cliente solo envía ``lead_id`` + ``reason`` (código); los literales de
    Salesforce se resuelven en el runner con ``lead_closure.reason_contract``.
    """
    if not isinstance(payload, dict) or payload.get("operation") != CLOSE_QUEUE_OPERATION:
        raise ValueError("La cola de cierre no declara operation='close_leads'.")
    # El modo de país decide a qué campo va el motivo: se valida junto con la cola.
    normalize_country(payload.get("country"))
    leads = payload.get("leads")
    if not isinstance(leads, list) or not leads:
        raise ValueError("La cola de cierre no contiene Leads.")
    seen: set[str] = set()
    validated = []
    for index, lead in enumerate(leads):
        item = _validate_close_lead(lead, index)
        if item["lead_id"] in seen:
            raise ValueError(f"Lead {index} duplicado en la cola de cierre.")
        seen.add(item["lead_id"])
        validated.append(item)
    return validated


def load_close_queue_file(queue_path: str, queue_directory: Path) -> dict[str, object]:
    """Lee y valida una cola de cierre dentro del directorio local queues."""
    allowed_directory = queue_directory.resolve()
    candidate_path = Path(queue_path).expanduser().resolve()
    if candidate_path.parent != allowed_directory:
        raise ValueError("La cola de cierre debe estar dentro del directorio local queues.")
    try:
        payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"La cola de cierre no es un JSON válido: {error.msg}") from error
    return {
        "leads": validate_close_queue(payload),
        "run_id": str(payload.get("run_id") or "").strip(),
        "country": normalize_country(payload.get("country")),
    }


def results_path_for(queue_path: str) -> Path:
    """Mantiene los resultados junto a la cola, fuera del repositorio."""
    return Path(queue_path).expanduser().resolve().with_suffix(".resultado.json")


def closure_result_entry(
    lead_id: str,
    status: str,
    reason: str,
    run_id: str,
    elapsed_seconds: float | None = None,
    stage_seconds: dict[str, float] | None = None,
    verify_reloads: int = 0,
    extra: dict | None = None,
) -> dict:
    """Entrada de resultado sin contenido de campos ni datos de clientes."""
    entry = {
        "lead_id": lead_id,
        "status": status,
        "reason": reason,
        "run_id": run_id,
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
    """Persiste el último estado de cada Lead; uno nuevo reemplaza al anterior."""
    results = {}
    if results_path.exists():
        try:
            for item in json.loads(results_path.read_text(encoding="utf-8")):
                results[item["lead_id"]] = item
        except (json.JSONDecodeError, KeyError, TypeError):
            results = {}
    results[entry["lead_id"]] = entry
    results_path.write_text(
        json.dumps(list(results.values()), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
