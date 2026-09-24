"""Carga y valida colas de corrección generadas desde la UI local.

Cada corrección lleva el texto completo de ``Otra información`` (dato de
cliente), por eso el archivo vive en ``ui_output/`` y nunca en ``queues/``
ni en el repositorio. Contrato del JSON::

    {
      "generated_at": "...",
      "source_file": "...",
      "corrections": [
        {"lead_id": "...", "new_value": "...", "base_hash": "<sha256 hex>"}
      ]
    }
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def _valid_correction(item: object) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("lead_id"), str)
        and item["lead_id"].strip()
        and isinstance(item.get("new_value"), str)
        and isinstance(item.get("base_hash"), str)
        and bool(_HEX_64.match(item["base_hash"]))
    )


def load_corrections(corrections_path: str) -> list[dict]:
    """Devuelve las correcciones válidas o lanza ValueError con el motivo."""
    path = Path(corrections_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"no existe el archivo: {path}")  # noqa: TRY003 - mensaje de uso para el operador
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON inválido: {error}") from error  # noqa: TRY003 - datos de archivo, no tipo de argumento

    corrections = data.get("corrections") if isinstance(data, dict) else data
    if not isinstance(corrections, list):
        raise ValueError("falta la lista 'corrections'")  # noqa: TRY003 - forma del JSON, no tipo de argumento
    invalid = [i for i, item in enumerate(corrections) if not _valid_correction(item)]
    if invalid:
        raise ValueError(  # noqa: TRY003 - validación de contenido del archivo
            f"{len(invalid)} correcciones inválidas (lead_id, new_value y base_hash sha256 requeridos)"
        )
    return corrections
