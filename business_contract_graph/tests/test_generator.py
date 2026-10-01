from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from business_contract_graph.generator import generate_graph
from business_contract_graph.paths import SOURCE_PATH, TEMPLATE_PATH
from business_contract_graph.validator import load_contracts, sha256


class BusinessContractGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.data = load_contracts(SOURCE_PATH)

    def generate(self, directory: str) -> Path:
        output = Path(directory) / "business-contracts.html"
        return generate_graph(
            source_path=SOURCE_PATH,
            template_path=TEMPLATE_PATH,
            output_path=output,
        )

    def test_two_generations_have_the_same_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.generate(directory)
            first_hash = sha256(output)
            output = self.generate(directory)

            self.assertEqual(sha256(output), first_hash)

    def test_each_node_and_relationship_is_serialized_once(self):
        with tempfile.TemporaryDirectory() as directory:
            html = self.generate(directory).read_text(encoding="utf-8")

        for item in [*self.data["macrofunctions"], *self.data["relationships"]]:
            with self.subTest(item=item["id"]):
                self.assertEqual(html.count(f'"id":"{item["id"]}"'), 1)

    def test_output_is_self_contained_responsive_and_presentable(self):
        with tempfile.TemporaryDirectory() as directory:
            html = self.generate(directory).read_text(encoding="utf-8")

        for marker in (
            'id="theme-toggle"',
            'id="presentation-toggle"',
            "@media (max-width:900px)",
            "@media (max-width:620px)",
            "prefers-reduced-motion",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)
        self.assertNotIn("https://", html.lower())
        self.assertNotIn('src="//', html.lower())

    def test_technical_evidence_is_only_rendered_inside_details(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        evidence_details = template.index("<details><summary>Ver evidencia técnica")
        implementation = template.index("item.implementation_refs")
        test_refs = template.index("item.test_refs")

        self.assertLess(evidence_details, implementation)
        self.assertLess(evidence_details, test_refs)

    def test_references_do_not_escape_the_served_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            html = self.generate(directory).read_text(encoding="utf-8")

        self.assertNotIn("../../", html)
        self.assertIn('href="#${escapeHtml(anchor)}"', html)


if __name__ == "__main__":
    unittest.main()
