import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from closure_store import (
    CLOSE_QUEUE_OPERATION,
    closure_result_entry,
    load_close_queue_file,
    record_result,
    results_path_for,
    validate_close_queue,
)
from lead_closure import CLOSURE_REASONS, FINAL_OWNER, reason_contract, subqualification_options

VALID_CLOSE_LEAD = {"lead_id": "00Q000000000001AAA", "reason": "ilocalizable"}


def queue_payload(leads=None):
    return {
        "operation": CLOSE_QUEUE_OPERATION,
        "generated_at": "t",
        "leads": [VALID_CLOSE_LEAD] if leads is None else leads,
    }


class ClosureReasonContractTests(unittest.TestCase):
    def test_reason_contracts_contain_exact_approved_values(self):
        self.assertEqual(
            reason_contract("ilocalizable"),
            {
                "label": "Ilocalizable",
                "comentario": "Ilocalizable",
                "cualificacion": "Rechazo no argumentado",
                "subcualificacion": "Ilocalizable",
                "subcualificacion_alternativas": ("Permanece ilocalizable",),
            },
        )
        self.assertEqual(
            reason_contract("deja_de_interactuar"),
            {
                "label": "Deja de interactuar",
                "comentario": "Cliente deja de interactuar",
                "cualificacion": "Rechazo argumentado",
                "subcualificacion": "Interesado en precio o condición",
            },
        )

    def test_comentario_literals_have_no_trailing_space(self):
        for contract in CLOSURE_REASONS.values():
            self.assertEqual(contract["comentario"], contract["comentario"].strip())

    def test_subcualificacion_uses_o_not_y(self):
        self.assertIn("precio o condición", reason_contract("deja_de_interactuar")["subcualificacion"])
        self.assertNotIn("precio y condición", reason_contract("deja_de_interactuar")["subcualificacion"])

    def test_ilocalizable_subqualification_prefers_primary_then_fallback(self):
        self.assertEqual(
            subqualification_options(reason_contract("ilocalizable")),
            ("Ilocalizable", "Permanece ilocalizable"),
        )
        self.assertEqual(
            subqualification_options(reason_contract("deja_de_interactuar")),
            ("Interesado en precio o condición",),
        )

    def test_unknown_reason_rejected(self):
        with self.assertRaisesRegex(ValueError, "desconocido"):
            reason_contract("otro_motivo")

    def test_final_owner_is_ar_lead_cold(self):
        self.assertEqual(FINAL_OWNER, "AR_LEAD_COLD")


class ValidateCloseQueueTests(unittest.TestCase):
    def test_valid_queue_returns_leads(self):
        leads = validate_close_queue(queue_payload([VALID_CLOSE_LEAD]))
        self.assertEqual(leads, [VALID_CLOSE_LEAD])

    def test_rejects_missing_operation(self):
        with self.assertRaisesRegex(ValueError, "operation"):
            validate_close_queue({"leads": [VALID_CLOSE_LEAD]})

    def test_rejects_wrong_operation(self):
        with self.assertRaisesRegex(ValueError, "operation"):
            validate_close_queue({**queue_payload(), "operation": "document_attempts"})

    def test_rejects_empty_leads(self):
        with self.assertRaisesRegex(ValueError, "Leads"):
            validate_close_queue(queue_payload([]))

    def test_rejects_invalid_lead_id(self):
        bad = {"lead_id": "abc", "reason": "ilocalizable"}
        with self.assertRaisesRegex(ValueError, "Lead ID"):
            validate_close_queue(queue_payload([bad]))

    def test_rejects_unknown_reason(self):
        bad = {"lead_id": "00Q000000000001AAA", "reason": "cualquiera"}
        with self.assertRaisesRegex(ValueError, "motivo"):
            validate_close_queue(queue_payload([bad]))

    def test_rejects_duplicate_lead_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicado"):
            validate_close_queue(queue_payload([VALID_CLOSE_LEAD, dict(VALID_CLOSE_LEAD)]))

    def test_accepts_mixed_reasons_in_one_batch(self):
        second = {"lead_id": "00Q000000000002AAA", "reason": "deja_de_interactuar"}
        leads = validate_close_queue(queue_payload([VALID_CLOSE_LEAD, second]))
        self.assertEqual([lead["reason"] for lead in leads], ["ilocalizable", "deja_de_interactuar"])

    def test_rejects_unknown_country(self):
        with self.assertRaisesRegex(ValueError, "país"):
            validate_close_queue({**queue_payload(), "country": "peru"})


class LoadCloseQueueFileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.queue_directory = Path(self.temporary.name) / "queues"
        self.queue_directory.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def test_rejects_queue_outside_queues_directory(self):
        outside = Path(self.temporary.name) / "cierre.json"
        outside.write_text(json.dumps(queue_payload()), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "queues"):
            load_close_queue_file(str(outside), self.queue_directory)

    def test_reads_run_id(self):
        path = self.queue_directory / "cierre_run_x.json"
        path.write_text(json.dumps({**queue_payload(), "run_id": "run_x"}), encoding="utf-8")
        queue_file = load_close_queue_file(str(path), self.queue_directory)
        self.assertEqual(queue_file["run_id"], "run_x")
        self.assertEqual(len(queue_file["leads"]), 1)

    def test_reads_country_and_defaults_legacy_to_argentina(self):
        path = self.queue_directory / "cierre_run_x.json"
        path.write_text(
            json.dumps({**queue_payload(), "run_id": "run_x", "country": "colombia_mexico"}),
            encoding="utf-8",
        )
        self.assertEqual(load_close_queue_file(str(path), self.queue_directory)["country"], "colombia_mexico")

        legacy = self.queue_directory / "cierre_run_y.json"
        legacy.write_text(json.dumps(queue_payload()), encoding="utf-8")
        self.assertEqual(load_close_queue_file(str(legacy), self.queue_directory)["country"], "argentina")


class ClosureResultsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.results_path = Path(self.temporary.name) / "queues" / "cola_cierre_activa.resultado.json"
        self.results_path.parent.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def test_result_entry_carries_reason_and_run_id_without_field_content(self):
        entry = closure_result_entry(
            "00Q000000000001AAA",
            "cerrado_verificado",
            "ilocalizable",
            "run_x",
            elapsed_seconds=12.3456,
            stage_seconds={"save": 1.2345},
            verify_reloads=1,
        )
        self.assertEqual(entry["reason"], "ilocalizable")
        self.assertEqual(entry["run_id"], "run_x")
        self.assertEqual(entry["elapsed_seconds"], 12.3)
        self.assertEqual(entry["stage_seconds"], {"save": 1.2})
        self.assertEqual(entry["verify_reloads"], 1)
        self.assertNotIn("comentario", entry)
        self.assertNotIn("field_value", entry)

    def test_record_result_replaces_previous_entry_of_same_lead(self):
        record_result(
            self.results_path,
            closure_result_entry("00Q000000000001AAA", "conversion_pendiente", "ilocalizable", "run_1"),
        )
        record_result(
            self.results_path,
            closure_result_entry("00Q000000000001AAA", "cerrado_verificado", "ilocalizable", "run_2"),
        )
        results = json.loads(self.results_path.read_text(encoding="utf-8"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "cerrado_verificado")
        self.assertEqual(results[0]["run_id"], "run_2")

    def test_record_result_tolerates_corrupt_file(self):
        self.results_path.write_text("{roto", encoding="utf-8")
        record_result(
            self.results_path,
            closure_result_entry("00Q000000000001AAA", "error", "ilocalizable", "run_1"),
        )
        results = json.loads(self.results_path.read_text(encoding="utf-8"))
        self.assertEqual(len(results), 1)

    def test_results_path_mirrors_queue_name(self):
        self.assertEqual(
            results_path_for("queues/cierre_run_x.json").name,
            "cierre_run_x.resultado.json",
        )


if __name__ == "__main__":
    unittest.main()
