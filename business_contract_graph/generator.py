"""Generación determinística del candidato Workflow v2 para Archify."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from page_identity import publish_decorated_html, verify_decorated_html

from .paths import (
    ARCHIFY_OUTPUT_PATH,
    CANDIDATE_PATH,
    FINALIZE_SUMMARY_PATH,
    PUBLISHED_OUTPUT_PATH,
    REPOSITORY_ROOT,
    SOURCE_PATH,
    TECHNICAL_GRAPH_PATH,
    VISUAL_EVIDENCE_DIRECTORY,
    WORKFLOW_DIRECTORY,
)
from .validator import (
    ContractValidationError,
    load_contracts,
    scan_sensitive_text,
    sha256,
    validate_contracts,
)

REPOSITORY_URL = "https://github.com/JocDLC/doc_predictiv.git"
REPOSITORY_REVISION = "535941b72f628ec2014ca463188509134b1a08ee"

NODE_LAYOUT: dict[str, tuple[str, int, str, str]] = {
    "salesforce-csv": ("campaign", 0, "database", "Entrada · CSV"),
    "prepare-wolkvox-file": ("campaign", 1, "backend", "Base → archivo"),
    "wolkvox-ready-csv": ("campaign", 2, "database", "Salida · CSV"),
    "upload-wolkvox-campaign": ("campaign", 3, "cloud", "Acción externa"),
    "wolkvox-attempts-csv": ("results", 0, "database", "Entrada · CSV"),
    "organize-call-attempts": ("results", 1, "backend", "Ordena pendientes"),
    "select-documentation-batch": ("results", 2, "frontend", "Pendientes → lote"),
    "document-manually": ("manual", 3, "frontend", "Registro humano"),
    "document-with-bot": ("bot", 3, "backend", "Registro del bot"),
    "confirm-salesforce-documentation": (
        "results",
        4,
        "cloud",
        "Registrar y confirmar",
    ),
    "review-results": ("results", 5, "security", "Resumen operativo"),
    "apply-safe-correction": ("manual", 5, "security", "Revisa y corrige"),
}

TYPE_TAGS = {
    "system": "Automático",
    "manual": "Decisión manual",
    "external": "Manual · Externo",
    "control": "Control",
}

NODE_TAGS = {
    "confirm-salesforce-documentation": "Externo",
}

NODE_WIDTHS = {
    "confirm-salesforce-documentation": 180,
    "organize-call-attempts": 180,
}

NODE_LABELS = {
    "salesforce-csv": "CSV de Salesforce",
    "prepare-wolkvox-file": "Preparar CSV",
    "wolkvox-ready-csv": "CSV Wolkvox",
    "upload-wolkvox-campaign": "Subir a Wolkvox",
    "wolkvox-attempts-csv": "CSV con intentos",
    "organize-call-attempts": "Ordenar Intentos llamadas",
    "select-documentation-batch": "Elegir lote",
    "document-manually": "Ruta manual",
    "document-with-bot": "Ruta con bot",
    "confirm-salesforce-documentation": "Documentar en Salesforce",
    "review-results": "Ver resultados",
    "apply-safe-correction": "Corregir",
}

EDGE_LABELS = {
    "sf-file-to-prepare": "Base",
    "prepare-to-wolkvox-file": "Validado",
    "wolkvox-file-to-upload": "Campaña",
    "attempts-to-organize": "Intentos",
    "organize-to-select": "Pendientes",
    "organize-to-manual": "Manual",
    "select-to-bot": "Bot",
    "manual-to-confirm": "Registrado",
    "bot-to-confirm": "Guardado",
    "confirm-to-results": "Confirmado",
    "results-to-correction": "Corregir",
    "correction-to-confirm": "Revalidar",
}

EDGE_STYLES = {
    "primary": ("default", "main"),
    "manual": ("default", "branch"),
    "automated": ("emphasis", "branch"),
    "correction": ("dashed", "error"),
}


def _source_reference(reference: str, label: str) -> dict[str, Any]:
    path, separator, suffix = reference.rpartition(":")
    source: dict[str, Any] = {
        "path": path if separator and suffix.isdigit() else reference,
        "label": label,
    }
    if separator and suffix.isdigit():
        source["line"] = int(suffix)
    return source


def _heading_line(relative_path: str, heading: str) -> int:
    spec_path = REPOSITORY_ROOT / relative_path
    for line_number, line in enumerate(
        spec_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line == heading:
            return line_number
    raise ContractValidationError(
        f"No se encontró el encabezado OpenSpec para el candidato: {heading}."
    )


def _contract_sources(contract: dict[str, Any]) -> list[dict[str, Any]]:
    sources = [_source_reference(contract["implementation_refs"][0], "Implementación")]
    for reference in contract["spec_refs"][:2]:
        sources.append(
            {
                "path": reference["path"],
                "line": _heading_line(
                    reference["path"],
                    f"### Requirement: {reference['requirement']}",
                ),
                "label": "Contrato OpenSpec",
            }
        )
    return sources


def _artifact_node(artifact: dict[str, Any]) -> dict[str, Any]:
    lane, col, node_type, sublabel = NODE_LAYOUT[artifact["id"]]
    return {
        "id": artifact["id"],
        "lane": lane,
        "col": col,
        "type": node_type,
        "label": NODE_LABELS.get(artifact["id"], artifact["name"]),
        "sublabel": sublabel,
        "tag": "CSV vigente",
        "icon": "database",
        "sources": [
            _source_reference(artifact["implementation_refs"][0], "Implementación")
        ],
        "width": 110,
    }


def _macrofunction_node(contract: dict[str, Any]) -> dict[str, Any]:
    lane, col, node_type, sublabel = NODE_LAYOUT[contract["id"]]
    return {
        "id": contract["id"],
        "lane": lane,
        "col": col,
        "type": node_type,
        "label": NODE_LABELS.get(contract["id"], contract["name"]),
        "sublabel": sublabel,
        "tag": NODE_TAGS.get(contract["id"], TYPE_TAGS[contract["activity_type"]]),
        "sources": _contract_sources(contract),
        "width": NODE_WIDTHS.get(contract["id"], 110),
    }


def _contract_card(contract: dict[str, Any]) -> dict[str, Any]:
    dot_by_type = {
        "system": "cyan",
        "manual": "amber",
        "external": "violet",
        "control": "emerald",
    }
    return {
        "dot": dot_by_type[contract["activity_type"]],
        "title": contract["name"],
        "items": [
            f"Qué recibe: {contract['inputs'][0]}",
            f"Qué entrega: {contract['outputs'][0]}",
            f"Regla principal: {contract['rules'][0]}",
            f"Si falla: {contract['failure_behavior'][0]}",
        ],
    }


def build_candidate(data: dict[str, Any]) -> dict[str, Any]:
    """Transforma el modelo contractual en un Workflow v2 nativo de Archify."""

    validate_contracts(data)
    artifacts = [_artifact_node(item) for item in data["artifacts"]]
    macrofunctions = [_macrofunction_node(item) for item in data["macrofunctions"]]
    edges = []
    for relationship in data["relationships"]:
        variant, role = EDGE_STYLES[relationship["kind"]]
        edge: dict[str, Any] = {
            "id": relationship["id"],
            "from": relationship["from"],
            "to": relationship["to"],
            "label": EDGE_LABELS[relationship["id"]],
            "variant": variant,
            "role": role,
        }
        if relationship["id"] == "correction-to-confirm":
            edge["role"] = "return"
        edges.append(edge)

    candidate = {
        "schema_version": 2,
        "diagram_type": "workflow",
        "meta": {
            "title": data["title"],
            "subtitle": data["subtitle"],
            "animation": "none",
            "quality_profile": "showcase",
            "output": data["archify_output"],
            "repository": {
                "url": REPOSITORY_URL,
                "provider": "github",
                "link_mode": "web",
                "revision": REPOSITORY_REVISION,
            },
            "legend": {
                "mode": "all",
                "entries": {
                    "frontend": {"label": "Decisión manual"},
                    "backend": {"label": "Trabajo automático"},
                    "database": {"label": "Archivo CSV"},
                    "cloud": {"label": "Sistema externo"},
                    "security": {"label": "Control y verificación"},
                    "messagebus": {"visible": False},
                    "external": {"visible": False},
                },
            },
        },
        "lanes": [
            {"id": "campaign", "label": "1 · Salesforce → Wolkvox"},
            {"id": "results", "label": "2 · Wolkvox → Salesforce"},
            {"id": "manual", "label": "Intervención humana"},
            {"id": "bot", "label": "Opción con bot"},
        ],
        "phases": [
            {"id": "receive", "label": "Recibir", "fromCol": 0, "toCol": 0},
            {
                "id": "prepare",
                "label": "Organizar",
                "fromCol": 1,
                "toCol": 2,
                "variant": "emphasis",
            },
            {"id": "act", "label": "Actuar", "fromCol": 3, "toCol": 4},
            {
                "id": "review",
                "label": "Revisar",
                "fromCol": 5,
                "toCol": 5,
                "variant": "dashed",
            },
        ],
        "groups": [
            {
                "id": "campaign_path",
                "label": "Archivo preparado sin ajustes manuales",
                "lane": "campaign",
                "fromCol": 0,
                "toCol": 3,
                "variant": "emphasis",
            },
            {
                "id": "manual_path",
                "label": "El operador registra",
                "lane": "manual",
                "fromCol": 3,
                "toCol": 3,
            },
            {
                "id": "bot_path",
                "label": "El bot registra",
                "lane": "bot",
                "fromCol": 3,
                "toCol": 3,
                "variant": "emphasis",
            },
            {
                "id": "correction_path",
                "label": "Solo si hace falta corregir",
                "lane": "manual",
                "fromCol": 5,
                "toCol": 5,
                "variant": "dashed",
            },
        ],
        "semanticChecks": {
            "allowedRoots": ["salesforce-csv", "wolkvox-attempts-csv"],
            "allowedTerminals": ["upload-wolkvox-campaign", "review-results"],
            "requiredPaths": [
                {"from": "salesforce-csv", "to": "upload-wolkvox-campaign"},
                {"from": "organize-call-attempts", "to": "document-manually"},
                {"from": "select-documentation-batch", "to": "document-with-bot"},
                {"from": "document-manually", "to": "confirm-salesforce-documentation"},
                {"from": "document-with-bot", "to": "confirm-salesforce-documentation"},
            ],
        },
        "nodes": [*artifacts, *macrofunctions],
        "edges": edges,
        "cards": [_contract_card(item) for item in data["macrofunctions"]],
    }
    scan_sensitive_text(
        json.dumps(candidate, ensure_ascii=False), location="candidato Archify"
    )
    return candidate


def generate_candidate(
    *, source_path: Path = SOURCE_PATH, candidate_path: Path = CANDIDATE_PATH
) -> Path:
    data = load_contracts(source_path)
    candidate = build_candidate(data)
    rendered = json.dumps(candidate, ensure_ascii=False, indent=2) + "\n"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(rendered, encoding="utf-8", newline="\n")
    return candidate_path


def verify_archify_artifacts() -> None:
    """Comprueba que Archify finalizó el candidato y que la copia publicada coincide."""

    for path in (CANDIDATE_PATH, ARCHIFY_OUTPUT_PATH, FINALIZE_SUMMARY_PATH):
        if not path.is_file():
            raise ContractValidationError(f"Falta el artefacto Archify: {path}.")
    summary = json.loads(FINALIZE_SUMMARY_PATH.read_text(encoding="utf-8"))
    if not summary.get("ok") or summary.get("status") != "pass":
        raise ContractValidationError(
            "El recibo de finalización Archify no está aprobado."
        )
    expected_gates = {"validate", "deliver", "check", "browser-check"}
    gates = summary.get("gates", {})
    if any(gates.get(gate) != "pass" for gate in expected_gates):
        raise ContractValidationError("No pasaron todos los gates nativos de Archify.")
    if summary.get("type") != "workflow" or summary.get("quality") != "showcase":
        raise ContractValidationError(
            "El artefacto debe ser un workflow Archify con calidad showcase."
        )
    if summary.get("artifact", {}).get("sha256") != sha256(ARCHIFY_OUTPUT_PATH):
        raise ContractValidationError("El HTML no coincide con el recibo de Archify.")
    if not PUBLISHED_OUTPUT_PATH.is_file():
        raise ContractValidationError("Falta la copia publicada del workflow.")
    try:
        verify_decorated_html(
            ARCHIFY_OUTPUT_PATH.read_text(encoding="utf-8"),
            PUBLISHED_OUTPUT_PATH.read_text(encoding="utf-8"),
            "business-flow",
        )
    except ValueError as exc:
        raise ContractValidationError(str(exc)) from exc
    if PUBLISHED_OUTPUT_PATH.resolve() == TECHNICAL_GRAPH_PATH.resolve():
        raise ContractValidationError("La publicación apunta al gráfico técnico.")

    evidence_files = {
        CANDIDATE_PATH,
        ARCHIFY_OUTPUT_PATH,
        PUBLISHED_OUTPUT_PATH,
        *WORKFLOW_DIRECTORY.rglob("*.json"),
        *VISUAL_EVIDENCE_DIRECTORY.glob("*.json"),
        *VISUAL_EVIDENCE_DIRECTORY.glob("*.html"),
    }
    for evidence_path in evidence_files:
        scan_sensitive_text(
            evidence_path.read_text(encoding="utf-8"),
            location=f"evidencia Archify {evidence_path.name}",
        )
    for image_path in VISUAL_EVIDENCE_DIRECTORY.glob("*.png"):
        scan_sensitive_text(image_path.name, location="nombre de captura Archify")


def publish_archify_artifact() -> Path:
    """Publica una copia decorada del HTML ya finalizado por Archify."""

    if not ARCHIFY_OUTPUT_PATH.is_file() or not FINALIZE_SUMMARY_PATH.is_file():
        raise ContractValidationError(
            "Archify debe finalizar el workflow antes de publicarlo."
        )
    summary = json.loads(FINALIZE_SUMMARY_PATH.read_text(encoding="utf-8"))
    if not summary.get("ok") or summary.get("status") != "pass":
        raise ContractValidationError("No se publica un workflow Archify no aprobado.")
    html = ARCHIFY_OUTPUT_PATH.read_text(encoding="utf-8")
    scan_sensitive_text(html, location="HTML Archify")
    publish_decorated_html(ARCHIFY_OUTPUT_PATH, PUBLISHED_OUTPUT_PATH, "business-flow")
    return PUBLISHED_OUTPUT_PATH
