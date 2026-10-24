import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import run_distribucion_queue
from run_distribucion_queue import SKIP_OWNERS, distribute_one_lead

LEAD = {"lead_id": "00Q000000000001AAA", "persona": "Ana Perez"}
CONFIG = {
    "salesforce_url": "https://sf.example",
    "record_object_api_name": "Lead",
    "timeouts": {"page_load_seconds": 5},
    "ui_output_directory": "ui_output",
}
INGRESO = ["AR_LEAD_QUALIF", "CO_LEAD_QUALIF", "MX_LEAD_QUALIF"]


class FakeDriver:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)

    def save_screenshot(self, path):
        Path(path).write_bytes(b"png")


class DistributeOneLeadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.results_path = Path(self.temporary.name) / "cola_distribucion.resultado.json"
        self.screenshots = Path(self.temporary.name) / "capturas"
        self.driver = FakeDriver()

    def tearDown(self):
        self.temporary.cleanup()

    def run_lead(self, owner_sequence, reassign="reasignado", **overrides):
        """Ejecuta distribute_one_lead con el DOM mockeado.

        ``owner_sequence`` alimenta wait_record_owner/read_record_owner:
        la primera lectura es la del registro; las siguientes, la espera de
        cambio tras el Pick Up.
        """
        readers = list(owner_sequence)
        patches = {
            "open_record": Mock(),
            "wait_record_owner": Mock(side_effect=lambda *_a: readers[0] if readers else ""),
            "read_record_owner": Mock(side_effect=lambda *_a: readers.pop(0) if readers else ""),
            "press_pick_up": overrides.get("press_pick_up", Mock(return_value="clicked")),
            "reassign_owner": overrides.get("reassign_owner", Mock(return_value=reassign)),
            "save_contact_panel_if_present": overrides.get("panel", Mock(return_value="panel_guardado")),
            "_reread_owner_after_refresh": overrides.get("reread", Mock(return_value="Usuario Bot")),
            "capture_failure": Mock(return_value=Path("cap.png")),
        }
        with patch.multiple(run_distribucion_queue, **patches), patch("run_distribucion_queue.time.sleep"):
            entry = distribute_one_lead(
                self.driver, LEAD, CONFIG, INGRESO, self.results_path, self.screenshots, Mock(), "run_x"
            )
        return entry, patches

    def test_owner_is_destino_does_nothing(self):
        entry, patches = self.run_lead(["Ana Perez"])
        self.assertEqual(entry["status"], "ya_asignado")
        patches["press_pick_up"].assert_not_called()
        patches["reassign_owner"].assert_not_called()

    def test_owner_matches_destino_case_insensitive(self):
        entry, _ = self.run_lead(["ANA PEREZ"])
        self.assertEqual(entry["status"], "ya_asignado")

    def test_skipped_queues_are_never_touched(self):
        for owner in SKIP_OWNERS:
            entry, patches = self.run_lead([owner])
            self.assertEqual(entry["status"], "cola_excluida")
            self.assertEqual(entry["propietario_observado"], owner)
            patches["press_pick_up"].assert_not_called()
            patches["reassign_owner"].assert_not_called()

    def test_ingreso_queue_pickup_then_reassign(self):
        # Owner leído: cola; tras Pick Up pasa al usuario del bot; luego reassign.
        entry, patches = self.run_lead(["AR_LEAD_QUALIF", "AR_LEAD_QUALIF", "Usuario Bot"])
        self.assertEqual(entry["status"], "reasignado")
        patches["press_pick_up"].assert_called_once()
        patches["save_contact_panel_if_present"].assert_called_once()
        patches["reassign_owner"].assert_called_once_with(self.driver, "Ana Perez", 5)

    def test_other_owner_reassigns_directly(self):
        entry, patches = self.run_lead(["Otra Persona"])
        self.assertEqual(entry["status"], "reasignado")
        patches["press_pick_up"].assert_not_called()
        patches["save_contact_panel_if_present"].assert_not_called()

    def test_lookup_failure_keeps_error_outcome(self):
        entry, _ = self.run_lead(["Otra Persona"], reassign="reasignacion_error:opcion")
        self.assertEqual(entry["status"], "reasignacion_error:opcion")

    def test_pickup_without_button(self):
        entry, _ = self.run_lead(["AR_LEAD_QUALIF"], press_pick_up=Mock(return_value="not_found"))
        self.assertEqual(entry["status"], "pickup_error")
        self.assertEqual(entry["detalle"], "sin_boton_pickup")

    def test_pickup_owner_never_changes(self):
        # Tras el Pick Up el propietario sigue siendo la cola, incluso tras refresh.
        with patch("run_distribucion_queue.OWNER_VERIFY_TIMEOUT_SECONDS", 0.001):
            entry, _ = self.run_lead(
                ["AR_LEAD_QUALIF"] * 20, reread=Mock(return_value="AR_LEAD_QUALIF")
            )
        self.assertEqual(entry["status"], "pickup_error")
        self.assertEqual(entry["detalle"], "propietario_no_cambio")

    def test_unreadable_owner_is_inaccesible(self):
        entry, _ = self.run_lead([""])
        self.assertEqual(entry["status"], "lead_inaccesible")

    def test_navigation_failure_records_inaccesible(self):
        from selenium.common.exceptions import TimeoutException

        with (
            patch.multiple(
                run_distribucion_queue,
                open_record=Mock(side_effect=TimeoutException()),
                capture_failure=Mock(return_value=Path("cap.png")),
            ),
        ):
            entry = distribute_one_lead(
                self.driver, LEAD, CONFIG, INGRESO, self.results_path, self.screenshots, Mock(), "run_x"
            )
        self.assertEqual(entry["status"], "lead_inaccesible")

    def test_result_is_persisted_per_lead(self):
        self.run_lead(["Otra Persona"])
        persisted = json.loads(self.results_path.read_text(encoding="utf-8"))
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["lead_id"], LEAD["lead_id"])
        self.assertEqual(persisted[0]["persona"], "Ana Perez")
        self.assertEqual(persisted[0]["status"], "reasignado")


if __name__ == "__main__":
    unittest.main()
