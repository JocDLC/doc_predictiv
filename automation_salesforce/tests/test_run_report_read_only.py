import io
import unittest
from contextlib import redirect_stdout

from report_reader import VisibleLead
from run_report_read_only import print_report_summary


class ReportSummaryTests(unittest.TestCase):
    def test_summary_prints_lead_ids_only_to_local_console(self):
        lead_id = "00QbD00000t6sipUAA"
        output = io.StringIO()

        with redirect_stdout(output):
            print_report_summary(
                3,
                [
                    VisibleLead(lead_id=lead_id, created_at=""),
                    VisibleLead(lead_id="", created_at=""),
                ],
            )

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "Filas visibles: 3",
                "Leads con AR_LEAD_QUALIF: 1",
                "Lead IDs:",
                lead_id,
            ],
        )
        self.assertIn(lead_id, output.getvalue())


if __name__ == "__main__":
    unittest.main()
