"""Validación del modelo de negocio, su trazabilidad y su privacidad."""

from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from pathlib import Path
from typing import Any

from .paths import (
    ARCHIFY_OUTPUT_PATH,
    CANDIDATE_PATH,
    EXPECTED_TECHNICAL_GRAPH_SHA256,
    PUBLISHED_OUTPUT_PATH,
    REPOSITORY_ROOT,
    TECHNICAL_GRAPH_PATH,
)

REQUIRED_ROOT_FIELDS = {
    "schema_version",
    "title",
    "subtitle",
    "revision",
    "technical_artifact",
    "candidate_output",
    "archify_output",
    "published_output",
    "allowed_spec_paths",
    "journeys",
    "artifacts",
    "macrofunctions",
    "relationships",
}
REQUIRED_JOURNEY_FIELDS = {"id", "name", "purpose"}
REQUIRED_ARTIFACT_FIELDS = {
    "id",
    "journey_id",
    "name",
    "summary",
    "artifact_type",
    "format",
    "implementation_refs",
}
REQUIRED_CONTRACT_FIELDS = {
    "id",
    "journey_id",
    "activity_type",
    "name",
    "summary",
    "purpose",
    "inputs",
    "outputs",
    "rules",
    "failure_behavior",
    "spec_refs",
    "implementation_refs",
    "test_refs",
    "verification_status",
}
REQUIRED_RELATIONSHIP_FIELDS = {"id", "from", "to", "label", "kind"}
CONTRACT_LIST_FIELDS = {"inputs", "outputs", "rules", "failure_behavior"}
ALLOWED_STATUSES = {"verified", "partial", "pending"}
ALLOWED_ACTIVITY_TYPES = {"system", "manual", "external", "control"}
ALLOWED_ARTIFACT_TYPES = {"input", "output"}
ALLOWED_RELATIONSHIP_KINDS = {
    "primary",
    "manual",
    "automated",
    "correction",
}
REQUIRED_JOURNEYS = {"salesforce-to-wolkvox", "wolkvox-to-salesforce"}
SENSITIVE_PATTERNS = {
    "canario sensible": re.compile(r"SENSITIVE[-_ ]CANARY", re.IGNORECASE),
    "correo electrónico": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
    ),
    "ID real de Lead": re.compile(r"\b00Q[A-Za-z0-9]{12,15}\b"),
    "credencial": re.compile(
        r"\b(?:password|passwd|api[_-]?key|secret|cookie)\s*[:=]", re.IGNORECASE
    ),
}


class ContractValidationError(ValueError):
    """Error identificable que impide publicar el gráfico."""


def load_contracts(source_path: Path) -> dict[str, Any]:
    try:
        return json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractValidationError(
            f"No se pudo leer la fuente contractual: {exc}"
        ) from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def scan_sensitive_text(text: str, *, location: str) -> None:
    for label, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(text):
            raise ContractValidationError(
                f"Contenido sensible detectado ({label}) en {location}."
            )


def _require_fields(item: dict[str, Any], required: set[str], location: str) -> None:
    missing = sorted(required - item.keys())
    if missing:
        raise ContractValidationError(
            f"{location}: faltan campos obligatorios: {', '.join(missing)}."
        )


def _require_non_empty_string(value: Any, location: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{location}: se esperaba texto no vacío.")


def _require_non_empty_list(value: Any, location: str) -> None:
    if not isinstance(value, list) or not value:
        raise ContractValidationError(f"{location}: se esperaba una lista no vacía.")
    for index, entry in enumerate(value):
        _require_non_empty_string(entry, f"{location}[{index}]")


def _safe_repository_path(relative_path: str, location: str) -> Path:
    candidate = (REPOSITORY_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(REPOSITORY_ROOT.resolve())
    except ValueError as exc:
        raise ContractValidationError(
            f"{location}: la ruta sale del repositorio."
        ) from exc
    return candidate


def _evidence_path(reference: str) -> str:
    path, separator, suffix = reference.rpartition(":")
    return path if separator and suffix.isdigit() else reference


def _validate_evidence_refs(references: Any, location: str) -> None:
    if not isinstance(references, list):
        raise ContractValidationError(f"{location}: se esperaba una lista.")
    for index, reference in enumerate(references):
        _require_non_empty_string(reference, f"{location}[{index}]")
        evidence_path = _safe_repository_path(
            _evidence_path(reference), f"{location}[{index}]"
        )
        if not evidence_path.is_file():
            raise ContractValidationError(
                f"{location}: evidencia inexistente: {reference}."
            )


def _validate_spec_ref(
    reference: Any,
    *,
    macrofunction_id: str,
    allowed_paths: set[str],
    seen_refs: set[tuple[str, str]],
) -> None:
    location = f"macrofunción {macrofunction_id}.spec_refs"
    if not isinstance(reference, dict):
        raise ContractValidationError(
            f"{location}: cada referencia debe ser un objeto."
        )
    _require_fields(reference, {"path", "requirement", "scenarios"}, location)
    path = reference["path"]
    requirement = reference["requirement"]
    scenarios = reference["scenarios"]
    _require_non_empty_string(path, f"{location}.path")
    _require_non_empty_string(requirement, f"{location}.requirement")
    if path not in allowed_paths:
        raise ContractValidationError(
            f"{location}: fuente no permitida o archivada: {path}."
        )
    if "archive" in Path(path).parts:
        raise ContractValidationError(
            f"{location}: no se admiten fuentes archivadas: {path}."
        )
    key = (path, requirement)
    if key in seen_refs:
        raise ContractValidationError(
            f"{location}: referencia duplicada: {path} :: {requirement}."
        )
    seen_refs.add(key)

    spec_path = _safe_repository_path(path, location)
    if not spec_path.is_file():
        raise ContractValidationError(
            f"{location}: no existe la fuente OpenSpec: {path}."
        )
    spec_text = spec_path.read_text(encoding="utf-8")
    requirement_heading = f"### Requirement: {requirement}"
    if spec_text.count(requirement_heading) != 1:
        raise ContractValidationError(
            f"{location}: requisito inexistente o ambiguo en {path}: {requirement}."
        )
    _require_non_empty_list(scenarios, f"{location}.scenarios")
    for scenario in scenarios:
        heading = f"#### Scenario: {scenario}"
        if spec_text.count(heading) != 1:
            raise ContractValidationError(
                f"{location}: escenario inexistente o ambiguo en {path}: {scenario}."
            )


def _validate_journeys(data: dict[str, Any]) -> set[str]:
    journeys = data["journeys"]
    if not isinstance(journeys, list):
        raise ContractValidationError("journeys: se esperaba una lista.")
    journey_ids: set[str] = set()
    for index, journey in enumerate(journeys):
        location = f"journeys[{index}]"
        if not isinstance(journey, dict):
            raise ContractValidationError(f"{location}: se esperaba un objeto.")
        _require_fields(journey, REQUIRED_JOURNEY_FIELDS, location)
        for field in REQUIRED_JOURNEY_FIELDS:
            _require_non_empty_string(journey[field], f"{location}.{field}")
        if journey["id"] in journey_ids:
            raise ContractValidationError(f"{location}: ID duplicado: {journey['id']}.")
        journey_ids.add(journey["id"])
    if journey_ids != REQUIRED_JOURNEYS:
        raise ContractValidationError(
            "journeys: deben existir los caminos Salesforce → Wolkvox y Wolkvox → Salesforce."
        )
    return journey_ids


def _validate_artifacts(data: dict[str, Any], journey_ids: set[str]) -> set[str]:
    artifacts = data["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise ContractValidationError("artifacts: se esperaba una lista no vacía.")
    artifact_ids: set[str] = set()
    for index, artifact in enumerate(artifacts):
        location = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            raise ContractValidationError(f"{location}: se esperaba un objeto.")
        _require_fields(artifact, REQUIRED_ARTIFACT_FIELDS, location)
        for field in ("id", "name", "summary", "format"):
            _require_non_empty_string(artifact[field], f"{location}.{field}")
        if artifact["id"] in artifact_ids:
            raise ContractValidationError(
                f"{location}: ID duplicado: {artifact['id']}."
            )
        artifact_ids.add(artifact["id"])
        if artifact["journey_id"] not in journey_ids:
            raise ContractValidationError(f"{location}: camino inexistente.")
        if artifact["artifact_type"] not in ALLOWED_ARTIFACT_TYPES:
            raise ContractValidationError(f"{location}: tipo de artefacto desconocido.")
        if artifact["format"].upper() != "CSV":
            raise ContractValidationError(
                f"{location}: el formato operativo vigente debe ser CSV."
            )
        _validate_evidence_refs(
            artifact["implementation_refs"], f"{location}.implementation_refs"
        )
    return artifact_ids


def _validate_macrofunctions(
    data: dict[str, Any], journey_ids: set[str], allowed_paths: set[str]
) -> set[str]:
    macrofunctions = data["macrofunctions"]
    if not isinstance(macrofunctions, list) or len(macrofunctions) != 9:
        raise ContractValidationError(
            "macrofunctions: deben existir exactamente nueve macrofunciones."
        )

    ids: set[str] = set()
    activity_types: set[str] = set()
    for index, contract in enumerate(macrofunctions):
        location = f"macrofunctions[{index}]"
        if not isinstance(contract, dict):
            raise ContractValidationError(f"{location}: se esperaba un objeto.")
        _require_fields(contract, REQUIRED_CONTRACT_FIELDS, location)
        contract_id = contract["id"]
        _require_non_empty_string(contract_id, f"{location}.id")
        if contract_id in ids:
            raise ContractValidationError(f"{location}: ID duplicado: {contract_id}.")
        ids.add(contract_id)
        if contract["journey_id"] not in journey_ids:
            raise ContractValidationError(f"{location}: camino inexistente.")
        activity_type = contract["activity_type"]
        if activity_type not in ALLOWED_ACTIVITY_TYPES:
            raise ContractValidationError(
                f"{location}.activity_type: tipo de actividad desconocido."
            )
        activity_types.add(activity_type)
        for field in ("name", "summary", "purpose"):
            _require_non_empty_string(contract[field], f"{location}.{field}")
        for field in CONTRACT_LIST_FIELDS:
            _require_non_empty_list(contract[field], f"{location}.{field}")
        if not isinstance(contract["spec_refs"], list) or not contract["spec_refs"]:
            raise ContractValidationError(
                f"{location}.spec_refs: falta una fuente OpenSpec."
            )
        for field in ("implementation_refs", "test_refs"):
            _validate_evidence_refs(contract[field], f"{location}.{field}")
        status = contract["verification_status"]
        if status not in ALLOWED_STATUSES:
            raise ContractValidationError(
                f"{location}.verification_status: estado desconocido: {status}."
            )
        if status == "verified" and (
            not contract["implementation_refs"] or not contract["test_refs"]
        ):
            raise ContractValidationError(
                f"{location}: un contrato sin evidencia no puede estar verificado."
            )
        seen_refs: set[tuple[str, str]] = set()
        for reference in contract["spec_refs"]:
            _validate_spec_ref(
                reference,
                macrofunction_id=contract_id,
                allowed_paths=allowed_paths,
                seen_refs=seen_refs,
            )

    required_activity_types = {"system", "manual", "external", "control"}
    if not required_activity_types.issubset(activity_types):
        raise ContractValidationError(
            "macrofunctions: deben distinguir sistema, manual, externo y control."
        )
    executive_text = json.dumps(macrofunctions, ensure_ascii=False)
    if re.search(r"\bxlsx\b", executive_text, re.IGNORECASE):
        raise ContractValidationError(
            "macrofunctions: XLSX no puede anunciarse como formato vigente."
        )
    return ids


def _has_path(adjacency: dict[str, set[str]], start: str, target: str) -> bool:
    pending = deque([start])
    visited: set[str] = set()
    while pending:
        current = pending.popleft()
        if current == target:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(adjacency.get(current, set()) - visited)
    return False


def _validate_relationships(data: dict[str, Any], node_ids: set[str]) -> None:
    relationships = data["relationships"]
    if not isinstance(relationships, list) or not relationships:
        raise ContractValidationError("relationships: se esperaba una lista no vacía.")
    relationship_ids: set[str] = set()
    adjacency: dict[str, set[str]] = {}
    for index, relationship in enumerate(relationships):
        location = f"relationships[{index}]"
        if not isinstance(relationship, dict):
            raise ContractValidationError(f"{location}: se esperaba un objeto.")
        _require_fields(relationship, REQUIRED_RELATIONSHIP_FIELDS, location)
        relationship_id = relationship["id"]
        _require_non_empty_string(relationship_id, f"{location}.id")
        if relationship_id in relationship_ids:
            raise ContractValidationError(
                f"{location}: ID duplicado: {relationship_id}."
            )
        relationship_ids.add(relationship_id)
        for endpoint in ("from", "to"):
            if relationship[endpoint] not in node_ids:
                raise ContractValidationError(
                    f"{location}.{endpoint}: nodo inexistente: {relationship[endpoint]}."
                )
        _require_non_empty_string(relationship["label"], f"{location}.label")
        if relationship["kind"] not in ALLOWED_RELATIONSHIP_KINDS:
            raise ContractValidationError(
                f"{location}.kind: tipo de relación desconocido."
            )
        adjacency.setdefault(relationship["from"], set()).add(relationship["to"])

    required_paths = (
        ("salesforce-csv", "upload-wolkvox-campaign"),
        ("organize-call-attempts", "document-manually"),
        ("select-documentation-batch", "document-with-bot"),
        ("document-manually", "confirm-salesforce-documentation"),
        ("document-with-bot", "confirm-salesforce-documentation"),
        ("confirm-salesforce-documentation", "review-results"),
    )
    for start, target in required_paths:
        if not _has_path(adjacency, start, target):
            raise ContractValidationError(
                f"relationships: falta el camino obligatorio {start} → {target}."
            )


def validate_contracts(
    data: dict[str, Any], *, published_output_path: Path | None = None
) -> None:
    if not isinstance(data, dict):
        raise ContractValidationError(
            "La raíz de la fuente contractual debe ser un objeto."
        )
    _require_fields(data, REQUIRED_ROOT_FIELDS, "raíz")
    if data["schema_version"] != 2:
        raise ContractValidationError("schema_version: solo se admite la versión 2.")
    for field in (
        "title",
        "subtitle",
        "revision",
        "technical_artifact",
        "candidate_output",
        "archify_output",
        "published_output",
    ):
        _require_non_empty_string(data[field], f"raíz.{field}")

    configured_technical = _safe_repository_path(
        data["technical_artifact"], "technical_artifact"
    )
    configured_candidate = _safe_repository_path(
        data["candidate_output"], "candidate_output"
    )
    configured_archify_output = _safe_repository_path(
        data["archify_output"], "archify_output"
    )
    configured_published_output = _safe_repository_path(
        data["published_output"], "published_output"
    )
    selected_output = (published_output_path or configured_published_output).resolve()
    expected_paths = {
        "technical_artifact": (configured_technical, TECHNICAL_GRAPH_PATH),
        "candidate_output": (configured_candidate, CANDIDATE_PATH),
        "archify_output": (configured_archify_output, ARCHIFY_OUTPUT_PATH),
        "published_output": (configured_published_output, PUBLISHED_OUTPUT_PATH),
    }
    for label, (configured, expected) in expected_paths.items():
        if configured != expected.resolve():
            raise ContractValidationError(f"{label} no coincide con la ruta protegida.")
    if not configured_technical.is_file():
        raise ContractValidationError("No existe el gráfico técnico protegido.")
    if sha256(configured_technical) != EXPECTED_TECHNICAL_GRAPH_SHA256:
        raise ContractValidationError(
            "El gráfico técnico protegido cambió respecto de la línea base."
        )
    if selected_output == configured_technical:
        raise ContractValidationError(
            "La salida no puede sobrescribir el gráfico técnico protegido."
        )

    allowed = data["allowed_spec_paths"]
    if not isinstance(allowed, list) or not allowed:
        raise ContractValidationError(
            "allowed_spec_paths: se esperaba una allowlist no vacía."
        )
    allowed_paths = set(allowed)
    if len(allowed_paths) != len(allowed):
        raise ContractValidationError("allowed_spec_paths: contiene rutas duplicadas.")
    for path in allowed_paths:
        _require_non_empty_string(path, "allowed_spec_paths")
        if "archive" in Path(path).parts:
            raise ContractValidationError(
                f"allowed_spec_paths: fuente archivada no permitida: {path}."
            )

    journey_ids = _validate_journeys(data)
    artifact_ids = _validate_artifacts(data, journey_ids)
    macrofunction_ids = _validate_macrofunctions(data, journey_ids, allowed_paths)
    if artifact_ids & macrofunction_ids:
        raise ContractValidationError(
            "Los IDs de artefactos y macrofunciones se repiten."
        )
    _validate_relationships(data, artifact_ids | macrofunction_ids)
    scan_sensitive_text(
        json.dumps(data, ensure_ascii=False), location="fuente contractual"
    )
