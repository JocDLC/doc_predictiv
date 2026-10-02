from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from business_contract_graph.generator import build_candidate, generate_candidate
from business_contract_graph.paths import SOURCE_PATH
from business_contract_graph.validator import load_contracts, sha256


class BusinessContractGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.data = load_contracts(SOURCE_PATH)
        self.candidate = build_candidate(self.data)

    def test_candidate_is_native_showcase_workflow_v2(self):
        self.assertEqual(self.candidate["schema_version"], 2)
        self.assertEqual(self.candidate["diagram_type"], "workflow")
        self.assertEqual(self.candidate["meta"]["quality_profile"], "showcase")
        self.assertEqual(self.candidate["meta"]["animation"], "none")
        self.assertNotIn("visual_preset", self.candidate["meta"])

    def test_two_generations_have_the_same_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            generate_candidate(candidate_path=first)
            generate_candidate(candidate_path=second)
            self.assertEqual(sha256(first), sha256(second))

    def test_candidate_contains_every_source_node_once(self):
        candidate_ids = [node["id"] for node in self.candidate["nodes"]]
        source_ids = [
            *(item["id"] for item in self.data["artifacts"]),
            *(item["id"] for item in self.data["macrofunctions"]),
        ]
        self.assertCountEqual(candidate_ids, source_ids)
        self.assertEqual(len(candidate_ids), len(set(candidate_ids)))

    def test_each_macrofunction_has_one_native_contract_card(self):
        card_titles = [card["title"] for card in self.candidate["cards"]]
        expected_titles = [item["name"] for item in self.data["macrofunctions"]]
        self.assertEqual(card_titles, expected_titles)
        for card in self.candidate["cards"]:
            with self.subTest(card=card["title"]):
                self.assertEqual(len(card["items"]), 4)
                self.assertTrue(card["items"][0].startswith("Qué recibe:"))
                self.assertTrue(card["items"][1].startswith("Qué entrega:"))
                self.assertTrue(card["items"][2].startswith("Regla principal:"))
                self.assertTrue(card["items"][3].startswith("Si falla:"))

    def test_candidate_exposes_two_roots_and_manual_bot_paths(self):
        semantic = self.candidate["semanticChecks"]
        self.assertEqual(
            set(semantic["allowedRoots"]),
            {"salesforce-csv", "wolkvox-attempts-csv"},
        )
        required_paths = {
            (item["from"], item["to"]) for item in semantic["requiredPaths"]
        }
        self.assertIn(("wolkvox-attempts-csv", "document-manually"), required_paths)
        self.assertIn(("wolkvox-attempts-csv", "document-with-bot"), required_paths)

    def test_salesforce_documentation_is_a_visible_external_destination(self):
        node_by_id = {node["id"]: node for node in self.candidate["nodes"]}
        salesforce_documentation = node_by_id["confirm-salesforce-documentation"]
        self.assertEqual(salesforce_documentation["label"], "Documentar en Salesforce")
        self.assertEqual(salesforce_documentation["type"], "cloud")
        self.assertEqual(salesforce_documentation["tag"], "Externo")

    def test_candidate_uses_csv_and_does_not_advertise_xlsx(self):
        rendered = json.dumps(self.candidate, ensure_ascii=False)
        self.assertIn("CSV exportado de Salesforce", rendered)
        self.assertIn("CSV con intentos", rendered)
        self.assertIn("CSV descargado de Wolkvox con intentos de llamada", rendered)
        self.assertNotIn("XLSX", rendered.upper())

    def test_business_labels_hide_technical_identifiers(self):
        visible_text = json.dumps(
            {
                "lanes": self.candidate["lanes"],
                "nodes": [
                    {
                        "label": node["label"],
                        "sublabel": node.get("sublabel"),
                        "tag": node.get("tag"),
                    }
                    for node in self.candidate["nodes"]
                ],
                "edges": [edge.get("label") for edge in self.candidate["edges"]],
                "cards": self.candidate["cards"],
            },
            ensure_ascii=False,
        )
        for forbidden in (".py", "localhost", "127.0.0.1", "selenium", "DOM"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, visible_text)


if __name__ == "__main__":
    unittest.main()
