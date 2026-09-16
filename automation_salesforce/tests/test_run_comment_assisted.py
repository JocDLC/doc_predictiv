import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from run_comment_assisted import (
    ROOT,
    confirm_preparation,
    print_preparation_summary,
    queue_directory_from_config,
)


class AssistedRunnerTests(unittest.TestCase):
    def test_summary_includes_only_metrics_not_comment_content(self):
        output = io.StringIO()

        with redirect_stdout(output):
            print_preparation_summary(
                lead_id="00Q000000000001AAA",
                previous_length=31,
                next_int=2,
                prepared_length=67,
            )

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "Lead ID: 00Q000000000001AAA",
                "Caracteres previos: 31",
                "Próximo INT: 2",
                "Caracteres preparados: 67",
            ],
        )
        self.assertNotIn("Envío WhatsApp", output.getvalue())

    def test_preparation_requires_the_explicit_local_confirmation(self):
        with patch("builtins.input", return_value="PREPARAR"):
            self.assertTrue(confirm_preparation())
        with patch("builtins.input", return_value="guardar"):
            self.assertFalse(confirm_preparation())

    def test_queue_directory_defaults_for_previous_local_configs(self):
        self.assertEqual(queue_directory_from_config({}), ROOT / "queues")
        self.assertEqual(
            queue_directory_from_config({"queue_directory": "local_queue"}),
            ROOT / "local_queue",
        )


if __name__ == "__main__":
    unittest.main()
