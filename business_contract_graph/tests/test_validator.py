from __future__ import annotations

import copy
import json
import re
import unittest

from business_contract_graph.paths import (
    EXPECTED_TECHNICAL_GRAPH_SHA256,
    SOURCE_PATH,
    TECHNICAL_GRAPH_PATH,
)
from business_contract_graph.validator import (
    ContractValidationError,
    load_contracts,
    sha256,
    validate_contracts,
)

EXPECTED_MACROFUNCTIONS = [
    "Preparar archivo para Wolkvox",
    "Cargar campaña en Wolkvox",
    "Organizar intentos de llamada",
    "Elegir información a documentar",
    "Documentar manualmente",
    "Documentar con el bot",
    "Confirmar en Salesforce",
    "Consultar resultados",
    "Aplicar una corrección segura",
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

    def test_exactly_two_business_journeys_are_declared(self):
        journey_ids = {item["id"] for item in self.data["journeys"]}
        self.assertEqual(
            journey_ids, {"salesforce-to-wolkvox", "wolkvox-to-salesforce"}
        )

    def test_every_declared_file_is_csv(self):
        self.assertTrue(self.data["artifacts"])
        self.assertEqual({item["format"] for item in self.data["artifacts"]}, {"CSV"})

    def test_manual_and_bot_routes_both_finish_in_salesforce_confirmation(self):
        edges = {(item["from"], item["to"]) for item in self.data["relationships"]}
        self.assertIn(("organize-call-attempts", "document-manually"), edges)
        self.assertNotIn(("select-documentation-batch", "document-manually"), edges)
        self.assertIn(("select-documentation-batch", "document-with-bot"), edges)
        self.assertIn(("document-manually", "confirm-salesforce-documentation"), edges)
        self.assertIn(("document-with-bot", "confirm-salesforce-documentation"), edges)

    def test_activity_types_distinguish_ownership(self):
        activity_types = {item["activity_type"] for item in self.data["macrofunctions"]}
        self.assertEqual(activity_types, {"system", "manual", "external", "control"})

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

    def test_xlsx_cannot_be_advertised_as_available(self):
        invalid = copy.deepcopy(self.data)
        invalid["macrofunctions"][0]["inputs"][0] = "Archivo XLSX"
        with self.assertRaisesRegex(ContractValidationError, "XLSX no puede"):
            validate_contracts(invalid)

    def test_non_csv_artifact_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["artifacts"][0]["format"] = "XLSX"
        with self.assertRaisesRegex(ContractValidationError, "debe ser CSV"):
            validate_contracts(invalid)

    def test_contract_without_evidence_must_not_be_verified(self):
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

    def test_unknown_activity_type_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["macrofunctions"][0]["activity_type"] = "magic"
        with self.assertRaisesRegex(ContractValidationError, "actividad desconocido"):
            validate_contracts(invalid)

    def test_broken_relationship_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["relationships"][0]["to"] = "missing"
        with self.assertRaisesRegex(ContractValidationError, "nodo inexistente"):
            validate_contracts(invalid)

    def test_missing_manual_route_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["relationships"] = [
            relation
            for relation in invalid["relationships"]
            if relation["id"] != "organize-to-manual"
        ]
        with self.assertRaisesRegex(ContractValidationError, "camino obligatorio"):
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

    def test_sensitive_content_is_rejected(self):
        prohibited_values = (
            "SENSITIVE-CANARY",
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
            validate_contracts(self.data, published_output_path=TECHNICAL_GRAPH_PATH)


if __name__ == "__main__":
    unittest.main()
