import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from correction_loader import load_corrections
from run_corrections import correction_entry
from snapshot_store import content_hash


def _write_corrections(path: Path, corrections) -> None:
    path.write_text(
        json.dumps({"corrections": corrections}, ensure_ascii=False),
        encoding="utf-8",
    )


def _valid_correction(**overrides) -> dict:
    correction = {
        "lead_id": "00Q000000000001AAA",
        "new_value": "1 INT\tResultado\t01/01/2026\t10:00\t1",
        "base_hash": content_hash("texto base"),
    }
    correction.update(overrides)
    return correction


class CorrectionLoaderTests(unittest.TestCase):
    def test_loads_valid_corrections(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "correcciones.json"
            _write_corrections(path, [_valid_correction()])

            corrections = load_corrections(str(path))

        self.assertEqual(len(corrections), 1)
        self.assertEqual(corrections[0]["lead_id"], "00Q000000000001AAA")

    def test_rejects_missing_file(self):
        with self.assertRaises(ValueError):
            load_corrections("ui_output/no_existe.json")

    def test_rejects_invalid_base_hash(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "correcciones.json"
            _write_corrections(path, [_valid_correction(base_hash="no-es-hash")])

            with self.assertRaises(ValueError):
                load_corrections(str(path))

    def test_rejects_missing_new_value(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "correcciones.json"
            correction = _valid_correction()
            del correction["new_value"]
            _write_corrections(path, [correction])

            with self.assertRaises(ValueError):
                load_corrections(str(path))

    def test_rejects_non_list_payload(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "correcciones.json"
            path.write_text('{"corrections": {}}', encoding="utf-8")

            with self.assertRaises(ValueError):
                load_corrections(str(path))


class CorrectionDecisionTests(unittest.TestCase):
    def test_matching_hash_allows_write(self):
        base = "texto base"
        self.assertEqual(content_hash(base), content_hash(base))

    def test_different_value_produces_different_hash(self):
        self.assertNotEqual(content_hash("texto base"), content_hash("texto cambiado"))

    def test_empty_and_none_values_share_hash(self):
        self.assertEqual(content_hash(""), content_hash(None))

    def test_correction_entry_has_no_customer_content(self):
        entry = correction_entry("00Q000000000001AAA", "corregido")
        self.assertEqual(set(entry), {"lead_id", "status", "at"})
        self.assertEqual(entry["status"], "corregido")


if __name__ == "__main__":
    unittest.main()
