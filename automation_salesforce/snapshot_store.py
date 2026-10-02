"""Almacenamiento local privado de snapshots de ``Otra información``."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from attempt_identity import documented_call_ids


def snapshot_path_for(queue_path: str, output_directory: Path) -> Path:
    """Ubica los snapshots fuera de la cola y del repositorio."""
    return output_directory / f"{Path(queue_path).stem}.snapshots.json"


def content_hash(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def record_snapshot(
    snapshot_path: Path,
    lead_id: str,
    field_value: str,
    run_id: str = "",
    call_ids: list[str] | None = None,
) -> None:
    """Guarda el último valor confirmado, sin escribirlo en consola o logs.

    ``run_id`` y ``call_ids`` identifican la ejecución y las llamadas que la
    lectura confirma; sin ellos la evidencia queda como histórica y no puede
    marcar intentos nuevos como documentados.
    """
    snapshots = {}
    if snapshot_path.exists():
        try:
            for item in json.loads(snapshot_path.read_text(encoding="utf-8")):
                snapshots[item["lead_id"]] = item
        except (json.JSONDecodeError, KeyError, TypeError):
            snapshots = {}

    snapshots[lead_id] = {
        "lead_id": lead_id,
        "field_value": field_value,
        "base_hash": content_hash(field_value),
        "read_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": str(run_id or ""),
        "call_ids": sorted(call_ids if call_ids is not None else documented_call_ids(field_value)),
    }
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(list(snapshots.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
