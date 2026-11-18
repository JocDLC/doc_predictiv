import unittest
from datetime import datetime, timezone

from laboratory_contracts import (
    LAB_OPERATION,
    argentina_now,
    build_queue,
    canonical_lead_id,
    is_argentina,
    validate_laboratory_queue,
    wants_whatsapp,
    whatsapp_attempt_line,
)

LEAD = {"lead_id": "00Q000000000001AAA"}


class ContractTests(unittest.TestCase):
    def test_validates_basic_queue(self):
        queue = validate_laboratory_queue(
            {
                "operation": LAB_OPERATION,
                "mode": "prueba",
                "engine": "agent_browser",
                "campaign_id": "lab_x",
                "leads": [LEAD],
            }
        )
        self.assertEqual(queue["mode"], "prueba")
        self.assertEqual(queue["engine"], "agent_browser")
        self.assertEqual(queue["leads"][0]["engines"], ["agent_browser"])

    def test_comparacion_only_in_prueba(self):
        with self.assertRaises(ValueError):
            validate_laboratory_queue(
                {
                    "operation": LAB_OPERATION,
                    "mode": "real",
                    "engine": "comparacion",
                    "leads": [LEAD],
                }
            )
        queue = validate_laboratory_queue(
            {
                "operation": LAB_OPERATION,
                "mode": "prueba",
                "engine": "comparacion",
                "leads": [LEAD],
            }
        )
        self.assertEqual(queue["leads"][0]["engines"], ["selenium", "agent_browser"])

    def test_rejects_duplicates_bad_ids_and_empty(self):
        with self.assertRaises(ValueError):
            validate_laboratory_queue({"operation": LAB_OPERATION, "leads": [LEAD, LEAD]})
        with self.assertRaises(ValueError):
            validate_laboratory_queue({"operation": LAB_OPERATION, "leads": []})
        with self.assertRaises(ValueError):
            validate_laboratory_queue({"operation": LAB_OPERATION, "leads": [{"lead_id": "123"}]})
        with self.assertRaises(ValueError):
            validate_laboratory_queue({"operation": "otra", "leads": [LEAD]})

    def test_canonical_lead_id(self):
        self.assertEqual(canonical_lead_id(" 00Q000000000001AAA "), "00Q000000000001AAA")
        self.assertEqual(canonical_lead_id("00Q000000000001"), "00Q000000000001")
        with self.assertRaises(ValueError):
            canonical_lead_id("abc")

    def test_country_and_preference_matching(self):
        self.assertTrue(is_argentina("Argentina"))
        self.assertTrue(is_argentina("argentina "))
        self.assertFalse(is_argentina("Colombia"))
        self.assertTrue(wants_whatsapp("Vía WhatsApp"))
        self.assertTrue(wants_whatsapp("WHATSAPP"))
        self.assertFalse(wants_whatsapp("Llamada"))
        self.assertFalse(wants_whatsapp(""))

    def test_attempt_line_format_and_argentina_time(self):
        # 2026-11-17 12:00 UTC → 09:00 Argentina (UTC-3).
        line = whatsapp_attempt_line(3, datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(line, "3 INT Se envía WhatsApp 17/11/2026 09:00")
        self.assertEqual(argentina_now(datetime(2026, 11, 17, 2, 0, tzinfo=timezone.utc)).hour, 23)
        with self.assertRaises(ValueError):
            whatsapp_attempt_line(0)

    def test_build_queue_roundtrip(self):
        queue = build_queue(
            [{"lead_id": "00Q000000000001AAA", "nombre": "Ana"}],
            mode="real",
            engine="selenium",
            campaign_id="lab_test",
        )
        self.assertEqual(queue["leads"][0]["nombre"], "Ana")
        self.assertEqual(queue["batch_size"], 10)


if __name__ == "__main__":
    unittest.main()


class AuditAndComparisonTests(unittest.TestCase):
    def test_auditoria_mode_accepted(self):
        queue = build_queue(
            [{"lead_id": "00Q000000000001AAA"}],
            mode="auditoria",
            engine="agent_browser",
            campaign_id="audit",
        )
        self.assertEqual(queue["mode"], "auditoria")

    def test_comparacion_alternates_engine_order(self):
        queue = build_queue(
            [{"lead_id": "00Q000000000001AAA"}, {"lead_id": "00Q000000000002AAA"}],
            mode="prueba",
            engine="comparacion",
            campaign_id="lab",
        )
        self.assertEqual(queue["leads"][0]["engines"], ["selenium", "agent_browser"])
        self.assertEqual(queue["leads"][1]["engines"], ["agent_browser", "selenium"])
