import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from queue_loader import load_queue

VALID_LEAD = {
    "lead_id": "00Q000000000001AAA",
    "attempts": [
        {"result": "No contesta", "date": "15/09/2026", "time": "10:30", "call_id": "12345"},
        {"result": "Cliente contesta", "date": "15/09/2026", "time": "11:02", "call_id": "12346"},
    ],
}


class QueueLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.queue_directory = Path(self.temporary.name) / "queues"
        self.queue_directory.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def write_queue(self, payload: object, name: str = "cola.json") -> Path:
        path = self.queue_directory / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_loads_valid_queue_preserving_attempt_order(self):
        path = self.write_queue({"generated_at": "t", "source_file": "f.csv", "leads": [VALID_LEAD]})

        leads = load_queue(str(path), self.queue_directory)

        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["lead_id"], "00Q000000000001AAA")
        self.assertEqual([a["call_id"] for a in leads[0]["attempts"]], ["12345", "12346"])

    def test_rejects_queue_outside_queues_directory(self):
        outside = Path(self.temporary.name) / "cola.json"
        outside.write_text(json.dumps({"leads": [VALID_LEAD]}), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "queues"):
            load_queue(str(outside), self.queue_directory)

    def test_rejects_invalid_lead_id(self):
        path = self.write_queue({"leads": [{**VALID_LEAD, "lead_id": "00Q000000001"}]})

        with self.assertRaisesRegex(ValueError, "Lead 0"):
            load_queue(str(path), self.queue_directory)

    def test_rejects_lead_without_attempts(self):
        path = self.write_queue({"leads": [{**VALID_LEAD, "attempts": []}]})

        with self.assertRaisesRegex(ValueError, "Lead 0"):
            load_queue(str(path), self.queue_directory)

    def test_rejects_attempt_missing_required_field(self):
        attempt = {"result": "No contesta", "date": "15/09/2026", "time": "10:30"}
        path = self.write_queue({"leads": [{"lead_id": VALID_LEAD["lead_id"], "attempts": [attempt]}]})

        with self.assertRaisesRegex(ValueError, "call_id"):
            load_queue(str(path), self.queue_directory)

    def test_rejects_empty_leads_list(self):
        path = self.write_queue({"leads": []})

        with self.assertRaisesRegex(ValueError, "pendientes"):
            load_queue(str(path), self.queue_directory)

    def test_rejects_invalid_json(self):
        path = self.queue_directory / "rota.json"
        path.write_text("{no json", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "JSON"):
            load_queue(str(path), self.queue_directory)


if __name__ == "__main__":
    unittest.main()
