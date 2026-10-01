import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from productivity_metrics import (
    metrics_path_for,
    round_elapsed_seconds,
    summarize_results,
    write_metrics,
)


class ProductivityMetricsTests(unittest.TestCase):
    def test_round_elapsed_seconds_uses_one_decimal(self):
        self.assertEqual(round_elapsed_seconds(12.34), 12.3)
        self.assertEqual(round_elapsed_seconds(12.35), 12.4)

    def test_summary_uses_only_saved_durations_and_full_cycle(self):
        results = [
            {"lead_id": "00Q000000000001AAA", "status": "guardado", "elapsed_seconds": 30.0},
            {"lead_id": "00Q000000000002AAA", "status": "guardado", "elapsed_seconds": 40.0},
            {"lead_id": "00Q000000000003AAA", "status": "error", "elapsed_seconds": 50.0},
        ]

        summary = summarize_results(results, cycle_elapsed_seconds=150.0)

        self.assertEqual(summary["sample_size"], 3)
        self.assertEqual(summary["saved"], 2)
        self.assertEqual(summary["duplicates"], 0)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["success_rate"], 66.7)
        self.assertEqual(
            summary["saved_elapsed_seconds"],
            {
                "mean": 35.0,
                "median": 35.0,
                "min": 30.0,
                "max": 40.0,
            },
        )
        self.assertEqual(summary["time_thresholds"], {"normal_max": 35.0, "intermediate_max": 42.0})
        self.assertEqual(summary["effective_leads_per_hour"], 48.0)
        self.assertNotIn("lead_id", json.dumps(summary))

    def test_summary_counts_duplicates_without_treating_them_as_saved(self):
        summary = summarize_results(
            [{"lead_id": "00Q000000000001AAA", "status": "duplicado", "elapsed_seconds": 4.0}],
            cycle_elapsed_seconds=4.0,
        )

        self.assertEqual(summary["duplicates"], 1)
        self.assertEqual(summary["saved"], 0)
        self.assertEqual(summary["effective_leads_per_hour"], None)

    def test_summary_separates_verification_buckets_from_new_saves(self):
        results = [
            {"lead_id": "00Q000000000001AAA", "status": "ya_documentado"},
            {"lead_id": "00Q000000000002AAA", "status": "parcial"},
            {"lead_id": "00Q000000000003AAA", "status": "revision"},
        ]

        summary = summarize_results(results, cycle_elapsed_seconds=10.0)

        self.assertEqual(summary["already_documented"], 1)
        self.assertEqual(summary["partial"], 1)
        self.assertEqual(summary["review"], 1)
        self.assertEqual(summary["saved"], 0)
        self.assertIsNone(summary["saved_elapsed_seconds"])

    def test_summary_without_saved_leads_has_no_duration_statistics(self):
        summary = summarize_results(
            [{"lead_id": "00Q000000000001AAA", "status": "error", "elapsed_seconds": 12.0}],
            cycle_elapsed_seconds=12.0,
        )

        self.assertEqual(summary["sample_size"], 1)
        self.assertEqual(summary["saved"], 0)
        self.assertEqual(summary["duplicates"], 0)
        self.assertEqual(summary["success_rate"], 0.0)
        self.assertIsNone(summary["saved_elapsed_seconds"])
        self.assertIsNone(summary["time_thresholds"])
        self.assertIsNone(summary["effective_leads_per_hour"])

    def test_summary_aggregates_stage_means_and_verify_reloads(self):
        results = [
            {
                "lead_id": "00Q000000000001AAA",
                "status": "guardado",
                "elapsed_seconds": 20.0,
                "stage_seconds": {"navigation": 4.0, "comment_check": 2.0},
                "verify_reloads": 0,
            },
            {
                "lead_id": "00Q000000000002AAA",
                "status": "guardado",
                "elapsed_seconds": 30.0,
                "stage_seconds": {"navigation": 6.0, "comment_check": 4.0},
                "verify_reloads": 1,
            },
            {
                "lead_id": "00Q000000000003AAA",
                "status": "duplicado",
                "elapsed_seconds": 5.0,
                "stage_seconds": {"navigation": 3.0, "comment_check": 2.0},
            },
        ]

        summary = summarize_results(results, cycle_elapsed_seconds=60.0)

        self.assertEqual(
            summary["stage_seconds_mean"],
            {
                "navigation": 4.3,
                "comment_check": 2.7,
            },
        )
        self.assertEqual(summary["verify_reloads"], 1)
        self.assertNotIn("lead_id", json.dumps(summary))

    def test_summary_without_stages_reports_no_stage_means(self):
        summary = summarize_results(
            [{"lead_id": "00Q000000000001AAA", "status": "guardado", "elapsed_seconds": 12.0}],
            cycle_elapsed_seconds=12.0,
        )

        self.assertIsNone(summary["stage_seconds_mean"])
        self.assertEqual(summary["verify_reloads"], 0)

    def test_metrics_file_is_next_to_results_and_contains_no_lead_ids(self):
        with TemporaryDirectory() as temporary_directory:
            results_path = Path(temporary_directory) / "cola.resultado.json"
            metrics_path = metrics_path_for(results_path)
            write_metrics(metrics_path, summarize_results([], cycle_elapsed_seconds=0.0))
            content = metrics_path.read_text(encoding="utf-8")

        self.assertEqual(metrics_path.name, "cola.metricas.json")
        self.assertNotIn("00Q", content)


if __name__ == "__main__":
    unittest.main()
