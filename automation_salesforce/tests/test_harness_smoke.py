import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import harness


class HarnessSmokeTests(unittest.TestCase):
    def test_required_layers_are_registered(self):
        self.assertEqual(
            set(harness.LAYER_MODULES),
            {"unit", "contract", "integration-local", "security-privacy", "browser-local"},
        )

    def test_production_file_list_includes_runner_and_tests(self):
        targets = harness.production_python_files()
        self.assertIn("harness.py", targets)
        self.assertIn("run_document_queue.py", targets)
        self.assertIn("tests", targets)

    def test_coverage_scope_accepts_all_productive_modules(self):
        report = '<coverage><packages><package><classes><class filename="critical.py"/></classes></package></packages></coverage>'
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "coverage.xml"
            report_path.write_text(report, encoding="utf-8")
            with patch("harness.coverage_python_files", return_value={"critical.py"}):
                harness.verify_coverage_scope(report_path)

    def test_coverage_scope_rejects_missing_critical_module(self):
        report = "<coverage><packages /></coverage>"
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "coverage.xml"
            report_path.write_text(report, encoding="utf-8")
            with (
                patch("harness.coverage_python_files", return_value={"ui_server.py"}),
                patch("harness.CRITICAL_COVERAGE_FILES", frozenset({"ui_server.py"})),
            ):
                with self.assertRaisesRegex(SystemExit, "Críticos omitidos: ui_server.py"):
                    harness.verify_coverage_scope(report_path)

    def test_command_failure_is_propagated(self):
        completed = subprocess.CompletedProcess([sys.executable], 7)
        with patch("harness.subprocess.run", return_value=completed):
            with self.assertRaises(SystemExit) as context:
                harness.run([sys.executable, "-c", "raise SystemExit(7)"])
        self.assertEqual(context.exception.code, 7)

    def test_unknown_programmatic_command_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "desconocido"):
            harness.run_named_command("salesforce")

    def test_external_executable_uses_platform_resolution(self):
        with patch("harness.shutil.which", return_value="C:/tools/openspec.CMD"):
            self.assertEqual(harness.resolve_executable("openspec"), "C:/tools/openspec.CMD")

    def test_missing_external_executable_fails_clearly(self):
        with patch("harness.shutil.which", return_value=None):
            with self.assertRaisesRegex(SystemExit, "No se encontró"):
                harness.resolve_executable("openspec")


if __name__ == "__main__":
    unittest.main()
