"""Comprobante persistente de la recogida de apertura (REQ-834).

Un archivo JSON por lote en ``ui_output/apertura/``: encabezado con bandeja y
rango, y un lead por línea con su estado. Cada ``update_lead`` reescribe el
archivo atómicamente (tmp + replace) — un corte a mitad de toma nunca deja un
lote corrupto. Independiente de ``monitor_state.results``: el historial del
monitor se puede vaciar con un botón y el comprobante sobrevive.

Estados por lead: ``en_curso`` (seleccionado, clic pendiente o en vuelo) →
``tomado_confirmado`` | ``revisar`` | ``tomado_por_otro`` | ``error``. Al
reiniciar el servidor, ``reconciliar_en_curso`` pasa los ``en_curso`` a
``revisar``: el clic pudo haberse ejecutado sin persistirse, así que no se
reintenta a ciegas — se lista para verificación manual del propietario.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ESTADO_EN_CURSO = "en_curso"
ESTADO_TOMADO_CONFIRMADO = "tomado_confirmado"
ESTADO_REVISION = "revisar"
ESTADO_TOMADO_POR_OTRO = "tomado_por_otro"
ESTADO_ERROR = "error"
ESTADOS_FINAIS = (ESTADO_TOMADO_CONFIRMADO, ESTADO_REVISION, ESTADO_TOMADO_POR_OTRO, ESTADO_ERROR)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _lote_path(store_dir: Path, lote_id: str) -> Path:
    return store_dir / f"{lote_id}.json"


def _write_lote(store_dir: Path, lote: dict) -> None:
    store_dir.mkdir(parents=True, exist_ok=True)
    path = _lote_path(store_dir, lote["lote_id"])
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(lote, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp_path, path)


def create_lote(
    store_dir: Path,
    bandeja: str,
    desde: str,
    hasta: str,
    lead_ids: list[str],
    preview_id: str | None = None,
) -> dict:
    """Crea el lote con todos los seleccionados en ``en_curso`` y lo persiste
    antes de tocar Salesforce — el comprobante existe aunque la toma no corra."""
    lote_id = f"apertura_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{os.urandom(3).hex()}"
    lote = {
        "lote_id": lote_id,
        "preview_id": preview_id,
        "bandeja": bandeja,
        "desde": desde,
        "hasta": hasta,
        "creado": _utcnow(),
        "leads": {lead_id: {"estado": ESTADO_EN_CURSO, "actualizado": _utcnow()} for lead_id in lead_ids},
    }
    _write_lote(store_dir, lote)
    return lote


def load_lote(store_dir: Path, lote_id: str) -> dict:
    return json.loads(_lote_path(store_dir, lote_id).read_text(encoding="utf-8"))


def lotes(store_dir: Path) -> list[dict]:
    """Todos los lotes persistidos, más nuevos primero."""
    if not store_dir.is_dir():
        return []
    found = []
    for path in sorted(store_dir.glob("apertura_*.json"), reverse=True):
        try:
            found.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return found


def update_lead(
    store_dir: Path,
    lote_id: str,
    lead_id: str,
    estado: str,
    **fields,
) -> dict:
    """Resultado por lead, persistido atómicamente de inmediato."""
    lote = load_lote(store_dir, lote_id)
    entry = lote["leads"].setdefault(lead_id, {})
    entry["estado"] = estado
    entry["actualizado"] = _utcnow()
    entry.update(fields)
    _write_lote(store_dir, lote)
    return entry


def reconciliar_en_curso(store_dir: Path) -> int:
    """Arranque del servidor: los ``en_curso`` persistidos corresponden a tomas
    cuya escritura final no llegó — pasan a ``revisar`` para control manual."""
    changed = 0
    for lote in lotes(store_dir):
        dirty = False
        for entry in lote["leads"].values():
            if entry.get("estado") == ESTADO_EN_CURSO:
                entry["estado"] = ESTADO_REVISION
                entry["motivo"] = "interrumpido: reinicio del servidor"
                entry["actualizado"] = _utcnow()
                dirty = True
                changed += 1
        if dirty:
            _write_lote(store_dir, lote)
    return changed


def disponibles(store_dir: Path, bandeja: str | None = None) -> list[dict]:
    """Leads ``tomado_confirmado`` no consumidos, candidatos de Distribuir."""
    found = []
    for lote in lotes(store_dir):
        if bandeja and lote.get("bandeja") != bandeja:
            continue
        for lead_id, entry in lote["leads"].items():
            if entry.get("estado") == ESTADO_TOMADO_CONFIRMADO and not entry.get("consumido"):
                found.append(
                    {
                        "lead_id": lead_id,
                        "bandeja": lote.get("bandeja"),
                        "lote_id": lote["lote_id"],
                        "tomado": entry.get("actualizado"),
                    }
                )
    return found


def marcar_consumidos(store_dir: Path, lead_ids: list[str], run_id: str) -> int:
    """Marca los leads ya incorporados a una cola de distribución para no
    re-ofrecerlos; devuelve cuántos se marcaron."""
    wanted = set(lead_ids)
    marked = 0
    for lote in lotes(store_dir):
        dirty = False
        for lead_id, entry in lote["leads"].items():
            if lead_id in wanted and entry.get("estado") == ESTADO_TOMADO_CONFIRMADO and not entry.get("consumido"):
                entry["consumido"] = run_id
                entry["actualizado"] = _utcnow()
                dirty = True
                marked += 1
        if dirty:
            _write_lote(store_dir, lote)
    return marked
