import unittest
from unittest.mock import patch

from run_leads_ui import read_report, scan_mode


class LeadsUiRunnerTests(unittest.TestCase):
    def test_default_mode_reads_only_the_current_visible_grid(self):
        mode, vertical_passes = scan_mode([])

        with patch("run_leads_ui.read_visible_unassigned_leads", return_value=(3, [])) as visible_reader, patch(
            "run_leads_ui.read_full_report"
        ) as full_reader:
            result = read_report(object(), 1, "Lead", {}, [], mode, vertical_passes)

        self.assertEqual(result, (3, []))
        visible_reader.assert_called_once()
        full_reader.assert_not_called()

    def test_complete_mode_uses_explicit_full_grid_scan(self):
        mode, vertical_passes = scan_mode(["--completo"])

        with patch("run_leads_ui.read_visible_unassigned_leads") as visible_reader, patch(
            "run_leads_ui.read_full_report", return_value=(9, [])
        ) as full_reader:
            result = read_report(object(), 1, "Lead", {}, [], mode, vertical_passes)

        self.assertEqual(result, (9, []))
        visible_reader.assert_not_called()
        full_reader.assert_called_once_with(
            unittest.mock.ANY,
            1,
            "Lead",
            {},
            [],
            max_vertical_passes=80,
        )


if __name__ == "__main__":
    unittest.main()
