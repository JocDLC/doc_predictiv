"""Almacenamiento local privado de snapshots de ``Otra información``."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def snapshot_path_for(queue_path: str, output_directory: Path) -> Path:
    """Ubica los snapshots fuera de la cola y del repositorio."""
    return output_directory / f"{Path(queue_path).stem}.snapshots.json"


def content_hash(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def record_snapshot(snapshot_path: Path, lead_id: str, field_value: str) -> None:
    """Guarda el último valor confirmado, sin escribirlo en consola o logs."""
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
    }
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(list(snapshots.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
