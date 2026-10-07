import unittest

from comment_reader import COMMENT_LABELS, OTHER_INFORMATION_LABELS
from country_fields import (
    ARGENTINA,
    COLOMBIA_MEXICO,
    COUNTRY_MODES,
    field_display,
    field_key,
    field_labels,
    normalize_country,
)


class CountryFieldContractTests(unittest.TestCase):
    def test_argentina_attempts_in_otra_informacion_closure_in_comentario(self):
        self.assertEqual(field_key(ARGENTINA, "attempts"), "otra_informacion")
        self.assertEqual(field_key(ARGENTINA, "closure"), "comentario")
        self.assertEqual(field_labels(ARGENTINA, "attempts"), OTHER_INFORMATION_LABELS)
        self.assertEqual(field_labels(ARGENTINA, "closure"), COMMENT_LABELS)

    def test_colombia_mexico_swaps_the_two_fields(self):
        self.assertEqual(field_key(COLOMBIA_MEXICO, "attempts"), "comentario")
        self.assertEqual(field_key(COLOMBIA_MEXICO, "closure"), "otra_informacion")
        self.assertEqual(field_labels(COLOMBIA_MEXICO, "attempts"), COMMENT_LABELS)
        self.assertEqual(field_labels(COLOMBIA_MEXICO, "closure"), OTHER_INFORMATION_LABELS)

    def test_display_names_are_visible_salesforce_labels(self):
        self.assertEqual(field_display(ARGENTINA, "attempts"), "Otra información")
        self.assertEqual(field_display(COLOMBIA_MEXICO, "attempts"), "Comentario")
        self.assertEqual(field_display(ARGENTINA, "closure"), "Comentario")
        self.assertEqual(field_display(COLOMBIA_MEXICO, "closure"), "Otra información")

    def test_missing_country_defaults_to_legacy_argentina(self):
        self.assertEqual(normalize_country(None), ARGENTINA)
        self.assertEqual(normalize_country(""), ARGENTINA)

    def test_unknown_country_rejected(self):
        with self.assertRaisesRegex(ValueError, "país"):
            normalize_country("peru")
        with self.assertRaisesRegex(ValueError, "país"):
            field_labels("mexico", "attempts")

    def test_country_accepts_case_variants(self):
        self.assertEqual(normalize_country(" Colombia_Mexico "), COLOMBIA_MEXICO)

    def test_only_two_modes_supported(self):
        self.assertEqual(set(COUNTRY_MODES), {ARGENTINA, COLOMBIA_MEXICO})


if __name__ == "__main__":
    unittest.main()
