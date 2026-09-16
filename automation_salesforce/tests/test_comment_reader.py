import unittest

from comment_reader import (
    build_record_url,
    field_result_if_found,
    field_result_in_any_frame,
    find_other_information,
    next_attempt_number,
    other_information_structure_summary,
)


class FakeCommentDriver:
    def __init__(self, result, structure_result=None):
        self.result = result
        self.structure_result = structure_result
        self.scripts = []

    def execute_script(self, script, labels):
        self.scripts.append((script, labels))
        if "label_found" in script:
            return self.structure_result
        return self.result


class CommentReaderTests(unittest.TestCase):
    def test_next_attempt_number_returns_one_for_empty_or_unrelated_text(self):
        self.assertEqual(next_attempt_number(""), 1)
        self.assertEqual(next_attempt_number("Sin intentos registrados"), 1)

    def test_next_attempt_number_increments_single_attempt(self):
        self.assertEqual(next_attempt_number("1 INT Envío WhatsApp"), 2)

    def test_next_attempt_number_uses_maximum_from_multiple_attempts(self):
        comment = "1 INT Llamada\n2 INT WhatsApp\n3 INT Sin respuesta"

        self.assertEqual(next_attempt_number(comment), 4)

    def test_next_attempt_number_ignores_unrelated_text_and_uses_twelve(self):
        comment = "Texto libre\n12 INT Contacto sin éxito"

        self.assertEqual(next_attempt_number(comment), 13)

    def test_next_attempt_number_handles_repeated_and_unordered_values(self):
        comment = "3 INT Uno\n1 INT Dos\n3 INT Tres\n2 INT Cuatro"

        self.assertEqual(next_attempt_number(comment), 4)

    def test_find_other_information_returns_value_without_its_label(self):
        driver = FakeCommentDriver(
            {"found": True, "text": "Otra información\n1 INT Envío WhatsApp"}
        )

        comment = find_other_information(driver, timeout_seconds=1)

        self.assertEqual(comment, "1 INT Envío WhatsApp")
        self.assertEqual(len(driver.scripts), 1)

    def test_find_other_information_returns_empty_value_when_field_is_empty(self):
        driver = FakeCommentDriver({"found": True, "text": "Otra información"})

        self.assertEqual(find_other_information(driver, timeout_seconds=1), "")

    def test_field_result_wait_condition_rejects_missing_label(self):
        driver = FakeCommentDriver({"found": False, "text": ""})

        self.assertFalse(field_result_if_found(driver))

    def test_frame_reader_prefers_a_nonempty_visible_field(self):
        class FrameDriver(FakeCommentDriver):
            def __init__(self):
                super().__init__({})
                self.switch_to = self
                self.frame_index = -1

            def default_content(self):
                self.frame_index = -1

            def find_elements(self, *_):
                return [object()]

            def frame(self, _):
                self.frame_index = 0

            def execute_script(self, _script, _labels):
                return (
                    {"found": True, "text": ""}
                    if self.frame_index == -1
                    else {"found": True, "text": "1 INT Envío WhatsApp"}
                )

        result = field_result_in_any_frame(FrameDriver(), "safe script")

        self.assertEqual(result["text"], "1 INT Envío WhatsApp")

    def test_structure_summary_contains_only_dom_metadata(self):
        structure = {
            "label_found": True,
            "containers": [
                {
                    "tag": "records-record-layout-item",
                    "role": "",
                    "text_length": 31,
                    "descendants": [{"tag": "span", "text_length": 20}],
                }
            ],
        }
        driver = FakeCommentDriver({}, structure_result=structure)

        summary = other_information_structure_summary(driver)

        self.assertEqual(summary, structure)
        self.assertNotIn("Envío WhatsApp", str(summary))

    def test_build_record_url_uses_configured_object_and_validates_id(self):
        url = build_record_url(
            "https://example.invalid/",
            "a1B000000000001AAA",
            "Prospecto__c",
        )

        self.assertEqual(
            url,
            "https://example.invalid/lightning/r/Prospecto__c/a1B000000000001AAA/view",
        )
        with self.assertRaises(ValueError):
            build_record_url("https://example.invalid", "invalid id", "Lead")


if __name__ == "__main__":
    unittest.main()
