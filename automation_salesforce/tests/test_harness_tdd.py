import unittest
from unittest.mock import Mock, patch

import harness


def completed(returncode=0, stdout="", stderr=""):
    result = Mock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TddRedTests(unittest.TestCase):
    def test_red_falla_si_el_test_pasa(self):
        with patch("harness.subprocess.run", return_value=completed(0, stdout="OK\n")):
            with self.assertRaises(SystemExit):
                harness.run_tdd_red("tests.test_x")

    def test_red_ok_cuando_el_test_falla_por_asercion(self):
        fallo = completed(1, stderr="FAILED (failures=1)\n")
        with patch("harness.subprocess.run", return_value=fallo):
            harness.run_tdd_red("tests.test_x")

    def test_red_ok_con_aviso_cuando_falla_por_error(self):
        fallo = completed(1, stderr="FAILED (errors=1)\n")
        with patch("harness.subprocess.run", return_value=fallo):
            with patch("builtins.print") as mock_print:
                harness.run_tdd_red("tests.test_x")
        printed = " ".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("AVISO", printed)


class TddGreenTests(unittest.TestCase):
    def test_green_corta_antes_de_suite_si_el_test_falla(self):
        with patch("harness.subprocess.run", return_value=completed(1)) as mock_run:
            with self.assertRaises(SystemExit):
                harness.run_tdd_green("tests.test_x")
        self.assertEqual(mock_run.call_count, 1)

    def test_green_ok_corre_test_suite_y_lint_en_orden(self):
        with patch("harness.subprocess.run", return_value=completed(0)) as mock_run:
            harness.run_tdd_green("tests.test_x")
        comandos = [call.args[0] for call in mock_run.call_args_list]
        self.assertEqual(len(comandos), 3)
        self.assertIn("tests.test_x", comandos[0])
        self.assertEqual(comandos[1][3:], ["discover", "-s", "tests", "-v"])
        self.assertEqual(comandos[2][3:], ["check", "."])


class ParseArgsTddTests(unittest.TestCase):
    def test_parse_args_acepta_tdd_red_con_test_id(self):
        args = harness.parse_args(["tdd-red", "tests.test_x"])
        self.assertEqual(args.command, "tdd-red")
        self.assertEqual(args.test_id, "tests.test_x")

    def test_parse_args_sigue_aceptando_test(self):
        args = harness.parse_args(["test"])
        self.assertEqual(args.command, "test")
        self.assertIsNone(args.test_id)

    def test_parse_args_rechaza_tdd_red_sin_test_id(self):
        with self.assertRaises(SystemExit):
            harness.parse_args(["tdd-red"])

    def test_parse_args_rechaza_tdd_green_sin_test_id(self):
        with self.assertRaises(SystemExit):
            harness.parse_args(["tdd-green"])


if __name__ == "__main__":
    unittest.main()
