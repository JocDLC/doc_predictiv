import inspect
import tempfile
import unittest
from pathlib import Path

import comment_writer
from comment_writer import (
    compose_attempts,
    compose_other_information,
    format_attempt,
    load_draft_body,
    replace_editor_value,
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

        self.assertEqual(source.count(".click()"), 1)
        self.assertIn("arguments[0].click()", source)
        self.assertIn("scrollIntoView", source)
        self.assertIn("inline-edit", source)
        self.assertIn("getBoundingClientRect", source)
        self.assertNotIn("SaveEdit", source)
        self.assertNotIn("save_record", source)
        self.assertNotIn("updateRecord", source)


if __name__ == "__main__":
    unittest.main()
