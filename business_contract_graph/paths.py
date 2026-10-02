"""Rutas estables del workflow Archify de contratos de negocio."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPOSITORY_ROOT / "business_contract_graph"
SOURCE_PATH = PACKAGE_ROOT / "contracts.json"

SERVED_DIRECTORY = (
    REPOSITORY_ROOT / ".archify" / "architecture-documentador-20260928-090859"
)
WORKFLOW_DIRECTORY = (
    REPOSITORY_ROOT / ".archify" / "workflow-documentador-negocio-20261001-190644"
)
CANDIDATE_PATH = WORKFLOW_DIRECTORY / "candidate.json"
ARCHIFY_OUTPUT_PATH = WORKFLOW_DIRECTORY / "documentador-business-contracts.html"
PUBLISHED_OUTPUT_PATH = SERVED_DIRECTORY / "documentador-business-contracts.html"
FINALIZE_EVIDENCE_DIRECTORY = WORKFLOW_DIRECTORY / "review-salesforce"
FINALIZE_SUMMARY_PATH = (
    FINALIZE_EVIDENCE_DIRECTORY
    / "documentador-business-contracts.finalize-summary.json"
)
VISUAL_EVIDENCE_DIRECTORY = REPOSITORY_ROOT / ".archify" / "vis-salesforce"
TECHNICAL_GRAPH_PATH = SERVED_DIRECTORY / "documentador-architecture.html"

EXPECTED_TECHNICAL_GRAPH_SHA256 = (
    "1024d1e1b547451dee11f758e17fa56122e59647c645bd378ee43db3d10d7f5b"
)
