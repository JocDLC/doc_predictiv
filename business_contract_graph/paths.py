"""Rutas estables del gráfico de contratos de negocio."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPOSITORY_ROOT / "business_contract_graph"
SOURCE_PATH = PACKAGE_ROOT / "contracts.json"
TEMPLATE_PATH = PACKAGE_ROOT / "template.html"
SERVED_DIRECTORY = (
    REPOSITORY_ROOT / ".archify" / "architecture-documentador-20260928-090859"
)
OUTPUT_PATH = SERVED_DIRECTORY / "documentador-business-contracts.html"
TECHNICAL_GRAPH_PATH = SERVED_DIRECTORY / "documentador-architecture.html"
EXPECTED_TECHNICAL_GRAPH_SHA256 = (
    "1024d1e1b547451dee11f758e17fa56122e59647c645bd378ee43db3d10d7f5b"
)
