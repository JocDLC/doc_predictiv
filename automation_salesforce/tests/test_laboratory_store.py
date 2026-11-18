import tempfile
import unittest
from pathlib import Path

from laboratory_store import (
    SEND_CONFIRMADO,
    SEND_INDETERMINADO,
    STAGE_CLIC_RESERVADO,
    STAGE_TERMINAL,
    LaboratoryStore,
    operation_id,
)

CAMPAIGN = "lab_test"
LEAD = "00Q000000000001AAA"


def make_store(tmp: str) -> LaboratoryStore:
    return LaboratoryStore(Path(tmp) / "lab.sqlite3")


class StoreTests(unittest.TestCase):
    def test_begin_operation_is_idempotent_and_keeps_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            first = store.begin_operation(
                CAMPAIGN, LEAD, "selenium", 2, "2 INT Se envía WhatsApp 17/11/2026 09:00", "prev"
            )
            second = store.begin_operation(
                CAMPAIGN, LEAD, "selenium", 5, "5 INT Se envía WhatsApp 18/11/2026 10:00", "prev"
            )
            # La reanudación nunca recalcula la línea ya reservada.
            self.assertEqual(second["attempt_line"], first["attempt_line"])
            self.assertEqual(second["next_int"], 2)

    def test_blocked_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            blocked, _ = store.is_blocked(CAMPAIGN, LEAD)
            self.assertFalse(blocked)
            store.begin_operation(CAMPAIGN, LEAD, "selenium")
            store.advance(CAMPAIGN, LEAD, STAGE_TERMINAL, send_status=SEND_CONFIRMADO)
            blocked, reason = store.is_blocked(CAMPAIGN, LEAD)
            self.assertTrue(blocked)
            self.assertEqual(reason, SEND_CONFIRMADO)

    def test_clic_reservado_without_terminal_is_indeterminate(self):
        """Un crash tras reservar el clic bloquea el reenvío para siempre."""
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.begin_operation(CAMPAIGN, LEAD, "selenium", 1, "1 INT Se envía WhatsApp 17/11/2026 09:00")
            store.advance(CAMPAIGN, LEAD, STAGE_CLIC_RESERVADO)
            blocked, reason = store.is_blocked(CAMPAIGN, LEAD)
            self.assertTrue(blocked)
            self.assertEqual(reason, SEND_INDETERMINADO)

    def test_pending_for_campaign_and_terminal_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.begin_operation(CAMPAIGN, LEAD, "selenium")
            store.begin_operation(CAMPAIGN, "00Q000000000002AAA", "selenium")
            store.advance(CAMPAIGN, LEAD, STAGE_TERMINAL)
            pending = store.pending_for_campaign(CAMPAIGN)
            self.assertEqual([p["lead_id"] for p in pending], ["00Q000000000002AAA"])

    def test_update_plan_renumbers_only_before_click(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.begin_operation(CAMPAIGN, LEAD, "selenium", 2, "2 INT Se envía WhatsApp 17/11/2026 09:00")
            store.update_plan(CAMPAIGN, LEAD, 4, "4 INT Se envía WhatsApp 17/11/2026 09:05", "nuevo")
            op = store.get_operation(CAMPAIGN, LEAD)
            self.assertEqual(op["next_int"], 4)
            # Tras reservar el clic el plan ya no se renumera.
            store.advance(CAMPAIGN, LEAD, STAGE_CLIC_RESERVADO)
            store.update_plan(CAMPAIGN, LEAD, 9, "9 INT Se envía WhatsApp 17/11/2026 09:10", "otro")
            self.assertEqual(store.get_operation(CAMPAIGN, LEAD)["next_int"], 4)

    def test_run_lifecycle_and_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.ensure_campaign(CAMPAIGN, "bd.xlsx", "ds1")
            store.register_run("run_1", CAMPAIGN, "real", "selenium")
            self.assertFalse(store.request_stop("run_inexistente"))
            self.assertTrue(store.request_stop("run_1"))
            self.assertTrue(store.stop_requested("run_1"))
            store.finish_run("run_1", "detenido")
            info = store.run_info("run_1")
            self.assertEqual(info["status"], "detenido")
            self.assertEqual(store.latest_run()["run_id"], "run_1")

    def test_operation_id(self):
        self.assertEqual(operation_id("c", "l"), "c|l")


if __name__ == "__main__":
    unittest.main()


class ReservationTests(unittest.TestCase):
    def test_reserve_send_click_blocks_other_campaigns(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.begin_operation("camp1", LEAD, "selenium", 1, "1 INT Se envía WhatsApp 17/11/2026 09:00")
            store.reserve_send_click("camp1", LEAD)
            blocked, reason = store.is_blocked("camp2", LEAD)
            self.assertTrue(blocked)
            self.assertIn("reserva:", reason)

    def test_reservation_state_updates_on_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.begin_operation("camp1", LEAD, "selenium", 1, "línea")
            store.reserve_send_click("camp1", LEAD)
            store.advance("camp1", LEAD, STAGE_TERMINAL, send_status=SEND_CONFIRMADO)
            reservation = store.reservation_for(LEAD)
            self.assertEqual(reservation["state"], "confirmado")

    def test_migration_blocks_historical_operations(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.begin_operation("camp_vieja", LEAD, "selenium", 1, "línea")
            store.reserve_send_click("camp_vieja", LEAD)
            store.advance("camp_vieja", LEAD, STAGE_TERMINAL, send_status=SEND_CONFIRMADO)
            store2 = LaboratoryStore(Path(tmp) / "lab.sqlite3", org_source="org2")
            blocked, reason = store2.is_blocked("otra_camp", LEAD)
            self.assertTrue(blocked)
            self.assertIn("reserva:", reason)

    def test_reservations_are_scoped_by_org(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LaboratoryStore(Path(tmp) / "lab.sqlite3", org_source="org1")
            store.begin_operation("camp1", LEAD, "selenium", 1, "línea")
            store.reserve_send_click("camp1", LEAD)
            # org distinto: la reserva de org1 no se pisa y sigue consultable.
            LaboratoryStore(Path(tmp) / "lab.sqlite3", org_source="org_otro")
            self.assertIsNotNone(store.reservation_for(LEAD))

    def test_latest_operation_for_lead_across_campaigns(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.begin_operation("camp1", LEAD, "selenium", 1, "línea1")
            store.begin_operation("camp2", LEAD, "selenium", 2, "línea2")
            latest = store.latest_operation_for_lead(LEAD)
            self.assertIsNotNone(latest)
            self.assertIn(latest["campaign_id"], ("camp1", "camp2"))
