import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from local_report import write_unassigned_leads_report
from report_reader import VisibleLead


class LocalReportTests(unittest.TestCase):
    def test_writes_only_the_minimum_local_report_fields(self):
        lead = VisibleLead(
            lead_id="00Q000000000001AAA",
            created_at="2026-09-02",
            grid_position=4,
            status="SIN_GESTION",
        )
        generated_at = datetime(2026, 9, 9, 10, 30, 0)

        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = write_unassigned_leads_report(
                visible_row_count=29,
                leads=[lead],
                output_directory=Path(temporary_directory),
                generated_at=generated_at,
            )

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report_path.name, "leads_sin_gestion_20260909_103000.json")
        self.assertEqual(report["visible_row_count"], 29)
        self.assertEqual(
            report["leads"],
            [
                {
                    "lead_id": "00Q000000000001AAA",
                    "created_at": "2026-09-02",
                    "grid_position": 4,
                    "status": "SIN_GESTION",
                }
            ],
        )
        self.assertNotIn("comment", str(report).lower())


if __name__ == "__main__":
    unittest.main()
