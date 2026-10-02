import inspect
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import run_document_queue
from run_document_queue import (
    ask_lead_action,
    parse_queue_args,
    print_lead_summary,
    record_result,
    result_entry,
    results_path_for,
    verify_saved_value,
    wait_for_manual_decision,
)


class RunDocumentQueueTests(unittest.TestCase):
    def test_summary_prints_metrics_without_comment_content(self):
        output = io.StringIO()
        with redirect_stdout(output):
            print_lead_summary("00Q000000000001AAA", 35, 4, 2, 120)

        text = output.getvalue()
        self.assertIn("00Q000000000001AAA", text)
        self.assertIn("35", text)
        self.assertIn("Próximo INT: 4", text)
        self.assertIn("Intentos nuevos: 2", text)
        self.assertIn("120", text)
        self.assertNotIn("No contesta", text)

    def test_ask_lead_action_maps_operator_responses(self):
        cases = {"preparar": "preparar", "s": "omitir", "q": "terminar"}
        for answer, expected in cases.items():
            with patch("builtins.input", return_value=answer):
                self.assertEqual(ask_lead_action(), expected)

    def test_ask_lead_action_reprompts_on_invalid_input(self):
        answers = iter(["x", "PREPARAR"])
        with patch("builtins.input", lambda _: next(answers)):
            self.assertEqual(ask_lead_action(), "preparar")

    def test_results_path_sits_next_to_the_queue_file(self):
        path = results_path_for("queues/cola_predictivo_20260917_101500.json")

        self.assertEqual(path.name, "cola_predictivo_20260917_101500.resultado.json")
        self.assertEqual(path.parent.name, "queues")

    def test_result_entry_records_only_operational_elapsed_time(self):
        entry = result_entry("00Q000000000001AAA", "guardado", 4, 2, 12.35)

        self.assertEqual(entry["elapsed_seconds"], 12.4)
        self.assertEqual(set(entry), {"lead_id", "status", "next_int", "attempts", "elapsed_seconds", "at"})
        self.assertNotIn("comment", entry)
        self.assertNotIn("phone", entry)

    def test_result_entry_records_stage_durations_without_content(self):
        entry = result_entry(
            "00Q000000000001AAA",
            "guardado",
            4,
            2,
            15.55,
            {"navigation": 4.24, "comment_check": 1.16},
            verify_reloads=1,
        )

        self.assertEqual(entry["elapsed_seconds"], 15.6)
        self.assertEqual(entry["stage_seconds"], {"navigation": 4.2, "comment_check": 1.2})
        self.assertEqual(entry["verify_reloads"], 1)
        self.assertNotIn("comment", entry)
        self.assertNotIn("field", entry)

    def test_record_result_writes_and_deduplicates_by_lead(self):
        with TemporaryDirectory() as temporary_directory:
            results_path = Path(temporary_directory) / "cola.resultado.json"

            record_result(results_path, result_entry("00Q000000000001AAA", "preparado", 4, 2))
            record_result(results_path, result_entry("00Q000000000002AAA", "omitido", 1, 1))
            record_result(results_path, result_entry("00Q000000000001AAA", "error", 4, 2))

            results = json.loads(results_path.read_text(encoding="utf-8"))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["status"], "error")
        self.assertEqual(results[1]["status"], "omitido")

    def test_wait_for_manual_decision_insists_while_editor_is_open(self):
        answers = iter(["", ""])
        editors = iter([object(), None])
        with (
            patch("builtins.input", lambda _: next(answers)),
            patch.object(run_document_queue, "find_editor_control", lambda _driver: next(editors)),
        ):
            wait_for_manual_decision(object())

    def test_parse_queue_args_detects_auto_flag_and_queue_path(self):
        self.assertEqual(parse_queue_args(["queues/cola.json"]), ("queues/cola.json", False, {}))
        self.assertEqual(parse_queue_args(["--auto", "queues/cola.json"]), ("queues/cola.json", True, {}))
        self.assertEqual(parse_queue_args([]), ("", False, {}))

    def test_parse_queue_args_accepts_run_id_and_output_overrides(self):
        queue_path, auto_mode, options = parse_queue_args(
            [
                "--auto",
                "--run-id",
                "run_20261001T000000Z_abc123",
                "--results",
                "queues/cola_activa.resultado.json",
                "--snapshots",
                "ui_output/cola_activa.snapshots.json",
                "--metrics",
                "queues/cola_activa.metricas.json",
                "queues/run_x.json",
            ]
        )

        self.assertEqual(queue_path, "queues/run_x.json")
        self.assertTrue(auto_mode)
        self.assertEqual(options["run_id"], "run_20261001T000000Z_abc123")
        self.assertEqual(options["results"], "queues/cola_activa.resultado.json")
        self.assertEqual(options["snapshots"], "ui_output/cola_activa.snapshots.json")
        self.assertEqual(options["metrics"], "queues/cola_activa.metricas.json")

    def test_result_entry_keeps_call_level_identity(self):
        entry = result_entry(
            "00Q000000000001AAA",
            "guardado",
            4,
            2,
            extra={
                "run_id": "run_x",
                "request_call_ids": ["1790709220.356411"],
                "documented_call_ids": ["1790709220.356411"],
                "added_call_ids": ["1790709220.356411"],
            },
        )

        self.assertEqual(entry["run_id"], "run_x")
        self.assertEqual(entry["documented_call_ids"], ["1790709220.356411"])
        self.assertNotIn("comment", entry)

    def test_verify_saved_value_reloads_and_compares_rstripped(self):
        class FakeDriver:
            def __init__(self):
                self.urls = []

            def get(self, url):
                self.urls.append(url)

        driver = FakeDriver()
        with (
            patch.object(run_document_queue, "wait_for_lightning_ready"),
            patch.object(run_document_queue, "find_other_information", return_value="1 INT A\n\n"),
        ):
            saved, persisted_length, reloads = verify_saved_value(driver, "https://sf/lead/1", "1 INT A", 5)
            self.assertTrue(saved)
            self.assertEqual(persisted_length, len("1 INT A\n\n"))
            self.assertEqual(reloads, 0)

        # La primera verificación lee la misma página: no recarga.
        self.assertEqual(driver.urls, [])

        driver.urls.clear()
        with (
            patch.object(run_document_queue, "wait_for_lightning_ready"),
            patch.object(run_document_queue, "find_other_information", return_value="1 INT B"),
            patch.object(run_document_queue.time, "sleep"),
        ):
            saved, persisted_length, reloads = verify_saved_value(driver, "https://sf/lead/1", "1 INT A", 5)
            self.assertFalse(saved)
            self.assertEqual(persisted_length, len("1 INT B"))
            self.assertEqual(reloads, 1)

        # Solo recarga una vez cuando la primera lectura no coincide.
        self.assertEqual(driver.urls, ["https://sf/lead/1"])

    def test_verify_saved_value_tolerates_display_whitespace(self):
        class FakeDriver:
            def get(self, _url):
                raise AssertionError("no debe recargar cuando la lectura ya coincide")

        # En modo lectura Salesforce muestra cada TAB como un espacio.
        with patch.object(run_document_queue, "find_other_information", return_value="2 INT Llamada 16/09/2026"):
            saved, _, reloads = verify_saved_value(FakeDriver(), "https://sf/lead/1", "2 INT\tLlamada\t16/09/2026", 5)

        self.assertTrue(saved)
        self.assertEqual(reloads, 0)

    def test_verify_saved_value_retries_until_value_propagates(self):
        class FakeDriver:
            def __init__(self):
                self.urls = []

            def get(self, url):
                self.urls.append(url)

        driver = FakeDriver()
        reads = iter(["valor anterior", "1 INT A"])
        with (
            patch.object(run_document_queue, "wait_for_lightning_ready"),
            patch.object(run_document_queue, "find_other_information", side_effect=lambda *_: next(reads)),
            patch.object(run_document_queue.time, "sleep"),
        ):
            saved, _, reloads = verify_saved_value(driver, "https://sf/lead/1", "1 INT A", 5, retries=2)

        self.assertTrue(saved)
        self.assertEqual(reloads, 1)
        self.assertEqual(driver.urls, ["https://sf/lead/1"])

    def test_runner_checks_duplicates_before_opening_the_editor(self):
        source = inspect.getsource(run_document_queue)

        self.assertLess(
            source.index("is_duplicate_lead(find_comment"), source.index("prepare_other_information(driver")
        )
        self.assertIn('"duplicado"', source)

    def test_runner_records_each_stage_of_the_flow(self):
        source = inspect.getsource(run_document_queue)

        for stage in (
            "navigation",
            "comment_check",
            "field_read",
            "editor",
            "save_settle",
            "verification",
            "snapshot",
        ):
            self.assertIn(f'"{stage}"', source)

    def test_runner_source_has_no_business_action_automation(self):
        source = inspect.getsource(run_document_queue)

        self.assertNotIn(".click(", source)
        self.assertNotIn("send_keys", source)
        self.assertNotIn("SaveEdit", source)
        self.assertNotIn("save_record", source)
        self.assertNotIn("updateRecord", source)


if __name__ == "__main__":
    unittest.main()
