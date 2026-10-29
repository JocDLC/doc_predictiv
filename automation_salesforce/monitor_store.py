"""Estado persistente del Monitor de Bandeja (``ui_output/monitor_state.json``).

Guarda habilitación, bandejas configuradas, franjas horarias y el último
resultado por Lead. El archivo vive fuera del repositorio (``ui_output/`` está
ignorado por Git); los ``details`` pueden contener datos de clientes igual que
los snapshots existentes, pero los logs solo usan ``lead_id`` enmascarado.

Contrato::

    {
      "enabled": false,
      "solo_listar": false,
      "bandejas": [{"code": "AR", "enabled": true, "url": "https://…/lightning/r/Report/…",
                    "unassigned_owner": "AR_LEAD_QUALIF", "expected_status": "Nuevo"}],
      "schedule": [{"start": "08:00", "end": "20:00"}],
      "last_cycle_at": "…ISO…",
      "paused_reason": null,
      "results": [{"lead_id": "00Q…", "bandeja": "AR", "status": "tomado",
                   "at": "…", "attempts": 1, "details": {…}}]
    }
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from comment_reader import SALESFORCE_ID_PATTERN
from local_audit import mask_lead_id

STATE_FILE_NAME = "monitor_state.json"
MAX_RESULTS = 200
MAX_ATTEMPTS = 2  # `error` y `no_verificado` admiten un solo reintento en el ciclo siguiente

BANDEJA_CODES = ("AR", "CO", "MX")
DEFAULT_EXPECTED_STATUS = "Nuevo"

STATUS_TOMADO = "tomado"
STATUS_TOMADO_POR_OTRO = "tomado_por_otro"
STATUS_NO_VERIFICADO = "no_verificado"
STATUS_ERROR = "error"
STATUS_DETECTADO = "detectado"  # modo prueba: listado sin Pick Up; siempre reprocesable
RESULT_STATUSES = frozenset(
    {STATUS_TOMADO, STATUS_TOMADO_POR_OTRO, STATUS_NO_VERIFICADO, STATUS_ERROR, STATUS_DETECTADO}
)
TERMINAL_STATUSES = frozenset({STATUS_TOMADO, STATUS_TOMADO_POR_OTRO})

# Razones de pausa visibles en la UI; `session_lost` también es tipo de evento SSE.
PAUSE_RUN_ACTIVO = "run_activo"
PAUSE_FUERA_DE_HORARIO = "fuera_de_horario"
PAUSE_SESSION_LOST = "session_lost"
PAUSE_SIN_BANDEJAS = "sin_bandejas"

HHMM_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def default_unassigned_owner(code: str) -> str:
    return f"{code}_LEAD_QUALIF"


# Diferencia horaria del país del lead respecto al país donde corre el bot
# (Colombia): la documentación de intentos (``1 INT ... DD/MM/AAAA HH:MM``)
# debe quedar en la hora del lead, no la local.
DEFAULT_TZ_OFFSETS = {"AR": 2, "CO": 0, "MX": -1}


def _is_lightning_report_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc) and "/lightning/r/Report/" in parsed.path


def validate_bandeja(entry: object) -> dict:
    """Valida y normaliza una bandeja: código, URL de reporte y filtros."""
    if not isinstance(entry, dict):
        raise ValueError("Cada bandeja debe ser un objeto.")
    code = str(entry.get("code") or "").strip().upper()
    if code not in BANDEJA_CODES:
        raise ValueError(f"Código de bandeja inválido: {code!r}. Usar AR, CO o MX.")
    url = str(entry.get("url") or "").strip()
    enabled = bool(entry.get("enabled"))
    if url and not _is_lightning_report_url(url):
        raise ValueError(f"La URL de la bandeja {code} no es un reporte Lightning https.")
    if enabled and not url:
        raise ValueError(f"La bandeja {code} está habilitada pero no tiene URL de reporte.")
    unassigned_owner = str(entry.get("unassigned_owner") or "").strip() or default_unassigned_owner(code)
    expected_status = str(entry.get("expected_status") or "").strip() or DEFAULT_EXPECTED_STATUS
    tz_offset = entry.get("tz_offset")
    if tz_offset is None:
        tz_offset = DEFAULT_TZ_OFFSETS.get(code, 0)
    try:
        tz_offset = int(tz_offset)
    except (TypeError, ValueError):
        raise ValueError(f"El ajuste horario de la bandeja {code} debe ser un entero de horas.") from None
    if not -12 <= tz_offset <= 12:
        raise ValueError(f"El ajuste horario de la bandeja {code} debe estar entre -12 y +12 horas.")
    return {
        "code": code,
        "enabled": enabled,
        "url": url,
        "unassigned_owner": unassigned_owner,
        "expected_status": expected_status,
        "tz_offset": tz_offset,
    }


def validate_bandejas(entries: object) -> list[dict]:
    if not isinstance(entries, list):
        raise ValueError("Se esperaba una lista de bandejas.")
    seen: set[str] = set()
    validated = []
    for entry in entries:
        bandeja = validate_bandeja(entry)
        if bandeja["code"] in seen:
            raise ValueError(f"Bandeja duplicada: {bandeja['code']}.")
        seen.add(bandeja["code"])
        validated.append(bandeja)
    return validated


def _parse_hhmm(value: object, label: str) -> int:
    text = str(value or "").strip()
    match = HHMM_PATTERN.fullmatch(text)
    if not match:
        raise ValueError(f"{label} debe tener formato HH:MM (recibido: {text!r}).")
    return int(match.group(1)) * 60 + int(text[3:5])


def _validate_franjas(slots: object, nombre: str) -> list[dict]:
    """Franjas ``HH:MM–HH:MM`` más ``bandejas`` (códigos, opcionales).

    ``nombre`` prefija los errores ("Micaela: ..."); vacío para el
    horario propio ("La franja 0 ..."). No chequea solapes — eso lo
    decide cada caller con su propia regla.
    ``_start_minutes``/``_end_minutes`` se devuelven para ese chequeo y
    luego se descartan.
    """
    prefix = f"{nombre}: " if nombre else ""
    if slots is None:
        return []
    if not isinstance(slots, list):
        raise ValueError(f"{prefix}Se esperaba una lista de franjas horarias.")
    normalized = []
    for index, slot in enumerate(slots):
        if not isinstance(slot, dict):
            raise ValueError(f"{prefix}La franja {index} debe ser un objeto con 'start' y 'end'.")
        start_minutes = _parse_hhmm(slot.get("start"), f"{prefix}franja {index} start")
        end_minutes = _parse_hhmm(slot.get("end"), f"{prefix}franja {index} end")
        if start_minutes >= end_minutes:
            raise ValueError(f"{prefix}La franja {index} empieza después de que termina.")
        raw_codes = slot.get("bandejas")
        bandejas = []
        if raw_codes is not None:
            if not isinstance(raw_codes, list):
                raise ValueError(f"{prefix}'bandejas' de la franja {index} debe ser una lista de códigos.")
            for raw_code in raw_codes:
                code = str(raw_code or "").strip()
                if not code:
                    raise ValueError(f"{prefix}Código de bandeja vacío en la franja {index}.")
                if code not in bandejas:
                    bandejas.append(code)
        normalized.append(
            {
                "start": str(slot["start"]).strip(),
                "end": str(slot["end"]).strip(),
                "bandejas": bandejas,
                "_start_minutes": start_minutes,
                "_end_minutes": end_minutes,
            }
        )
    normalized.sort(key=lambda item: item["_start_minutes"])
    return normalized


def _franjas_se_solapan(first: dict, second: dict) -> bool:
    """Solape prohibido: mismo rango horario y MISMA bandeja. Una franja
    sin bandejas ('todas' en horario propio / 'ninguna' en equipo) pisa
    todo lo que la solape."""
    if second["_start_minutes"] >= first["_end_minutes"]:
        return False
    return (
        not first["bandejas"]
        or not second["bandejas"]
        or bool(set(first["bandejas"]) & set(second["bandejas"]))
    )


def validate_schedule(slots: object) -> list[dict]:
    """Franjas propias ``HH:MM–HH:MM`` ordenadas, con ``bandejas``
    opcionales. ``bandejas`` vacía o ausente = la franja cubre TODAS las
    bandejas — las franjas viejas sin el campo siguen tomando todo.
    Dos franjas SÍ pueden solaparse si cubren bandejas distintas
    (AR 10–12 + CO 11–13); el solape prohibido es dentro de la misma
    bandeja — o con una franja "todas", que las cubre todas."""
    normalized = _validate_franjas(slots, "")
    for index, current in enumerate(normalized):
        for previous in normalized[:index]:
            if _franjas_se_solapan(previous, current):
                raise ValueError(
                    f"Las franjas {previous['start']}–{previous['end']} y "
                    f"{current['start']}–{current['end']} se solapan en la misma bandeja."
                )
    return [
        {"start": item["start"], "end": item["end"], "bandejas": item["bandejas"]}
        for item in normalized
    ]


def _validate_equipo_franjas(slots: object, nombre: str) -> list[dict]:
    """Franjas de una persona del equipo: misma forma que las propias.

    Dos franjas de equipo SÍ pueden solaparse en el tiempo si cubren
    bandejas distintas (una persona atiende AR 10–12 y CO 11–13). El
    solape prohibido es dentro de la misma bandeja — se valida en
    ``_check_bandeja_overlaps``.
    """
    return _validate_franjas(slots, nombre)


def _check_bandeja_overlaps(validated: list[dict]) -> None:
    """Rechaza franjas que se solapan en la MISMA bandeja — entre personas
    distintas o dentro de la misma persona. En bandejas distintas el solape
    es legal (Roger cubre AR 10–12 y CO 11–13 a la vez).
    """
    coverage: dict[str, list[tuple[int, int, str]]] = {}
    for member in validated:
        for slot in member["franjas"]:
            label = f"{member['nombre']} {slot['start']}–{slot['end']}"
            for code in slot["bandejas"]:
                coverage.setdefault(code, []).append(
                    (slot["_start_minutes"], slot["_end_minutes"], label)
                )
    for code, intervals in coverage.items():
        intervals.sort(key=lambda item: item[0])
        for previous, current in zip(intervals, intervals[1:]):
            if current[0] < previous[1]:
                raise ValueError(
                    f"Franjas de {code} solapadas: {previous[2]} y {current[2]}."
                )


def validate_equipo(members: object) -> list[dict]:
    """Valida la lista de personas destinatarias de leads reasignados.

    Cada entrada: ``nombre`` exacto como en el lookup de Salesforce y
    ``franjas`` ``HH:MM–HH:MM`` con ``bandejas`` (códigos de las bandejas
    que esa franja cubre). Una franja sin ``bandejas`` no cubre nada —
    las franjas viejas sin el campo quedan inertes hasta re-cargarlas.
    """
    if members is None:
        return []
    if not isinstance(members, list):
        raise ValueError("Se esperaba una lista de personas del equipo.")
    validated = []
    for index, member in enumerate(members):
        if not isinstance(member, dict):
            raise ValueError(f"La persona {index} debe ser un objeto con 'nombre' y 'franjas'.")
        nombre = str(member.get("nombre") or "").strip()
        if not nombre:
            raise ValueError(f"La persona {index} necesita el nombre exacto de Salesforce.")
        validated.append(
            {
                "nombre": nombre,
                "franjas": _validate_equipo_franjas(member.get("franjas"), nombre),
            }
        )
    _check_bandeja_overlaps(validated)
    return [
        {
            "nombre": member["nombre"],
            "franjas": [
                {"start": slot["start"], "end": slot["end"], "bandejas": slot["bandejas"]}
                for slot in member["franjas"]
            ],
        }
        for member in validated
    ]


def within_schedule(
    slots: list[dict[str, str]],
    moment: datetime | None = None,
    bandeja: str | object | None = None,
) -> bool:
    """Lista vacía = siempre dentro de horario; con franjas, exige estar en una.

    ``bandeja`` (un código o un iterable de códigos) exige además que la
    franja vigente la cubra: una franja sin ``bandejas`` vale para todas.
    """
    if not slots:
        return True
    wanted = None
    if bandeja is not None:
        wanted = {bandeja} if isinstance(bandeja, str) else set(bandeja)
    current = moment or datetime.now().astimezone()
    now_minutes = current.hour * 60 + current.minute
    for slot in slots:
        if wanted is not None and slot.get("bandejas") and not wanted & set(slot["bandejas"]):
            continue
        if _parse_hhmm(slot["start"], "start") <= now_minutes < _parse_hhmm(slot["end"], "end"):
            return True
    return False


def default_state() -> dict:
    return {
        "enabled": False,
        "solo_listar": False,
        "enviar_whatsapp": False,
        "notificar": True,
        "bandejas": [],
        "schedule": [],
        "equipo": [],
        "bot_owner": None,
        "last_cycle_at": None,
        "paused_reason": None,
        "monitor_url": None,
        "results": [],
    }


def load_state(state_path: Path) -> dict:
    """Lectura tolerante: un archivo ausente o roto devuelve el estado inicial."""
    state = default_state()
    try:
        payload = json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return state
    if not isinstance(payload, dict):
        return state
    state["enabled"] = bool(payload.get("enabled"))
    state["solo_listar"] = bool(payload.get("solo_listar"))
    state["enviar_whatsapp"] = bool(payload.get("enviar_whatsapp"))
    state["notificar"] = bool(payload.get("notificar", True))
    try:
        state["bandejas"] = validate_bandejas(payload.get("bandejas") or [])
        state["schedule"] = validate_schedule(payload.get("schedule"))
        state["equipo"] = validate_equipo(payload.get("equipo"))
    except ValueError:
        # Config inválida en disco: se descarta pero se conservan los resultados.
        state["bandejas"] = []
        state["schedule"] = []
        state["equipo"] = []
    if isinstance(payload.get("last_cycle_at"), str):
        state["last_cycle_at"] = payload["last_cycle_at"]
    if isinstance(payload.get("paused_reason"), str):
        state["paused_reason"] = payload["paused_reason"]
    if isinstance(payload.get("monitor_url"), str):
        state["monitor_url"] = payload["monitor_url"]
    if isinstance(payload.get("bot_owner"), str):
        state["bot_owner"] = payload["bot_owner"]
    if isinstance(payload.get("results"), list):
        state["results"] = [
            item
            for item in payload["results"]
            if isinstance(item, dict) and SALESFORCE_ID_PATTERN.fullmatch(str(item.get("lead_id") or ""))
        ][-MAX_RESULTS:]
    return state


def save_state(state_path: Path, state: dict) -> None:
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_results(state: dict) -> int:
    """Vacía el historial local sin alterar la configuración del monitor."""
    removed = len(state.get("results", []))
    state["results"] = []
    return removed


def _result_index(state: dict) -> dict[str, dict]:
    return {item["lead_id"]: item for item in state.get("results", []) if item.get("lead_id")}


def should_process(state: dict, lead_id: str) -> bool:
    """Estados finales no se reprocesan; ``error`` y ``no_verificado``
    admiten un reintento — el ciclo siguiente relee el propietario antes
    de clicar (no es un clic a ciegas: si otro lo tomó, sale
    ``tomado_por_otro``) — y ``detectado`` (modo prueba) siempre vuelve a
    evaluarse: al apagar el modo el Lead debe poder tomarse."""
    previous = _result_index(state).get(lead_id)
    if previous is None:
        return True
    if previous.get("status") == STATUS_DETECTADO:
        return True
    if previous.get("status") in (STATUS_ERROR, STATUS_NO_VERIFICADO):
        return int(previous.get("attempts") or 1) < MAX_ATTEMPTS
    return False


def record_result(
    state: dict,
    lead_id: str,
    bandeja: str,
    status: str,
    details: dict | None = None,
    extra: dict | None = None,
) -> dict:
    """Registra el último estado del Lead (uno nuevo reemplaza al anterior).

    ``extra`` agrega campos sueltos al resultado — por ejemplo
    ``asignado_a`` con el propietario observado tras el Pick Up.
    """
    if not SALESFORCE_ID_PATTERN.fullmatch(str(lead_id or "")):
        raise ValueError(f"Lead ID inválido para el monitor: {mask_lead_id(lead_id)}")
    if status not in RESULT_STATUSES:
        raise ValueError(f"Estado de monitor desconocido: {status!r}.")
    results = _result_index(state)
    previous = results.get(lead_id)
    attempts = int(previous.get("attempts") or 0) + 1 if previous else 1
    entry = {
        "lead_id": lead_id,
        "bandeja": str(bandeja or ""),
        "status": status,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "attempts": attempts,
    }
    if details:
        entry["details"] = details
    if extra:
        entry.update(extra)
    results[lead_id] = entry
    state["results"] = list(results.values())[-MAX_RESULTS:]
    return entry


def touch_cycle(state: dict, paused_reason: str | None = None) -> None:
    state["last_cycle_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state["paused_reason"] = paused_reason
