import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_laboratory_queue as lab
from laboratory_contracts import STATUS_APTO, STATUS_ENVIADO, STATUS_NO_ELEGIBLE
from laboratory_store import LaboratoryStore, STAGE_CLIC_RESERVADO, store_path_for

LEAD = {
    "lead_id": "00Q000000000001AAA",
    "engines": ["selenium"],
    "pais": "Argentina",
    "preferencia": "Vía WhatsApp",
}
CONFIG = {
    "browser": "edge",
    "profile_directory": "perfil",
    "debugger_address": "127.0.0.1:9222",
    "salesforce_url": "https://example.lightning.force.com",
    "timeouts": {"page_load_seconds": 5},
    "log_directory": "logs",
    "screenshot_directory": "screenshots",
    "lead_list_fields": {
        "pais": ["País"],
        "preferencia_contacto": ["Preferencia de contacto"],
    },
    "ui_output_directory": "ui_output",
    "queue_directory": "queues",
}


class FakeBrowser:
    engine = "selenium"

    def __init__(self, fields=None, clicks="clicked", toast=True, authenticated=True, opened=None):
        self.fields = fields or {}
        self.clicks = clicks
        self.toast = toast
        self.authenticated = authenticated
        self.opened = opened  # None => el lead abierto (identidad correcta)
        self.writes = []
        self.wa_clicks = 0
        self.armed = 0

    def open_record(self, lead_id):
        self.lead_id = lead_id

    def is_authenticated(self):
        return self.authenticated

    def current_record_id(self):
        return self.opened if self.opened is not None else self.lead_id

    def field_text(self, labels):
        for label in labels:
            if label in self.fields:
                return self.fields[label]
        return ""

    def wait_field_text(self, labels, timeout):
        return self.field_text(labels)

    def whatsapp_button_present(self):
        return self.clicks != "sin_boton"

    def write_and_save_field(self, labels, display, text, timeout):
        self.writes.append(text)
        self.fields[labels[0]] = text

    def reload(self, timeout):
        pass

    def click_whatsapp(self):
        self.wa_clicks += 1
        return self.clicks

    def whatsapp_toast(self, timeout):
        return self.toast

    def arm_whatsapp_observation(self):
        self.armed += 1
        return {"armed": True, "baseline": []}

    def guarded_click_whatsapp(self, expected_lead_id):
        self.wa_clicks += 1
        if expected_lead_id != self.lead_id:
            return "id_mismatch"
        return self.clicks

    def collect_whatsapp_evidence(self, timeout):
        if self.toast:
            return {"outcome": "confirmado", "reason": "toast_positivo", "events": [{"norm": "enviado"}]}
        return {"outcome": "no_confirmado", "reason": "sin_senal", "events": []}

    def dispose_whatsapp_observation(self):
        pass

    def close_whatsapp_toast(self):
        pass

    def release(self):
        pass


def ar_fields(pais="Argentina", pref="Vía WhatsApp", otra=""):
    # país/preferencia ya vienen en la cola (BD); la ficha solo aporta
    # Otra información. Los args se conservan para claridad en los tests.
    return {"otra información": otra}


def tmp_store(tmp):
    return LaboratoryStore(store_path_for(Path(tmp) / "ui_output"))


class VerifyLeadTests(unittest.TestCase):
    def test_apto_returns_next_attempt_line(self):
        browser = FakeBrowser(ar_fields(otra="1 INT Llamada 01/01/2026 10:00"))
        outcome = lab.verify_lead(browser, LEAD, CONFIG)
        self.assertEqual(outcome["status"], STATUS_APTO)
        self.assertTrue(outcome["attempt_line"].startswith("2 INT Se envía WhatsApp "))

    def test_no_elegible_filters_pais_and_preferencia(self):
        browser = FakeBrowser(ar_fields())
        lead_colombia = {**LEAD, "pais": "Colombia"}
        self.assertEqual(
            lab.verify_lead(browser, lead_colombia, CONFIG)["status"],
            STATUS_NO_ELEGIBLE,
        )
        lead_llamada = {**LEAD, "preferencia": "Llamada"}
        self.assertEqual(
            lab.verify_lead(browser, lead_llamada, CONFIG)["status"],
            STATUS_NO_ELEGIBLE,
        )
        # El lead no elegible ni siquiera abre la ficha.
        self.assertFalse(hasattr(browser, "lead_id"))

    def test_pais_vacio_se_interpreta_argentina(self):
        browser = FakeBrowser(ar_fields())
        lead_sin_pais = {k: v for k, v in LEAD.items() if k != "pais"}
        outcome = lab.verify_lead(browser, lead_sin_pais, CONFIG)
        self.assertEqual(outcome["status"], STATUS_APTO)


class SendForLeadTests(unittest.TestCase):
    def test_documents_history_and_sends(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            browser = FakeBrowser(ar_fields(otra="3 INT Contacto previo"))
            outcome = lab.send_for_lead(browser, LEAD, CONFIG, store, "camp")
            self.assertEqual(outcome["status"], STATUS_ENVIADO)
            self.assertEqual(browser.wa_clicks, 1)
            written = browser.writes[0]
            self.assertIn("3 INT Contacto previo", written)
            self.assertTrue(
                written.rstrip().endswith(
                    "INT Se envía WhatsApp " + written.rsplit(" ", 2)[-2] + " " + written.rsplit(" ", 1)[-1]
                )
            )
            op = store.get_operation("camp", LEAD["lead_id"])
            self.assertEqual(op["send_status"], "confirmado")
            self.assertEqual(op["next_int"], 4)

    def test_no_toast_blocks_retry_forever(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            browser = FakeBrowser(ar_fields(), toast=False)
            outcome = lab.send_for_lead(browser, LEAD, CONFIG, store, "camp")
            self.assertEqual(outcome["status"], "documentado_wa_no_confirmado")
            blocked, _ = store.is_blocked("camp", LEAD["lead_id"])
            self.assertTrue(blocked)
            # Reanudar: el lead bloqueado sigue bloqueado tras releer el diario.
            blocked2, reason = store.is_blocked("camp", LEAD["lead_id"])
            self.assertTrue(blocked2)

    def test_click_reservado_crash_is_indeterminate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            store.begin_operation("camp", LEAD["lead_id"], "selenium", 1, "1 INT Se envía WhatsApp 17/11/2026 09:00")
            store.advance("camp", LEAD["lead_id"], STAGE_CLIC_RESERVADO)
            blocked, reason = store.is_blocked("camp", LEAD["lead_id"])
            self.assertTrue(blocked)
            self.assertEqual(reason, "indeterminado")

    def test_verification_failure_blocks_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)

            class FailVerify(FakeBrowser):
                def write_and_save_field(self, labels, display, text, timeout):
                    # Simula un save que Salesforce nunca confirma en UI.
                    self.writes.append(text)

            config = {**CONFIG, "timeouts": {"page_load_seconds": 5, "save_verify_seconds": 0}}
            browser = FailVerify(ar_fields())
            outcome = lab.send_for_lead(browser, LEAD, config, store, "camp")
            self.assertEqual(outcome["status"], "error_documentacion")
            self.assertEqual(browser.wa_clicks, 0)  # nunca envía sin doc confirmada

    def test_missing_identity_blocks_before_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            browser = FakeBrowser(ar_fields(), opened="")
            outcome = lab.send_for_lead(browser, LEAD, CONFIG, store, "camp")
            self.assertEqual(outcome["status"], "bloqueado")
            self.assertIn("id_invalido", outcome["detail"])
            self.assertEqual(browser.wa_clicks, 0)
            self.assertEqual(browser.writes, [])

    def test_wrong_identity_blocks_before_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            browser = FakeBrowser(ar_fields(), opened="00Q000000000099AAA")
            outcome = lab.send_for_lead(browser, LEAD, CONFIG, store, "camp")
            self.assertEqual(outcome["status"], "bloqueado")
            self.assertEqual(browser.wa_clicks, 0)

    def test_expired_session_blocks_before_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            browser = FakeBrowser(ar_fields(), authenticated=False)
            outcome = lab.send_for_lead(browser, LEAD, CONFIG, store, "camp")
            self.assertEqual(outcome["status"], "bloqueado")
            self.assertIn("sesion", outcome["detail"])
            self.assertEqual(browser.wa_clicks, 0)

    def test_verify_blocks_on_empty_identity(self):
        browser = FakeBrowser(ar_fields(), opened="")
        outcome = lab.verify_lead(browser, LEAD, CONFIG)
        self.assertEqual(outcome["status"], "bloqueado")

    def test_evidence_and_reservation_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            browser = FakeBrowser(ar_fields())
            lab.send_for_lead(browser, LEAD, CONFIG, store, "camp")
            op = store.get_operation("camp", LEAD["lead_id"])
            evidence = json.loads(op["evidence"])
            self.assertEqual(evidence["confirmation"]["outcome"], "confirmado")
            self.assertEqual(evidence["click"], "clicked")
            self.assertEqual(evidence["expected_lead_id"], LEAD["lead_id"])
            reservation = store.reservation_for(LEAD["lead_id"])
            self.assertIsNotNone(reservation)
            self.assertEqual(reservation["state"], "confirmado")

    def test_reservation_blocks_other_campaigns(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            browser = FakeBrowser(ar_fields(), toast=False)
            lab.send_for_lead(browser, LEAD, CONFIG, store, "camp1")
            # Otra campaña/importación del mismo lead: la reserva bloquea.
            blocked, reason = store.is_blocked("camp2", LEAD["lead_id"])
            self.assertTrue(blocked)
            self.assertIn("reserva:", reason)

    def test_guarded_click_failure_is_indeterminate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            browser = FakeBrowser(ar_fields(), clicks="cubierto")
            outcome = lab.send_for_lead(browser, LEAD, CONFIG, store, "camp")
            self.assertEqual(outcome["status"], "documentado_wa_error")
            op = store.get_operation("camp", LEAD["lead_id"])
            self.assertEqual(op["send_status"], "indeterminado")
            self.assertEqual(op["review_reason"], "cubierto")


class AuditLeadTests(unittest.TestCase):
    def _store_with_op(self, tmp, field="1 INT Se envía WhatsApp 17/11/2026 09:00"):
        store = tmp_store(tmp)
        store.begin_operation("camp", LEAD["lead_id"], "selenium", 1, field)
        return store

    def test_audit_ok_single_occurrence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_op(tmp)
            browser = FakeBrowser(ar_fields(otra="1 INT Se envía WhatsApp 17/11/2026 09:00"))
            outcome = lab.audit_lead(browser, LEAD, CONFIG, store)
            self.assertEqual(outcome["status"], "auditada")

    def test_audit_discrepancia_double_occurrence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_op(tmp)
            browser = FakeBrowser(
                ar_fields(otra="1 INT Se envía WhatsApp 17/11/2026 09:00\n1 INT Se envía WhatsApp 17/11/2026 09:00")
            )
            outcome = lab.audit_lead(browser, LEAD, CONFIG, store)
            self.assertEqual(outcome["status"], "audit_discrepancia")
            self.assertIn("ocurrencias:2", outcome["detail"])

    def test_audit_sin_reserva(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tmp_store(tmp)
            browser = FakeBrowser(ar_fields())
            outcome = lab.audit_lead(browser, LEAD, CONFIG, store)
            self.assertEqual(outcome["status"], "audit_sin_reserva")

    def test_audit_wrong_identity_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_op(tmp)
            browser = FakeBrowser(ar_fields(), opened="00Q000000000099AAA")
            outcome = lab.audit_lead(browser, LEAD, CONFIG, store)
            self.assertEqual(outcome["status"], "bloqueado")


class RunQueueTests(unittest.TestCase):
    def test_prueba_mode_writes_nothing_and_real_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            queues = tmp_path / "queues"
            queues.mkdir()
            queue_path = queues / "lab.json"
            queue_path.write_text(
                json.dumps(
                    {
                        "operation": "laboratorio_whatsapp",
                        "mode": "prueba",
                        "engine": "selenium",
                        "campaign_id": "camp_x",
                        "leads": [{"lead_id": "00Q000000000001AAA", "preferencia": "Vía WhatsApp"}],
                    }
                ),
                encoding="utf-8",
            )
            results_path = queues / "res.jsonl"
            metrics_path = queues / "met.json"
            browser = FakeBrowser(ar_fields())
            with (
                patch.object(
                    lab,
                    "load_config",
                    return_value={
                        **CONFIG,
                        "queue_directory": str(queues),
                        "ui_output_directory": str(tmp_path / "ui_output"),
                    },
                ),
                patch.object(lab, "make_browser", return_value=browser),
                patch.object(lab, "create_logger", return_value=__import__("logging").getLogger("t")),
            ):
                code = lab.run_queue(str(queue_path), "run_test", results_path, metrics_path)
            self.assertEqual(code, 0)
            entries = lab.read_results(results_path)
            self.assertEqual(entries[0]["status"], STATUS_APTO)
            self.assertEqual(browser.wa_clicks, 0)
            self.assertEqual(browser.writes, [])
            self.assertTrue(metrics_path.exists())


if __name__ == "__main__":
    unittest.main()
