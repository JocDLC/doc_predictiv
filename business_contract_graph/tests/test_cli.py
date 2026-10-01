from __future__ import annotations

import subprocess
import sys
import unittest

from business_contract_graph.paths import REPOSITORY_ROOT


class BusinessContractCliTests(unittest.TestCase):
    def run_cli(self, command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "business_contract_graph", command],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_validate_generate_and_smoke_commands_succeed(self):
        for command in ("validate", "generate", "smoke"):
            with self.subTest(command=command):
                completed = self.run_cli(command)
                self.assertEqual(
                    completed.returncode, 0, completed.stdout + completed.stderr
                )

    def test_unknown_command_is_a_controlled_failure(self):
        completed = self.run_cli("unknown")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid choice", completed.stderr)


if __name__ == "__main__":
    unittest.main()
