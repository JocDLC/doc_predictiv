import inspect
import tempfile
import unittest
from pathlib import Path

import comment_writer
from selenium.common.exceptions import StaleElementReferenceException

from comment_writer import (
    compose_attempts,
    compose_other_information,
    format_attempt,
    load_draft_body,
    prepare_other_information,
    replace_editor_value,
    save_edit_form,
    scroll_toward_other_information,
    validate_draft_body,
    verify_editor_value,
)


class FakeEditor:
    def __init__(self, value=""):
        self.value = value

    def get_attribute(self, name):
        return self.value if name == "value" else None


class FakeDriver:
    def __init__(self):
        self.scripts = []

    def execute_script(self, script, *args):
        self.scripts.append((script, args))
        if len(args) == 2 and hasattr(args[0], "value"):
            args[0].value = args[1]


class CommentWriterTests(unittest.TestCase):
    def test_compose_preserves_history_and_uses_next_int(self):
        prepared = compose_other_information(
            "1 INT Envío WhatsApp",
            2,
            "Llamada sin respuesta",
        )

        self.assertEqual(
            prepared,
            "1 INT Envío WhatsApp\n2 INT Llamada sin respuesta",
        )

    def test_compose_starts_with_first_int_when_history_is_empty(self):
        self.assertEqual(
            compose_other_information("", 1, "Envío WhatsApp"),
            "1 INT Envío WhatsApp",
        )

    def test_draft_validation_rejects_empty_and_numbered_bodies(self):
        with self.assertRaises(ValueError):
            validate_draft_body("   ")
        with self.assertRaises(ValueError):
            validate_draft_body("2 INT Llamada")

    def test_draft_validation_collapses_whitespace_without_exposing_content(self):
        self.assertEqual(
            validate_draft_body("  Llamada\n sin respuesta  "),
            "Llamada sin respuesta",
        )

    def test_load_draft_accepts_only_a_file_inside_queues(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            queues = Path(temporary_directory) / "queues"
            queues.mkdir()
            draft = queues / "borrador.txt"
            draft.write_text("Envío WhatsApp", encoding="utf-8")

            self.assertEqual(load_draft_body(str(draft), queues), "Envío WhatsApp")
            with self.assertRaises(ValueError):
                load_draft_body(str(draft), queues / "other")

    def test_format_attempt_builds_tab_separated_line(self):
        line = format_attempt(
            4,
            {"result": "No contesta", "date": "15/09/2026", "time": "10:30", "call_id": "12345"},
        )

        self.assertEqual(line, "4 INT\tNo contesta\t15/09/2026\t10:30\t12345")

    def test_format_attempt_rejects_empty_result(self):
        with self.assertRaises(ValueError):
            format_attempt(1, {"result": " ", "date": "d", "time": "t", "call_id": "c"})

    def test_compose_attempts_numbers_consecutively_from_salesforce(self):
        attempts = [
            {"result": "No contesta", "date": "15/09/2026", "time": "10:30", "call_id": "12345"},
            {"result": "Ocupado", "date": "15/09/2026", "time": "11:02", "call_id": "12346"},
        ]

        prepared = compose_attempts("1 INT A\n2 INT B\n3 INT C", 4, attempts)

        self.assertEqual(
            prepared,
            "1 INT A\n2 INT B\n3 INT C\n"
            "4 INT\tNo contesta\t15/09/2026\t10:30\t12345\n"
            "5 INT\tOcupado\t15/09/2026\t11:02\t12346",
        )

    def test_compose_attempts_appends_on_next_line_after_trailing_newlines(self):
        attempts = [
            {"result": "No contesta", "date": "15/09/2026", "time": "10:30", "call_id": "12345"},
        ]

        prepared = compose_attempts("1 INT A\n\n", 2, attempts)

        self.assertEqual(
            prepared,
            "1 INT A\n2 INT\tNo contesta\t15/09/2026\t10:30\t12345",
        )

    def test_compose_attempts_without_history_starts_at_one(self):
        attempts = [
            {"result": "No contesta", "date": "15/09/2026", "time": "10:30", "call_id": "12345"},
        ]

        self.assertEqual(
            compose_attempts("", 1, attempts),
            "1 INT\tNo contesta\t15/09/2026\t10:30\t12345",
        )

    def test_compose_attempts_validates_inputs(self):
        attempts = [{"result": "X", "date": "d", "time": "t", "call_id": "c"}]
        with self.assertRaises(ValueError):
            compose_attempts("", 0, attempts)
        with self.assertRaises(ValueError):
            compose_attempts("", 1, [])

    def test_replace_editor_value_writes_via_script_preserving_tabs(self):
        driver = FakeDriver()
        editor = FakeEditor()

        replace_editor_value(driver, editor, "1 INT\tNo contesta")

        script, _ = driver.scripts[0]
        self.assertIn(".value", script)
        self.assertNotIn("send_keys", script)
        self.assertEqual(editor.value, "1 INT\tNo contesta")

    def test_verify_editor_value_compares_the_control_content(self):
        self.assertTrue(verify_editor_value(FakeEditor("abc"), "abc"))
        self.assertFalse(verify_editor_value(FakeEditor("abc"), "abd"))
        self.assertFalse(verify_editor_value(FakeEditor("abc"), "abc "))

    def test_scroll_helper_reports_when_lightning_can_progress_to_the_field(self):
        class ScrollDriver:
            def execute_script(self, _script, _labels):
                return {"field_found": False, "progressed": True}

        self.assertTrue(scroll_toward_other_information(ScrollDriver()))

    def test_save_button_script_targets_only_form_save(self):
        source = inspect.getsource(comment_writer)

        self.assertIn("SAVE_BUTTON_SCRIPT", source)
        self.assertIn("save_edit_form", source)
        self.assertIn("'guardar'", source)
        self.assertIn("'save'", source)
        self.assertNotIn("save_record", source)
        self.assertNotIn("updateRecord", source)

    def test_writer_clicks_only_the_field_edit_control(self):
        source = inspect.getsource(comment_writer)

        self.assertIn(".click()", source)
        self.assertIn("scrollIntoView", source)
        self.assertIn("inline-edit", source)
        self.assertIn("getBoundingClientRect", source)
        self.assertNotIn("SaveEdit", source)
        self.assertNotIn("save_record", source)
        self.assertNotIn("updateRecord", source)


class StaleMarshalDriver:
    """Edge 158: todo WebElement devuelto por JS muere entre llamadas.

    Las evaluaciones atómicas (labels/texto, sin elementos) funcionan y el
    driver solo expone iframes para probar la tolerancia del documento
    principal frente a un marshal que sale stale.
    """

    def __init__(self):
        self.switch_to = self
        self.editor_value = ""
        self.saved = False
        self.scripts = []
        self.cdp_calls = []
        self._in_frame = False
        self._focused = False

    def execute_cdp_cmd(self, command, params):
        """Teclado confiable: insertText reemplaza la selección del editor
        enfocado; el Tab confirma el campo (el borrador lo toma)."""
        self.cdp_calls.append((command, params))
        if command == "Input.insertText" and self._focused:
            self.editor_value = params["text"]

    def default_content(self):
        self._in_frame = False

    def frame(self, _frame):
        self._in_frame = True

    def find_elements(self, *_args, **_kwargs):
        return []

    def execute_script(self, script, *args):
        self.scripts.append((script, args))
        for arg in args:
            if isinstance(arg, FakeEditor):
                raise StaleElementReferenceException("stale al usar el handle")
        if script is comment_writer.CLICK_EDIT_CONTROL_ATOMIC_SCRIPT:
            return "clicked"
        if script is comment_writer.CLICK_SAVE_BUTTON_ATOMIC_SCRIPT:
            self.saved = True
            return "clicked"
        if script is comment_writer.EDITOR_PRESENT_ATOMIC_SCRIPT:
            return "not_found" if self.saved else "found"
        if script is comment_writer.SET_EDITOR_VALUE_ATOMIC_SCRIPT:
            self.editor_value = args[1]
            return self.editor_value
        if script is comment_writer.FOCUS_EDITOR_ATOMIC_SCRIPT:
            self._focused = True
            return "focused"
        if script is comment_writer.READ_EDITOR_VALUE_ATOMIC_SCRIPT:
            return self.editor_value
        return None


class AtomicEditorTests(unittest.TestCase):
    """La escritura de campos no puede exportar handles: en Edge 158 mueren
    entre find y click/set. Todo el recorrido usa scripts atómicos."""

    def test_prepare_writes_without_exporting_element_handles(self):
        driver = StaleMarshalDriver()

        prepare_other_information(driver, "1 INT prueba", 10)

        self.assertEqual(driver.editor_value, "1 INT prueba")

    def test_prepare_rejects_editor_that_keeps_wrong_value(self):
        driver = StaleMarshalDriver()
        driver.editor_value = "valor fijo"
        original = driver.execute_script

        def fixed_value(script, *args):
            result = original(script, *args)
            if script is comment_writer.READ_EDITOR_VALUE_ATOMIC_SCRIPT:
                driver.editor_value = "valor fijo"
                return "valor fijo"
            return result

        driver.execute_script = fixed_value
        with self.assertRaises(ValueError):
            prepare_other_information(driver, "1 INT prueba", 10)

        attempts = [c for c, _p in driver.cdp_calls if c == "Input.insertText"]
        self.assertEqual(len(attempts), 2)

    def test_prepare_types_with_trusted_keyboard_and_confirms_with_tab(self):
        """Lightning solo toma en el borrador lo tipeado con eventos de
        usuario confiables y confirmado con Tab: sin eso Guardar manda {Id}."""
        driver = StaleMarshalDriver()

        prepare_other_information(driver, "1 INT prueba", 10)

        commands = [c for c, _p in driver.cdp_calls]
        self.assertEqual(commands, ["Input.insertText", "Input.dispatchKeyEvent", "Input.dispatchKeyEvent"])
        self.assertEqual(driver.cdp_calls[0][1], {"text": "1 INT prueba"})
        self.assertEqual([p["type"] for _c, p in driver.cdp_calls[1:]], ["keyDown", "keyUp"])
        self.assertTrue(all(p["key"] == "Tab" for _c, p in driver.cdp_calls[1:]))
        # El foco se toma en la misma evaluación que ubica el editor (sin handles).
        focus_index = next(
            i for i, (s, _a) in enumerate(driver.scripts) if s is comment_writer.FOCUS_EDITOR_ATOMIC_SCRIPT
        )
        self.assertTrue(focus_index >= 0)
        self.assertNotIn(comment_writer.SET_EDITOR_VALUE_ATOMIC_SCRIPT, [s for s, _a in driver.scripts])

    def test_type_editor_value_reports_missing_editor_without_typing(self):
        driver = StaleMarshalDriver()
        original = driver.execute_script

        def no_editor(script, *args):
            if script is comment_writer.FOCUS_EDITOR_ATOMIC_SCRIPT:
                return "not_found"
            return original(script, *args)

        driver.execute_script = no_editor
        self.assertEqual(comment_writer.type_editor_value(driver, ("comentario",), "x"), "not_found")
        self.assertEqual(driver.cdp_calls, [])

    def test_save_clicks_and_waits_atomically_without_handles(self):
        driver = StaleMarshalDriver()

        save_edit_form(driver, 10, settle_seconds=0)

        self.assertTrue(driver.saved)
        self.assertTrue(all(not isinstance(arg, FakeEditor) for _script, args in driver.scripts for arg in args))

    def test_writer_keeps_atomic_contract_in_source(self):
        source = inspect.getsource(comment_writer)

        for name in (
            "CLICK_EDIT_CONTROL_ATOMIC_SCRIPT",
            "SET_EDITOR_VALUE_ATOMIC_SCRIPT",
            "READ_EDITOR_VALUE_ATOMIC_SCRIPT",
            "EDITOR_PRESENT_ATOMIC_SCRIPT",
            "CLICK_SAVE_BUTTON_ATOMIC_SCRIPT",
        ):
            self.assertIn(name, source)
        self.assertNotIn("SaveEdit", source)
        self.assertNotIn("save_record", source)
        self.assertNotIn("updateRecord", source)


if __name__ == "__main__":
    unittest.main()
