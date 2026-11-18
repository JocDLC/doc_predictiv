import json
import tempfile
import unittest
from pathlib import Path

from laboratory_metrics import (
    percentile_nearest_rank,
    summarize_laboratory_results,
    write_metrics,
)


class MetricsTests(unittest.TestCase):
    def test_summarize_groups_by_engine(self):
        results = [
            {"engine": "selenium", "status": "documentado_enviado", "elapsed_seconds": 1.5},
            {"engine": "selenium", "status": "error", "elapsed_seconds": 0.5},
            {
                "engine": "agent_browser",
                "status": "apto",
                "elapsed_seconds": 2.0,
                "stage_seconds": {"eligibility_read": 0.4},
                "intervencion_manual": True,
            },
        ]
        summary = summarize_laboratory_results(results, cycle_elapsed_seconds=30.0)
        self.assertEqual(summary["total_leads"], 3)
        sel = summary["engines"]["selenium"]
        self.assertEqual(sel["sample_size"], 2)
        self.assertEqual(sel["statuses"]["documentado_enviado"], 1)
        self.assertEqual(sel["statuses"]["error"], 1)
        ab = summary["engines"]["agent_browser"]
        self.assertEqual(ab["manual_interventions"], 1)
        self.assertEqual(ab["stage_seconds"]["eligibility_read"]["median"], 0.4)
        self.assertIn("effective_leads_per_hour", summary)

    def test_empty_results(self):
        summary = summarize_laboratory_results([])
        self.assertEqual(summary["engines"], {})
        self.assertNotIn("effective_leads_per_hour", summary)

    def test_percentile_nearest_rank(self):
        values = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(percentile_nearest_rank(values, 50), 2.0)
        self.assertEqual(percentile_nearest_rank(values, 95), 4.0)
        self.assertIsNone(percentile_nearest_rank([], 50))

    def test_write_metrics_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "metrics.json"
            write_metrics(path, {"a": 1})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 1})


if __name__ == "__main__":
    unittest.main()


class PairedMetricsTests(unittest.TestCase):
    def test_paired_block_counts_agreements(self):
        results = [
            {"lead_id": "L1", "engine": "selenium", "status": "apto", "elapsed_seconds": 10.0},
            {"lead_id": "L1", "engine": "agent_browser", "status": "apto", "elapsed_seconds": 8.0},
            {"lead_id": "L2", "engine": "selenium", "status": "bloqueado", "elapsed_seconds": 3.0},
            {"lead_id": "L2", "engine": "agent_browser", "status": "apto", "elapsed_seconds": 4.0},
        ]
        summary = summarize_laboratory_results(results)
        self.assertEqual(summary["unique_leads"], 2)
        paired = summary["paired"]
        self.assertEqual(paired["pairs"], 2)
        self.assertEqual(paired["agreements"], 1)
        self.assertEqual(len(paired["disagreements"]), 1)
        self.assertEqual(paired["both_apto_elapsed_median"]["selenium"], 10.0)
        self.assertEqual(paired["both_apto_elapsed_median"]["agent_browser"], 8.0)
