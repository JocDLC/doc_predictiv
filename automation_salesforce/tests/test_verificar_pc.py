import unittest
from unittest.mock import patch

import verificar_pc


class PipSeleniumTests(unittest.TestCase):
    def setUp(self):
        verificar_pc.REPORT.clear()

    def test_no_exige_pip_si_selenium_importa(self):
        with patch.object(verificar_pc.subprocess, "run") as run_mock:
            verificar_pc.check_pip_and_selenium()
        for call in run_mock.call_args_list:
            comando = call.args[0] if call.args else call.kwargs.get("args", [])
            self.assertNotIn(
                "pip",
                comando,
                f"no debe invocar pip cuando selenium ya importa: {comando}",
            )
        fallos = [line for line in verificar_pc.REPORT if line.startswith("[FALLO")]
        self.assertEqual([], fallos)
