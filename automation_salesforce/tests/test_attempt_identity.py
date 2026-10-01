"""Identidad por llamada: extracción de call_id y partición de intentos."""

import unittest

from attempt_identity import documented_call_ids, partition_attempts


def attempt(call_id: str, result: str = "Buzón directo") -> dict:
    return {"result": result, "date": "30/09/2026", "time": "13:41", "call_id": call_id}


FIELD_WITH_TWO = (
    "1 INT Envío WhatsApp 08:31 22/9/2026\n"
    "2 INT Buzón directo 24/09/2026 13:46 1790275580.100812\n"
    "3 INT No_efectivo_No_contesta 25/09/2026 08:36 1790343380.158281"
)


class DocumentedCallIdsTests(unittest.TestCase):
    def test_extracts_only_call_ids_from_int_lines(self):
        ids = documented_call_ids(FIELD_WITH_TWO)

        self.assertEqual(ids, {"1790275580.100812", "1790343380.158281"})

    def test_ignores_lines_without_int_prefix(self):
        field = "Nota libre 9999999999.123456\nOtra línea 2026-09-30"

        self.assertEqual(documented_call_ids(field), set())

    def test_empty_field_yields_no_ids(self):
        self.assertEqual(documented_call_ids(""), set())
        self.assertEqual(documented_call_ids(None), set())

    def test_ignores_final_tokens_that_are_not_call_ids(self):
        field = "1 INT Llamada 30/09/2026 13:41 CELULAR"

        self.assertEqual(documented_call_ids(field), set())


class PartitionAttemptsTests(unittest.TestCase):
    def test_all_missing_when_field_has_other_ids(self):
        missing, present, unverifiable = partition_attempts(
            FIELD_WITH_TWO,
            [attempt("1790709220.356411"), attempt("1790793665.523415")],
        )

        self.assertEqual([a["call_id"] for a in missing], ["1790709220.356411", "1790793665.523415"])
        self.assertEqual(present, [])
        self.assertEqual(unverifiable, [])

    def test_all_present_produces_no_missing(self):
        missing, present, unverifiable = partition_attempts(
            FIELD_WITH_TWO,
            [attempt("1790275580.100812"), attempt("1790343380.158281")],
        )

        self.assertEqual(missing, [])
        self.assertEqual(set(present), {"1790275580.100812", "1790343380.158281"})
        self.assertEqual(unverifiable, [])

    def test_partial_documentation_splits_missing_and_present(self):
        missing, present, _ = partition_attempts(
            FIELD_WITH_TWO,
            [attempt("1790343380.158281"), attempt("1790793665.523415")],
        )

        self.assertEqual([a["call_id"] for a in missing], ["1790793665.523415"])
        self.assertEqual(present, ["1790343380.158281"])

    def test_attempt_without_call_id_on_empty_field_is_writable(self):
        missing, _, unverifiable = partition_attempts("", [attempt("")])

        self.assertEqual(len(missing), 1)
        self.assertEqual(unverifiable, [])

    def test_attempt_without_call_id_on_nonempty_field_is_unverifiable(self):
        missing, _, unverifiable = partition_attempts(FIELD_WITH_TWO, [attempt("")])

        self.assertEqual(missing, [])
        self.assertEqual(len(unverifiable), 1)

    def test_duplicate_call_id_in_input_is_processed_once(self):
        missing, present, _ = partition_attempts(
            FIELD_WITH_TWO,
            [attempt("1790709220.356411"), attempt("1790709220.356411"), attempt("1790275580.100812")],
        )

        self.assertEqual([a["call_id"] for a in missing], ["1790709220.356411"])
        self.assertEqual(present, ["1790275580.100812"])

    def test_call_ids_compare_as_exact_strings(self):
        missing, _, _ = partition_attempts(
            FIELD_WITH_TWO,
            [attempt("1790275580.1008120")],  # dígito extra: no es el mismo ID
        )

        self.assertEqual(len(missing), 1)


if __name__ == "__main__":
    unittest.main()
