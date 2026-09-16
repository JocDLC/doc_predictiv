import inspect
import tempfile
import unittest
from pathlib import Path

import comment_writer
from comment_writer import (
    compose_other_information,
    load_draft_body,
    replace_editor_value,
    scroll_toward_other_information,
    validate_draft_body,
)


class FakeEditor:
    def __init__(self):
        self.cleared = False
        self.value = ""

    def clear(self):
        self.cleared = True

    def send_keys(self, value):
        self.value = value


class CommentWriterTests(unittest.TestCase):
    def test_compose_preserves_history_and_uses_next_int(self):
        prepared = compose_other_information(
            "1 INT Envío WhatsApp",
            2,
            "Llamada sin respuesta",
        )

        self.assertEqual(
            prepared,
            "1 INT Envío WhatsApp\n\n2 INT Llamada sin respuesta",
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

    def test_replace_editor_value_clears_then_types_the_prepared_comment(self):
        editor = FakeEditor()

        replace_editor_value(editor, "1 INT Envío WhatsApp")

        self.assertTrue(editor.cleared)
        self.assertEqual(editor.value, "1 INT Envío WhatsApp")

    def test_scroll_helper_reports_when_lightning_can_progress_to_the_field(self):
        class ScrollDriver:
            def execute_script(self, _script, _labels):
                return {"field_found": False, "progressed": True}

        self.assertTrue(scroll_toward_other_information(ScrollDriver()))

    def test_writer_clicks_only_the_field_edit_control(self):
        source = inspect.getsource(comment_writer)

        self.assertEqual(source.count(".click()"), 1)
        self.assertIn("edit_control.click()", source)
        self.assertIn("inline-edit", source)
        self.assertIn("getBoundingClientRect", source)
        self.assertNotIn("SaveEdit", source)
        self.assertNotIn("save_record", source)
        self.assertNotIn("updateRecord", source)


if __name__ == "__main__":
    unittest.main()
