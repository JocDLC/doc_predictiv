import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, call, patch

from selenium.common.exceptions import TimeoutException

import run_corrections
from snapshot_store import content_hash


def synthetic_correction(lead_id: str = "00Q000000000001AAA", new_value: str = "valor nuevo") -> dict:
    return {
        "lead_id": lead_id,
        "new_value": new_value,
        "base_hash": content_hash("valor base"),
    }


class RunCorrectionsTests(unittest.TestCase):
    def run_synthetic_main(self, corrections, *, field_reads, verification=(True, 11)):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        root = Path(temporary_directory.name)
        driver = Mock(attached_to_persistent_browser=False)
        logger = Mock()
        config = {
            "browser": "edge",
            "profile_directory": "synthetic-profile",
            "salesforce_url": "https://synthetic.example",
            "timeouts": {"page_load_seconds": 7},
            "log_directory": "logs",
            "screenshot_directory": "screenshots",
            "ui_output_directory": "ui_output",
        }

        stack = ExitStack()
        self.addCleanup(stack.close)
        mocks = {
            "record_result": stack.enter_context(patch.object(run_corrections, "record_result")),
            "record_snapshot": stack.enter_context(patch.object(run_corrections, "record_snapshot")),
            "prepare": stack.enter_context(patch.object(run_corrections, "prepare_other_information")),
            "save": stack.enter_context(patch.object(run_corrections, "save_edit_form")),
            "release": stack.enter_context(patch.object(run_corrections, "release_driver")),
            "capture": stack.enter_context(
                patch.object(run_corrections, "capture_failure", return_value=root / "synthetic.png")
            ),
        }
        stack.enter_context(patch.object(run_corrections, "ROOT", root))
        stack.enter_context(patch.object(run_corrections, "load_config", return_value=config))
        stack.enter_context(patch.object(run_corrections, "load_corrections", return_value=corrections))
        stack.enter_context(patch.object(run_corrections, "results_path_for", return_value=root / "results.json"))
        stack.enter_context(patch.object(run_corrections, "snapshot_path_for", return_value=root / "snapshots.json"))
        stack.enter_context(patch.object(run_corrections, "create_logger", return_value=logger))
        stack.enter_context(patch.object(run_corrections, "detect_browser", return_value=("edge", root / "edge.exe")))
        stack.enter_context(patch.object(run_corrections, "local_path", return_value=root / "profile"))
        stack.enter_context(patch.object(run_corrections, "create_driver", return_value=driver))
        stack.enter_context(patch.object(run_corrections, "prompt_for_manual_authentication"))
        stack.enter_context(patch.object(run_corrections, "wait_for_lightning_ready"))
        stack.enter_context(
            patch.object(run_corrections, "build_record_url", side_effect=lambda _url, lead_id, _object: lead_id)
        )
        stack.enter_context(patch.object(run_corrections, "find_other_information", side_effect=field_reads))
        stack.enter_context(patch.object(run_corrections, "verify_saved_value", return_value=verification))
        stack.enter_context(patch.object(run_corrections, "mask_lead_id", return_value="00Q***AAA"))

        result = run_corrections.main(["synthetic-corrections.json"])
        return result, driver, mocks, root

    def test_success_writes_verifies_snapshots_and_records_result(self):
        correction = synthetic_correction(new_value="valor nuevo")

        result, driver, mocks, root = self.run_synthetic_main(
            [correction],
            field_reads=["valor base", "valor nuevo"],
        )

        self.assertEqual(result, 0)
        mocks["prepare"].assert_called_once_with(driver, "valor nuevo", 7)
        mocks["save"].assert_called_once_with(driver, 7)
        mocks["record_snapshot"].assert_called_once_with(
            root / "snapshots.json",
            correction["lead_id"],
            "valor nuevo",
        )
        self.assertEqual(mocks["record_result"].call_args.args[1]["status"], "corregido")
        mocks["release"].assert_called_once_with(driver)

    def test_conflict_records_result_without_opening_editor_or_snapshot(self):
        correction = synthetic_correction()

        result, driver, mocks, _root = self.run_synthetic_main([correction], field_reads=["valor cambiado"])

        self.assertEqual(result, 0)
        mocks["prepare"].assert_not_called()
        mocks["save"].assert_not_called()
        mocks["record_snapshot"].assert_not_called()
        self.assertEqual(mocks["record_result"].call_args.args[1]["status"], "conflicto")
        mocks["release"].assert_called_once_with(driver)

    def test_read_failure_is_captured_recorded_and_releases_driver(self):
        result, driver, mocks, _root = self.run_synthetic_main(
            [synthetic_correction()],
            field_reads=[TimeoutException("synthetic timeout")],
        )

        self.assertEqual(result, 0)
        mocks["capture"].assert_called_once()
        mocks["prepare"].assert_not_called()
        self.assertEqual(mocks["record_result"].call_args.args[1]["status"], "error")
        mocks["release"].assert_called_once_with(driver)

    def test_failed_persistence_does_not_publish_snapshot(self):
        result, driver, mocks, _root = self.run_synthetic_main(
            [synthetic_correction()],
            field_reads=["valor base"],
            verification=(False, 4),
        )

        self.assertEqual(result, 0)
        mocks["prepare"].assert_called_once()
        mocks["save"].assert_called_once()
        mocks["capture"].assert_called_once()
        mocks["record_snapshot"].assert_not_called()
        self.assertEqual(mocks["record_result"].call_args.args[1]["status"], "error")
        mocks["release"].assert_called_once_with(driver)

    def test_mixed_batch_persists_each_result_incrementally(self):
        corrections = [
            synthetic_correction("00Q000000000001AAA", "nuevo uno"),
            synthetic_correction("00Q000000000002AAA", "nuevo dos"),
            synthetic_correction("00Q000000000003AAA", "nuevo tres"),
        ]

        result, driver, mocks, _root = self.run_synthetic_main(
            corrections,
            field_reads=["valor base", "nuevo uno", "valor cambiado", TimeoutException("synthetic timeout")],
        )

        self.assertEqual(result, 0)
        statuses = [record_call.args[1]["status"] for record_call in mocks["record_result"].call_args_list]
        lead_ids = [record_call.args[1]["lead_id"] for record_call in mocks["record_result"].call_args_list]
        self.assertEqual(statuses, ["corregido", "conflicto", "error"])
        self.assertEqual(lead_ids, [item["lead_id"] for item in corrections])
        self.assertEqual(mocks["record_result"].call_count, 3)
        mocks["release"].assert_has_calls([call(driver)])

    def test_invalid_queue_is_rejected_before_browser_creation(self):
        with (
            patch.object(run_corrections, "load_config", return_value={}),
            patch.object(run_corrections, "load_corrections", side_effect=ValueError("synthetic invalid")),
            patch.object(run_corrections, "create_driver") as create_driver,
        ):
            result = run_corrections.main(["invalid.json"])

        self.assertEqual(result, 2)
        create_driver.assert_not_called()

    def test_missing_path_returns_usage_error(self):
        with patch.object(run_corrections, "load_config") as load_config:
            result = run_corrections.main([])

        self.assertEqual(result, 2)
        load_config.assert_not_called()


if __name__ == "__main__":
    unittest.main()
