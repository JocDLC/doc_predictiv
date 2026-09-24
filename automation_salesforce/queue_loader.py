from __future__ import annotations

import json
from pathlib import Path

from comment_reader import SALESFORCE_ID_PATTERN

ATTEMPT_FIELDS = ("result", "date", "time", "call_id")


def _validate_attempt(attempt: object, lead_index: int, attempt_index: int) -> dict[str, str]:
    if not isinstance(attempt, dict):
        raise ValueError(  # noqa: TRY004 - error de datos de la cola, no de tipo de argumento
            f"Intento {attempt_index} del Lead {lead_index} no es un objeto válido."
        )
    validated = {}
    for field in ATTEMPT_FIELDS:
        value = attempt.get(field)
        if not isinstance(value, str):
            raise ValueError(  # noqa: TRY004 - error de datos de la cola, no de tipo de argumento
                f"Campo {field} del intento {attempt_index} del Lead {lead_index} no es texto."
            )
        validated[field] = value.strip()
    if not validated["result"]:
        raise ValueError(f"Campo result del intento {attempt_index} del Lead {lead_index} está vacío.")
    return validated


def _validate_lead(lead: object, lead_index: int) -> dict[str, object]:
    if not isinstance(lead, dict):
        raise ValueError(  # noqa: TRY004 - error de datos de la cola, no de tipo de argumento
            f"Lead {lead_index} de la cola no es un objeto válido."
        )
    lead_id = str(lead.get("lead_id") or "").strip()
    if not SALESFORCE_ID_PATTERN.fullmatch(lead_id):
        raise ValueError(f"Lead {lead_index} tiene un Lead ID inválido.")
    attempts = lead.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise ValueError(f"Lead {lead_index} no tiene intentos para documentar.")
    return {
        "lead_id": lead_id,
        "attempts": [
            _validate_attempt(attempt, lead_index, attempt_index)
            for attempt_index, attempt in enumerate(attempts)
        ],
    }


def load_queue(queue_path: str, queue_directory: Path) -> list[dict[str, object]]:
    allowed_directory = queue_directory.resolve()
    candidate_path = Path(queue_path).expanduser().resolve()
    if candidate_path.parent != allowed_directory:
        raise ValueError("La cola debe estar dentro del directorio local queues.")
    try:
        payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"La cola no es un JSON válido: {error.msg}") from error
    leads = payload.get("leads") if isinstance(payload, dict) else None
    if not isinstance(leads, list) or not leads:
        raise ValueError("La cola no contiene Leads pendientes.")
    return [_validate_lead(lead, index) for index, lead in enumerate(leads)]
