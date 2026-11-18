import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_browser as ab


class ParseEvalOutputTests(unittest.TestCase):
    def test_parses_wrapped_result(self):
        out = json.dumps({"result": "hola"})
        self.assertEqual(ab.parse_eval_output(out), "hola")

    def test_parses_nested_json_value(self):
        out = json.dumps({"data": {"value": {"a": 1}}})
        self.assertEqual(ab.parse_eval_output(out), {"a": 1})

    def test_last_json_line_on_noisy_stdout(self):
        out = "ruido del binario\n" + json.dumps({"result": 42})
        self.assertEqual(ab.parse_eval_output(out), 42)

    def test_empty_returns_none(self):
        self.assertIsNone(ab.parse_eval_output(""))
        self.assertIsNone(ab.parse_eval_output("   "))

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            ab.parse_eval_output("no json at all")


class CommandResolutionTests(unittest.TestCase):
    def test_unavailable_when_binary_missing(self):
        with patch.object(ab.shutil, "which", return_value=None):
            self.assertFalse(ab.command_available(""))
            with self.assertRaises(ab.AgentBrowserUnavailable):
                ab.resolve_command("")

    def test_available_with_configured_binary(self):
        with tempfile.NamedTemporaryFile(suffix=".cmd", delete=False) as tmp:
            path = tmp.name
        try:
            self.assertTrue(ab.command_available(path))
            self.assertEqual(ab.resolve_command(path), [path])
        finally:
            Path(path).unlink(missing_ok=True)

    def test_available_from_path(self):
        with patch.object(ab.shutil, "which", return_value=r"C:\bin\agent-browser.cmd"):
            self.assertTrue(ab.command_available(""))
            self.assertEqual(ab.resolve_command(""), [r"C:\bin\agent-browser.cmd"])


class ScriptContractTests(unittest.TestCase):
    def test_constants_cover_laboratory_flow(self):
        for name in (
            "JS_FIELD_READ",
            "JS_CLICK_EDIT",
            "JS_EDITOR_PRESENT",
            "JS_EDITOR_SET",
            "JS_EDITOR_VALUE",
            "JS_SAVE_CLICK",
            "JS_EDITOR_CLOSED",
            "JS_WA_BUTTON",
            "JS_WA_CLICK",
            "JS_WA_TOAST",
            "JS_WA_TOAST_CLOSE",
            "JS_PAGE_STATE",
            "JS_NAVIGATE",
            "JS_RELOAD",
            "LAB_JS_HELPERS",
        ):
            self.assertTrue(getattr(ab, name).strip(), name)

    def test_labels_literal_escapes_quotes(self):
        literal = ab._labels_literal(("Otra información", 'dijo "hola"'))
        parsed = json.loads(literal)
        self.assertEqual(["Otra información", "otra informacion", 'dijo "hola"'], parsed)
        self.assertIn("\\u00f3", literal)

    def test_normalize_js_escapes_are_single_backslash(self):
        # Regresión: en el raw string, "\\u0300" quedaba literal y la clase
        # de caracteres borraba 'f'/'u' ("información" -> "inormación").
        helpers = ab.LAB_JS_HELPERS
        self.assertIn("/[\\u0300-\\u036f]/g", helpers)
        self.assertIn("/\\s+/g", helpers)
        self.assertNotIn("\\\\u0300", helpers)
        self.assertNotIn("\\\\s", helpers)


if __name__ == "__main__":
    unittest.main()


class NodeConfirmationProbes(unittest.TestCase):
    """Sondas adversariales determinísticas sobre el JS de confirmación.

    Ejecutan ``LAB_WA_CONFIRM_HELPERS`` en Node (sin navegador): el
    clasificador y la agregación de evidencia son funciones puras testeables.
    """

    def _run(self, script: str) -> None:
        import shutil
        import subprocess
        import tempfile

        node = shutil.which("node")
        if not node:
            self.skipTest("node no disponible")
        body = (
            "const window = {};\n"
            "const document = {querySelectorAll: () => [], querySelector: () => null};\n"
            "class MutationObserver { constructor(cb){} observe(){} disconnect(){} }\n"
            "const performance = { now: () => 0 };\n" + ab.LAB_WA_CONFIRM_HELPERS + ab.LAB_JS_HELPERS + script
        )
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as file:
            file.write(body)
            path = file.name
        try:
            completed = subprocess.run([node, path], capture_output=True, text=True, timeout=20)
            if completed.returncode != 0:
                self.fail(f"sonda Node falló: {completed.stderr or completed.stdout}")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_error_toast_is_negative_not_confirmation(self):
        self._run(
            "if (waClassifyText(waNorm('Error: WhatsApp no enviado')) !== 'negative') throw 'A05';"
            "const ev = waEvidence([{norm: 'error whatsapp no enviado'}], []);"
            "if (ev.outcome !== 'no_confirmado' || ev.reason !== 'respuesta_negativa') throw 'A05b';"
        )

    def test_unrelated_status_is_not_confirmation(self):
        self._run(
            "if (waClassifyText(waNorm('WhatsApp status actualizado')) !== 'unrelated') throw 'A06';"
            "const ev = waEvidence([{norm: 'whatsapp status actualizado'}], []);"
            "if (ev.outcome !== 'no_confirmado' || ev.reason !== 'sin_senal') throw 'A06b';"
        )

    def test_stale_toast_is_not_confirmation(self):
        # Stale se marca por ELEMENTO en el observer (ev.stale), no por texto:
        # un nodo nuevo con texto idéntico al baseline SÍ confirma el envío.
        self._run(
            "const stale = 'message sent to whatsapp please follow the sending status';"
            "const ev = waEvidence([{norm: stale, stale: true}], [stale]);"
            "if (ev.outcome !== 'no_confirmado') throw 'A07';"
            "const fresh = waEvidence([{norm: stale, stale: false}], [stale]);"
            "if (fresh.outcome !== 'confirmado') throw 'A07b';"
        )

    def test_real_positive_toast_confirms(self):
        self._run(
            "const ev = waEvidence("
            "  [{norm: 'message sent to whatsapp please follow the sending status'}], []);"
            "if (ev.outcome !== 'confirmado' || ev.reason !== 'toast_positivo') throw 'A08';"
        )

    def test_contradictory_signals_are_indeterminate(self):
        self._run(
            "const ev = waEvidence("
            "  [{norm: 'message sent to whatsapp'}, {norm: 'error whatsapp no enviado'}], []);"
            "if (ev.outcome !== 'indeterminado') throw 'conflicto';"
        )

    def test_literal_history_preserved(self):
        # Una línea legítima que coincide con texto asistivo NO se filtra.
        self._run(
            "const labels = ['otra información', 'otra informacion'];"
            "const nl = String.fromCharCode(10);"
            "const value = textAfterLabel("
            "  ['Otra información', 'Modificar Otra información',"
            "   '1 INT Se envía WhatsApp 17/11/2026 09:00'].join(nl),"
            "  labels);"
            "if (!/modificar otra informacion/.test(normalize(value)))"
            "  throw 'A04: línea legítima borrada';"
        )
