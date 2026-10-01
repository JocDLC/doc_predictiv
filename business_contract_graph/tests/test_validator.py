from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from business_contract_graph.generator import generate_graph
from business_contract_graph.paths import (
    EXPECTED_TECHNICAL_GRAPH_SHA256,
    SOURCE_PATH,
    TECHNICAL_GRAPH_PATH,
    TEMPLATE_PATH,
)
from business_contract_graph.validator import (
    ContractValidationError,
    load_contracts,
    sha256,
    validate_contracts,
)

EXPECTED_MACROFUNCTIONS = [
    "Cargar base de Leads",
    "Validar y normalizar datos",
    "Preparar archivo para Wolkvox",
    "Leer Leads pendientes",
    "Seleccionar y confirmar un lote",
    "Preparar la documentación",
    "Guardar y verificar la documentación",
    "Consultar resultados y productividad",
    "Revisar y aplicar correcciones seguras",
]


class ContractValidatorTests(unittest.TestCase):
    def setUp(self):
        self.data = load_contracts(SOURCE_PATH)

    def test_approved_source_is_valid(self):
        validate_contracts(self.data)

    def test_technical_graph_still_matches_approved_baseline(self):
        self.assertEqual(sha256(TECHNICAL_GRAPH_PATH), EXPECTED_TECHNICAL_GRAPH_SHA256)

    def test_contract_snapshot_has_the_nine_approved_macrofunctions(self):
        names = [item["name"] for item in self.data["macrofunctions"]]

        self.assertEqual(names, EXPECTED_MACROFUNCTIONS)

    def test_every_contract_has_allowed_openspec_traceability(self):
        allowed = set(self.data["allowed_spec_paths"])

        for contract in self.data["macrofunctions"]:
            with self.subTest(contract=contract["id"]):
                self.assertTrue(contract["spec_refs"])
                self.assertTrue(
                    all(ref["path"] in allowed for ref in contract["spec_refs"])
                )

    def test_executive_layer_omits_technical_identifiers(self):
        forbidden = re.compile(
            r"(?:\.py\b|https?://|localhost|127\.0\.0\.1|\bport\b|selenium|playwright|\bdom\b)",
            re.IGNORECASE,
        )
        executive_fields = (
            "name",
            "summary",
            "purpose",
            "inputs",
            "outputs",
            "rules",
            "failure_behavior",
        )

        for contract in self.data["macrofunctions"]:
            text = json.dumps(
                {field: contract[field] for field in executive_fields},
                ensure_ascii=False,
            )
            with self.subTest(contract=contract["id"]):
                self.assertIsNone(forbidden.search(text), text)

    def test_contract_without_evidence_must_be_pending(self):
        invalid = copy.deepcopy(self.data)
        invalid["macrofunctions"][0]["verification_status"] = "verified"

        with self.assertRaisesRegex(
            ContractValidationError, "sin evidencia no puede estar verificado"
        ):
            validate_contracts(invalid)

    def test_missing_contract_field_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        del invalid["macrofunctions"][0]["inputs"]

        with self.assertRaisesRegex(
            ContractValidationError, "faltan campos obligatorios: inputs"
        ):
            validate_contracts(invalid)

    def test_duplicate_id_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["macrofunctions"][1]["id"] = invalid["macrofunctions"][0]["id"]

        with self.assertRaisesRegex(ContractValidationError, "ID duplicado"):
            validate_contracts(invalid)

    def test_broken_relationship_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["relationships"][0]["to"] = "missing"

        with self.assertRaisesRegex(
            ContractValidationError, "macrofunción inexistente"
        ):
            validate_contracts(invalid)

    def test_missing_openspec_reference_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["macrofunctions"][0]["spec_refs"][0]["requirement"] = "REQ inexistente"

        with self.assertRaisesRegex(
            ContractValidationError, "requisito inexistente o ambiguo"
        ):
            validate_contracts(invalid)

    def test_duplicate_openspec_reference_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["macrofunctions"][0]["spec_refs"].append(
            copy.deepcopy(invalid["macrofunctions"][0]["spec_refs"][0])
        )

        with self.assertRaisesRegex(ContractValidationError, "referencia duplicada"):
            validate_contracts(invalid)

    def test_archived_openspec_reference_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        archived = (
            "openspec/changes/archive/2026-09-16-ui-leads-ar-lead-qualif/"
            "specs/lista-leads-sin-gestion/spec.md"
        )
        invalid["allowed_spec_paths"].append(archived)
        invalid["macrofunctions"][0]["spec_refs"][0]["path"] = archived

        with self.assertRaisesRegex(ContractValidationError, "archivada"):
            validate_contracts(invalid)

    def test_sensitive_canary_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["macrofunctions"][0]["summary"] = "SENSITIVE-CANARY"

        with self.assertRaisesRegex(ContractValidationError, "Contenido sensible"):
            validate_contracts(invalid)

    def test_sensitive_data_patterns_are_rejected(self):
        prohibited_values = (
            "persona@example.com",
            "00Q000000000001AAA",
            "password=synthetic-value",
        )

        for value in prohibited_values:
            invalid = copy.deepcopy(self.data)
            invalid["macrofunctions"][0]["summary"] = value
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ContractValidationError, "Contenido sensible"),
            ):
                validate_contracts(invalid)

    def test_technical_graph_cannot_be_overwritten(self):
        with self.assertRaisesRegex(ContractValidationError, "no puede sobrescribir"):
            validate_contracts(self.data, output_path=TECHNICAL_GRAPH_PATH)

    def test_generation_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.html"
            second = Path(directory) / "second.html"
            generate_graph(
                source_path=SOURCE_PATH, template_path=TEMPLATE_PATH, output_path=first
            )
            generate_graph(
                source_path=SOURCE_PATH, template_path=TEMPLATE_PATH, output_path=second
            )

            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
