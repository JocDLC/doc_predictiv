"""Generación determinística del HTML autocontenido."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import OUTPUT_PATH, SOURCE_PATH, TECHNICAL_GRAPH_PATH, TEMPLATE_PATH
from .validator import load_contracts, scan_sensitive_text, validate_contracts

DATA_PLACEHOLDER = "__BUSINESS_CONTRACT_DATA__"


def render_graph(data: dict[str, Any], template: str) -> str:
    if template.count(DATA_PLACEHOLDER) != 1:
        raise ValueError("La plantilla debe contener exactamente un marcador de datos.")
    payload = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    payload = payload.replace("</", "<\\/")
    return template.replace(DATA_PLACEHOLDER, payload)


def generate_graph(
    *,
    source_path: Path = SOURCE_PATH,
    template_path: Path = TEMPLATE_PATH,
    output_path: Path = OUTPUT_PATH,
) -> Path:
    data = load_contracts(source_path)
    validate_contracts(data, output_path=output_path)
    if output_path.resolve() == TECHNICAL_GRAPH_PATH.resolve():
        raise ValueError(
            "La salida no puede sobrescribir el gráfico técnico protegido."
        )
    template = template_path.read_text(encoding="utf-8")
    rendered = render_graph(data, template)
    scan_sensitive_text(rendered, location="HTML generado")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8", newline="\n")
    return output_path
