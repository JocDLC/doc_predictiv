"""Validación del esquema, trazabilidad y privacidad de los contratos."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .paths import (
    EXPECTED_TECHNICAL_GRAPH_SHA256,
    REPOSITORY_ROOT,
    TECHNICAL_GRAPH_PATH,
)

REQUIRED_ROOT_FIELDS = {
    "schema_version",
    "title",
    "subtitle",
    "revision",
    "technical_artifact",
    "output",
    "allowed_spec_paths",
    "macrofunctions",
    "relationships",
}
REQUIRED_CONTRACT_FIELDS = {
    "id",
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
LIST_FIELDS = {"inputs", "outputs", "rules", "failure_behavior", "spec_refs"}
ALLOWED_STATUSES = {"verified", "partial", "pending"}
ALLOWED_RELATIONSHIP_KINDS = {"primary", "duplicate", "recovery", "correction"}
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


def _validate_macrofunctions(data: dict[str, Any], allowed_paths: set[str]) -> set[str]:
    macrofunctions = data["macrofunctions"]
    if not isinstance(macrofunctions, list) or len(macrofunctions) != 9:
        raise ContractValidationError(
            "macrofunctions: deben existir exactamente nueve macrofunciones."
        )

    ids: set[str] = set()
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
        for field in ("name", "summary", "purpose"):
            _require_non_empty_string(contract[field], f"{location}.{field}")
        for field in LIST_FIELDS:
            if field == "spec_refs":
                if not isinstance(contract[field], list) or not contract[field]:
                    raise ContractValidationError(
                        f"{location}.spec_refs: falta una fuente OpenSpec."
                    )
            else:
                _require_non_empty_list(contract[field], f"{location}.{field}")
        for field in ("implementation_refs", "test_refs"):
            if not isinstance(contract[field], list):
                raise ContractValidationError(
                    f"{location}.{field}: se esperaba una lista."
                )
            for ref_index, reference in enumerate(contract[field]):
                _require_non_empty_string(reference, f"{location}.{field}[{ref_index}]")
                ref_path = _safe_repository_path(
                    reference.split(":", 1)[0], f"{location}.{field}"
                )
                if not ref_path.exists():
                    raise ContractValidationError(
                        f"{location}.{field}: evidencia inexistente: {reference}."
                    )
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
    return ids


def _validate_relationships(data: dict[str, Any], macrofunction_ids: set[str]) -> None:
    relationships = data["relationships"]
    if not isinstance(relationships, list) or not relationships:
        raise ContractValidationError("relationships: se esperaba una lista no vacía.")
    relationship_ids: set[str] = set()
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
            if relationship[endpoint] not in macrofunction_ids:
                raise ContractValidationError(
                    f"{location}.{endpoint}: macrofunción inexistente: {relationship[endpoint]}."
                )
        _require_non_empty_string(relationship["label"], f"{location}.label")
        if relationship["kind"] not in ALLOWED_RELATIONSHIP_KINDS:
            raise ContractValidationError(
                f"{location}.kind: tipo de relación desconocido."
            )


def validate_contracts(
    data: dict[str, Any], *, output_path: Path | None = None
) -> None:
    if not isinstance(data, dict):
        raise ContractValidationError(
            "La raíz de la fuente contractual debe ser un objeto."
        )
    _require_fields(data, REQUIRED_ROOT_FIELDS, "raíz")
    if data["schema_version"] != 1:
        raise ContractValidationError("schema_version: solo se admite la versión 1.")
    for field in ("title", "subtitle", "revision", "technical_artifact", "output"):
        _require_non_empty_string(data[field], f"raíz.{field}")

    configured_technical = _safe_repository_path(
        data["technical_artifact"], "technical_artifact"
    )
    configured_output = _safe_repository_path(data["output"], "output")
    selected_output = (output_path or configured_output).resolve()
    if configured_technical != TECHNICAL_GRAPH_PATH.resolve():
        raise ContractValidationError(
            "technical_artifact no identifica el gráfico técnico protegido."
        )
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

    macrofunction_ids = _validate_macrofunctions(data, allowed_paths)
    _validate_relationships(data, macrofunction_ids)
    scan_sensitive_text(
        json.dumps(data, ensure_ascii=False), location="fuente contractual"
    )
