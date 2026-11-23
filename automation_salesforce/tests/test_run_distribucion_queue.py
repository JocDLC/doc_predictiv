import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import run_distribucion_queue
from run_distribucion_queue import SKIP_OWNERS, distribute_one_lead, simulate_one_lead

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
    def test_pickup_y_reasignacion_no_escriben_comentarios(self):
        """El lote guarda Contact Client y reasigna, sin documentar ni enviar."""
        from lead_monitor import save_contact_panel_if_present

        with (
            patch("lead_monitor._save_contact_panel_initial", return_value="panel_guardado") as panel,
            patch("lead_monitor._ensure_take_mark") as mark,
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form") as save,
            patch("lead_monitor.send_whatsapp") as send,
        ):
            entry, patches = self.run_lead(
                ["AR_LEAD_QUALIF", "AR_LEAD_QUALIF", "Usuario Bot"],
                panel=save_contact_panel_if_present,
            )
            self.assertEqual(entry["status"], "reasignado")
            patches["press_pick_up"].assert_called_once()
            panel.assert_called_once()
            patches["reassign_owner"].assert_called_once()
            mark.assert_not_called()
            edit.assert_not_called()
            save.assert_not_called()
            send.assert_not_called()

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
            "owner_page_diagnostic": overrides.get("diag", Mock(return_value="titulo:'x' | etiqueta_owner:no")),
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

    def test_entry_carries_lead_nombre(self):
        """La entrada de resultado guarda el nombre del lead del archivo:
        la columna Lead se mantiene aunque la página se recargue."""
        with patch.multiple(
            run_distribucion_queue,
            open_record=Mock(),
            wait_record_owner=Mock(return_value="Ana Perez"),
            press_pick_up=Mock(),
            reassign_owner=Mock(),
        ):
            entry = distribute_one_lead(
                self.driver,
                {**LEAD, "nombre": "Juan Cliente"},
                CONFIG,
                INGRESO,
                self.results_path,
                self.screenshots,
                Mock(),
                "run_x",
            )
        self.assertEqual(entry["nombre"], "Juan Cliente")

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

    def test_other_country_managed_queues_are_never_touched(self):
        # Listas viejas: un lead ya derivado al canal frío/export de MX o CO
        # ya fue gestionado — no se toca aunque la fila diga otra cosa.
        for owner in ("MX_LEAD_COLD", "MX_LEAD_EXPORT_GETLEAD", "CO_LEAD_COLD", "CO_LEAD_EXPORT_GETLEAD"):
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
            entry, _ = self.run_lead(["AR_LEAD_QUALIF"] * 20, reread=Mock(return_value="AR_LEAD_QUALIF"))
        self.assertEqual(entry["status"], "pickup_error")
        self.assertEqual(entry["detalle"], "propietario_no_cambio")

    def test_unreadable_owner_is_inaccesible(self):
        entry, _ = self.run_lead([""], reread=Mock(return_value=""))
        self.assertEqual(entry["status"], "lead_inaccesible")

    def test_unreadable_owner_retries_with_refresh_reread(self):
        """Bug del lote 17/11: el campo Propietario no apareció en la
        primera lectura pero sí tras recargar — el lead no es inaccesible,
        solo lento. Se reintenta con refresh antes de declarar."""
        entry, _ = self.run_lead([""], reread=Mock(return_value="Ana Perez"))
        self.assertEqual(entry["status"], "ya_asignado")

    def test_unreadable_owner_reports_page_diagnostic(self):
        """Si ni tras refresh aparece el campo, el detalle trae evidencia
        de la página (título/url/etiqueta de propietario) — el dato que
        distingue 'lead sin permiso' de 'campo con otra etiqueta'."""
        entry, patches = self.run_lead([""], reread=Mock(return_value=""))
        self.assertEqual(entry["status"], "lead_inaccesible")
        self.assertIn("propietario_ilegible", entry["detalle"])
        self.assertIn("etiqueta_owner", entry["detalle"])
        patches["capture_failure"].assert_called_once()

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


class SimulateOneLeadTests(unittest.TestCase):
    """Modo prueba: mismo recorrido de lectura/clasificación que la corrida
    real, pero NUNCA escribe en Salesforce —ni Pick Up ni reasignar— y los
    estados salen con prefijo ``prueba_``."""

    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.results_path = Path(self.temporary.name) / "cola_distribucion.resultado.json"
        self.screenshots = Path(self.temporary.name) / "capturas"
        self.driver = FakeDriver()

    def tearDown(self):
        self.temporary.cleanup()

    def run_lead(self, owner, verify="opcion_ok", reread=None):
        patches = {
            "open_record": Mock(),
            "wait_record_owner": Mock(return_value=owner),
            "_reread_owner_after_refresh": reread if reread is not None else Mock(return_value=""),
            "verify_persona_option": Mock(return_value=verify) if isinstance(verify, str) else Mock(side_effect=verify),
            "press_pick_up": Mock(),
            "reassign_owner": Mock(),
            "save_contact_panel_if_present": Mock(),
            "capture_failure": Mock(return_value=Path("cap.png")),
            "owner_page_diagnostic": Mock(return_value="titulo:'x' | etiqueta_owner:no"),
        }
        with patch.multiple(run_distribucion_queue, **patches):
            entry = simulate_one_lead(
                self.driver, LEAD, CONFIG, INGRESO, self.results_path, self.screenshots, Mock(), "run_x"
            )
        # Regla de oro del modo prueba: jamás se toca Salesforce.
        patches["press_pick_up"].assert_not_called()
        patches["reassign_owner"].assert_not_called()
        patches["save_contact_panel_if_present"].assert_not_called()
        return entry, patches

    def test_owner_is_destino_does_nothing(self):
        entry, patches = self.run_lead("Ana Perez")
        self.assertEqual(entry["status"], "prueba_ok:ya_asignado")
        patches["verify_persona_option"].assert_not_called()

    def test_skipped_queues_are_never_touched(self):
        for owner in SKIP_OWNERS:
            entry, patches = self.run_lead(owner)
            self.assertEqual(entry["status"], "prueba_ok:cola_excluida")
            self.assertEqual(entry["propietario_observado"], owner)
            patches["verify_persona_option"].assert_not_called()

    def test_other_country_managed_queues_are_listed_only(self):
        for owner in ("MX_LEAD_COLD", "MX_LEAD_EXPORT_GETLEAD", "CO_LEAD_COLD", "CO_LEAD_EXPORT_GETLEAD"):
            entry, patches = self.run_lead(owner)
            self.assertEqual(entry["status"], "prueba_ok:cola_excluida")
            self.assertEqual(entry["propietario_observado"], owner)
            patches["verify_persona_option"].assert_not_called()

    def test_ingreso_queue_reports_pickup_y_reasignar(self):
        entry, patches = self.run_lead("AR_LEAD_QUALIF")
        self.assertEqual(entry["status"], "prueba_ok:pickup_y_reasignar")
        patches["verify_persona_option"].assert_called_once_with(self.driver, "Ana Perez", 5, unittest.mock.ANY)

    def test_other_owner_reports_reasignar(self):
        entry, _ = self.run_lead("Otra Persona")
        self.assertEqual(entry["status"], "prueba_ok:reasignar")
        self.assertEqual(entry["propietario_observado"], "Otra Persona")

    def test_name_not_in_lookup_reports_nombre_no_encontrado(self):
        for owner in ("AR_LEAD_QUALIF", "Otra Persona"):
            entry, _ = self.run_lead(owner, verify="reasignacion_error:opcion")
            self.assertEqual(entry["status"], "prueba_nombre_no_encontrado")
            self.assertEqual(entry["propietario_observado"], owner)

    def test_modal_failures_report_prueba_error_paso(self):
        for outcome, expected in (
            ("reasignacion_error:modal", "prueba_error:modal"),
            ("reasignacion_error:busqueda", "prueba_error:busqueda"),
        ):
            entry, _ = self.run_lead("Otra Persona", verify=outcome)
            self.assertEqual(entry["status"], expected)

    def test_unreadable_owner_is_prueba_inaccesible(self):
        entry, patches = self.run_lead("")
        self.assertEqual(entry["status"], "prueba_inaccesible")
        self.assertIn("propietario_ilegible", entry["detalle"])
        patches["verify_persona_option"].assert_not_called()

    def test_unreadable_owner_retries_with_refresh_reread(self):
        """Réplica del lote 17/11: 133 leads 'inaccesibles' que a mano
        muestran el propietario — el campo llega tarde, no falta."""
        entry, patches = self.run_lead("", reread=Mock(return_value="Ana Perez"))
        self.assertEqual(entry["status"], "prueba_ok:ya_asignado")
        patches["verify_persona_option"].assert_not_called()

    def test_unreadable_owner_reports_page_diagnostic(self):
        entry, patches = self.run_lead("", reread=Mock(return_value=""))
        self.assertEqual(entry["status"], "prueba_inaccesible")
        self.assertIn("propietario_ilegible", entry["detalle"])
        self.assertIn("etiqueta_owner", entry["detalle"])
        patches["capture_failure"].assert_called_once()

    def test_lookup_diag_reports_closed_dialog(self):
        """Cuando el modal se cierra antes del volcado, el detalle lo
        declara — no 'opciones vistas' de otro contenedor de la página
        (caso 'notas y archivos adjuntos' del lote 17/11)."""
        from run_distribucion_queue import _format_lookup_diag

        detalle = _format_lookup_diag({"dialog_cerrado": True})
        self.assertIn("cerr", detalle.lower())

    def test_nombre_no_encontrado_detail_shows_what_lookup_saw(self):
        """Si la opción no aparece, el detalle cuenta qué vio el desplegable:
        el texto tipeado y las opciones visibles — el diagnóstico que
        faltaba para el caso 'nombre no encontrado en Salesforce'."""

        def fake_verify(driver, nombre, timeout, diagnostics):
            diagnostics.update({"inputValue": nombre, "options": ["ana perez"]})
            return "reasignacion_error:opcion"

        entry, _ = self.run_lead("Otra Persona", verify=fake_verify)
        self.assertEqual(entry["status"], "prueba_nombre_no_encontrado")
        self.assertIn("ana perez", entry["detalle"])
        self.assertIn("Ana Perez", entry["detalle"])

    def test_navigation_failure_records_prueba_inaccesible(self):
        from selenium.common.exceptions import TimeoutException

        with patch.multiple(
            run_distribucion_queue,
            open_record=Mock(side_effect=TimeoutException()),
            capture_failure=Mock(return_value=Path("cap.png")),
        ):
            entry = simulate_one_lead(
                self.driver, LEAD, CONFIG, INGRESO, self.results_path, self.screenshots, Mock(), "run_x"
            )
        self.assertEqual(entry["status"], "prueba_inaccesible")

    def test_result_is_persisted_with_modo_prueba(self):
        entry, _ = self.run_lead("Otra Persona")
        self.assertEqual(entry["modo"], "prueba")
        persisted = json.loads(self.results_path.read_text(encoding="utf-8"))
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["status"], "prueba_ok:reasignar")
        self.assertEqual(persisted[0]["modo"], "prueba")


class ConsumirAperturaTests(unittest.TestCase):
    """La corrida REAL marca consumido el lead de apertura confirmado —
    la simulación y los estados no confirmados no consumen (REQ-835)."""

    def setUp(self):
        from tempfile import TemporaryDirectory

        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.config = {"ui_output_directory": self._tmp.name}
        self.store_dir = Path(self._tmp.name) / "apertura"

        from apertura_store import ESTADO_TOMADO_CONFIRMADO, create_lote, update_lead

        lote = create_lote(self.store_dir, bandeja="AR", desde="d", hasta="h", lead_ids=["00Q1", "00Q2"])
        update_lead(self.store_dir, lote["lote_id"], "00Q1", ESTADO_TOMADO_CONFIRMADO)
        update_lead(self.store_dir, lote["lote_id"], "00Q2", ESTADO_TOMADO_CONFIRMADO)

    def _disponibles(self):
        from apertura_store import disponibles

        return [d["lead_id"] for d in disponibles(self.store_dir)]

    def test_reasignado_real_consume(self):
        from run_distribucion_queue import _consumir_apertura

        _consumir_apertura(self.config, "00Q1", "reasignado", "real", "run_1")
        self.assertEqual(self._disponibles(), ["00Q2"])

    def test_ya_asignado_real_consume(self):
        from run_distribucion_queue import _consumir_apertura

        _consumir_apertura(self.config, "00Q1", "ya_asignado", "real", "run_1")
        self.assertEqual(self._disponibles(), ["00Q2"])

    def test_prueba_no_consume(self):
        from run_distribucion_queue import _consumir_apertura

        _consumir_apertura(self.config, "00Q1", "prueba_ok:reasignar", "prueba", "run_1")
        self.assertEqual(sorted(self._disponibles()), ["00Q1", "00Q2"])

    def test_error_no_consume(self):
        from run_distribucion_queue import _consumir_apertura

        _consumir_apertura(self.config, "00Q1", "error", "real", "run_1")
        self.assertEqual(sorted(self._disponibles()), ["00Q1", "00Q2"])


if __name__ == "__main__":
    unittest.main()
