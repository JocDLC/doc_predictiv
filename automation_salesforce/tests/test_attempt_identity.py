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

    def test_ignores_lines_without_the_call_id_column(self):
        field = "1 INT Llamada 30/09/2026 13:41\n2 INT CELULAR\n3 INT 2999999999"

        self.assertEqual(documented_call_ids(field), set())

    def test_call_ids_are_opaque_values_after_date_and_time(self):
        for call_id in (
            "178000001.000002.123456.01", "000001", "CALL-MX_A:b/7",
            "b8c26780-2997-4441-811a-349135660001", "CELULAR", "MX lote 0001",
        ):
            with self.subTest(call_id=call_id):
                for separator in (" ", "\t"):
                    field = separator.join(("4 INT", "Fallo de línea", "5/10/2026", "17:38", call_id))
                    self.assertEqual(documented_call_ids(field), {call_id})
                    missing, present, ambiguous = partition_attempts(field, [attempt(call_id)])
                    self.assertEqual((missing, present, ambiguous), ([], [call_id], []))

    def test_mexico_repeated_history_does_not_add_or_renumber_attempts(self):
        from comment_reader import next_attempt_number

        ids = ["178000001.000002.173816.49", "178000001.000002.130042.54"]
        field = "\n".join(
            f"{number} INT Fallo de línea 5/10/2026 17:38 {call_id}"
            for number, call_id in enumerate(ids + ids, start=4)
        )
        missing, present, ambiguous = partition_attempts(field, [attempt(value) for value in ids])
        self.assertEqual(missing, [])
        self.assertEqual(present, ids)
        self.assertEqual(ambiguous, [])
        self.assertEqual(next_attempt_number(field), 8)

    def test_opaque_ids_keep_case_zeros_and_full_boundaries(self):
        field = "1 INT Resultado 5/10/2026 17:38 MX-0001.a.b"
        requested = ["mx-0001.a.b", "MX-1.a.b", "0001.a.b", "MX-0001.a.b.0", "MX-0001.a.b"]
        missing, present, _ = partition_attempts(field, [attempt(value) for value in requested])
        self.assertEqual([item["call_id"] for item in missing], requested[:-1])
        self.assertEqual(present, requested[-1:])


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
