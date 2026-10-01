import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from snapshot_store import content_hash, record_snapshot, snapshot_path_for


class SnapshotStoreTests(unittest.TestCase):
    def test_records_latest_private_snapshot_for_each_lead(self):
        with TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            path = snapshot_path_for("queues/cola.json", output_directory)
            record_snapshot(path, "00Q000000000001AAA", "Valor inicial")
            record_snapshot(path, "00Q000000000001AAA", "Valor confirmado")
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(path.name, "cola.snapshots.json")
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["field_value"], "Valor confirmado")
        self.assertEqual(payload[0]["base_hash"], content_hash("Valor confirmado"))

    def test_snapshot_records_run_and_call_id_evidence(self):
        field = "1 INT Llamada 30/09/2026 13:41 1790793665.523415"
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "cola.snapshots.json"
            record_snapshot(path, "00Q000000000001AAA", field, run_id="run_x")

            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload[0]["run_id"], "run_x")
        self.assertEqual(payload[0]["call_ids"], ["1790793665.523415"])

    def test_snapshot_call_ids_can_be_overridden_with_verified_subset(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "cola.snapshots.json"
            record_snapshot(path, "00Q000000000001AAA", "", run_id="run_x", call_ids=[])

            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload[0]["call_ids"], [])


if __name__ == "__main__":
    unittest.main()
