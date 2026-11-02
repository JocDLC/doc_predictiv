import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from monitor_store import (
    MAX_ATTEMPTS,
    MAX_RESULTS,
    STATUS_DETECTADO,
    STATUS_ERROR,
    STATUS_NO_VERIFICADO,
    STATUS_TOMADO,
    STATUS_TOMADO_POR_OTRO,
    clear_results,
    default_state,
    default_unassigned_owner,
    load_state,
    record_result,
    save_state,
    should_process,
    touch_cycle,
    validate_bandeja,
    validate_bandejas,
    validate_equipo,
    validate_schedule,
    within_schedule,
)

VALID_URL = "https://example.lightning.force.com/lightning/r/Report/00O123/view"
LEAD_ID = "00Q000000000001AAA"


def bandeja(code="AR", **overrides):
    payload = {"code": code, "enabled": True, "url": VALID_URL}
    payload.update(overrides)
    return payload


class BandejaValidationTests(unittest.TestCase):
    def test_valid_bandeja_defaults(self):
        result = validate_bandeja(bandeja("CO"))
        self.assertEqual(result["code"], "CO")
        self.assertEqual(result["unassigned_owner"], "CO_LEAD_QUALIF")
        self.assertEqual(result["expected_status"], "Nuevo")
        self.assertTrue(result["enabled"])

    def test_custom_owner_and_status(self):
        result = validate_bandeja(bandeja("MX", unassigned_owner="MX_OTRA_COLA", expected_status="Abierto"))
        self.assertEqual(result["unassigned_owner"], "MX_OTRA_COLA")
        self.assertEqual(result["expected_status"], "Abierto")

    def test_rejects_unknown_code(self):
        with self.assertRaises(ValueError):
            validate_bandeja(bandeja("BR"))

    def test_rejects_non_lightning_url(self):
        for bad in ("http://insecure/x", "https://example.com/otra/pagina", "", "no-url"):
            with self.assertRaises(ValueError, msg=bad):
                validate_bandeja(bandeja(url=bad))

    def test_disabled_bandeja_allows_empty_url(self):
        # Quien solo opera Argentina deja CO/MX deshabilitadas y sin URL.
        result = validate_bandeja(bandeja("CO", enabled=False, url=""))
        self.assertFalse(result["enabled"])
        self.assertEqual(result["url"], "")

    def test_disabled_bandeja_still_validates_provided_url(self):
        with self.assertRaises(ValueError):
            validate_bandeja(bandeja("CO", enabled=False, url="http://insegura"))

    def test_rejects_duplicate_codes(self):
        with self.assertRaises(ValueError):
            validate_bandejas([bandeja("AR"), bandeja("AR", url=VALID_URL + "?x=1")])

    def test_disabled_bandeja_keeps_url(self):
        result = validate_bandeja(bandeja(enabled=False))
        self.assertFalse(result["enabled"])
        self.assertEqual(result["url"], VALID_URL)

    def test_tz_offset_defaults_per_country(self):
        """El ajuste horario documenta los intentos en la hora del país del
        lead, no la local del bot (Colombia): AR +2, CO 0, MX -1."""
        self.assertEqual(validate_bandeja(bandeja("AR"))["tz_offset"], 2)
        self.assertEqual(validate_bandeja(bandeja("CO"))["tz_offset"], 0)
        self.assertEqual(validate_bandeja(bandeja("MX"))["tz_offset"], -1)

    def test_tz_offset_custom_and_validated(self):
        self.assertEqual(validate_bandeja(bandeja("AR", tz_offset=3))["tz_offset"], 3)
        self.assertEqual(validate_bandeja(bandeja("AR", tz_offset="-2"))["tz_offset"], -2)
        for bad in ("abc", 99, -13):
            with self.assertRaises(ValueError, msg=bad):
                validate_bandeja(bandeja("AR", tz_offset=bad))


class ScheduleValidationTests(unittest.TestCase):
    def test_empty_schedule_allowed(self):
        self.assertEqual(validate_schedule(None), [])
        self.assertEqual(validate_schedule([]), [])

    def test_valid_slots_sorted(self):
        result = validate_schedule([{"start": "14:00", "end": "18:00"}, {"start": "08:00", "end": "12:00"}])
        self.assertEqual(
            result,
            [
                {"start": "08:00", "end": "12:00", "bandejas": []},
                {"start": "14:00", "end": "18:00", "bandejas": []},
            ],
        )

    def test_slots_keep_bandejas(self):
        result = validate_schedule(
            [{"start": "08:00", "end": "12:00", "bandejas": ["AR", "MX", "AR"]}]
        )
        self.assertEqual(result, [{"start": "08:00", "end": "12:00", "bandejas": ["AR", "MX"]}])

    def test_overlap_same_bandeja_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule(
                [
                    {"start": "08:00", "end": "13:00", "bandejas": ["AR"]},
                    {"start": "12:00", "end": "18:00", "bandejas": ["AR"]},
                ]
            )

    def test_overlap_distinct_bandejas_allowed(self):
        result = validate_schedule(
            [
                {"start": "10:00", "end": "12:00", "bandejas": ["AR"]},
                {"start": "11:00", "end": "13:00", "bandejas": ["CO"]},
            ]
        )
        self.assertEqual(len(result), 2)

    def test_overlap_with_todas_rejected(self):
        # Una franja sin bandejas cubre todas: pisa cualquier franja que
        # la solape, tenga o no bandejas propias.
        with self.assertRaises(ValueError):
            validate_schedule(
                [
                    {"start": "08:00", "end": "13:00"},
                    {"start": "12:00", "end": "18:00", "bandejas": ["AR"]},
                ]
            )

    def test_rejects_bad_bandeja_payload(self):
        with self.assertRaises(ValueError):
            validate_schedule([{"start": "08:00", "end": "12:00", "bandejas": "AR"}])
        with self.assertRaises(ValueError):
            validate_schedule([{"start": "08:00", "end": "12:00", "bandejas": [""]}])

    def test_rejects_bad_format(self):
        for bad in ("8:00", "24:00", "aa:bb", "12:60", ""):
            with self.assertRaises(ValueError, msg=bad):
                validate_schedule([{"start": bad, "end": "20:00"}])

    def test_rejects_inverted_slot(self):
        with self.assertRaises(ValueError):
            validate_schedule([{"start": "18:00", "end": "09:00"}])

    def test_rejects_overlap(self):
        with self.assertRaises(ValueError):
            validate_schedule([{"start": "08:00", "end": "13:00"}, {"start": "12:00", "end": "18:00"}])

    def test_adjacent_slots_allowed(self):
        result = validate_schedule([{"start": "08:00", "end": "12:00"}, {"start": "12:00", "end": "18:00"}])
        self.assertEqual(len(result), 2)


class WithinScheduleTests(unittest.TestCase):
    def test_empty_schedule_always_within(self):
        self.assertTrue(within_schedule([], datetime(2026, 10, 8, 3, 0)))

    def test_inside_and_outside_slot(self):
        slots = [{"start": "08:00", "end": "20:00"}]
        self.assertTrue(within_schedule(slots, datetime(2026, 10, 8, 10, 0)))
        self.assertFalse(within_schedule(slots, datetime(2026, 10, 8, 22, 15)))
        self.assertTrue(within_schedule(slots, datetime(2026, 10, 8, 20, 0)))
        self.assertFalse(within_schedule(slots, datetime(2026, 10, 8, 20, 1)))
        self.assertTrue(within_schedule(slots, datetime(2026, 10, 8, 8, 0)))

    def test_end_minute_is_inclusive(self):
        """El usuario escribe 12:00–13:59 queriendo cubrir 13:59
        inclusive; 14:00 ya queda fuera."""
        slots = [{"start": "12:00", "end": "13:59"}]
        self.assertTrue(within_schedule(slots, datetime(2026, 10, 8, 13, 59)))
        self.assertFalse(within_schedule(slots, datetime(2026, 10, 8, 14, 0)))

    def test_second_slot_counts(self):
        slots = [{"start": "08:00", "end": "12:00"}, {"start": "14:00", "end": "18:00"}]
        self.assertTrue(within_schedule(slots, datetime(2026, 10, 8, 15, 0)))
        self.assertFalse(within_schedule(slots, datetime(2026, 10, 8, 13, 0)))

    def test_bandeja_filter(self):
        slots = [{"start": "08:00", "end": "20:00", "bandejas": ["AR"]}]
        moment = datetime(2026, 10, 8, 10, 0)
        self.assertTrue(within_schedule(slots, moment, bandeja="AR"))
        self.assertFalse(within_schedule(slots, moment, bandeja="MX"))
        # Sin filtro sigue comportándose como antes.
        self.assertTrue(within_schedule(slots, moment))

    def test_bandeja_set_and_todas(self):
        slots = [
            {"start": "08:00", "end": "12:00", "bandejas": ["AR"]},
            {"start": "14:00", "end": "18:00"},  # sin bandejas = todas
        ]
        # Franja con otra bandeja no cuenta; la "todas" sí.
        self.assertFalse(within_schedule(slots, datetime(2026, 10, 8, 10, 0), bandeja="MX"))
        self.assertTrue(within_schedule(slots, datetime(2026, 10, 8, 15, 0), bandeja="MX"))
        # Conjunto de códigos: basta que una franja cubra alguno.
        self.assertTrue(within_schedule(slots, datetime(2026, 10, 8, 10, 0), bandeja={"AR", "MX"}))


class MonitorStateTests(unittest.TestCase):
    def test_missing_file_returns_default(self):
        with TemporaryDirectory() as tmp:
            state = load_state(Path(tmp) / "monitor_state.json")
        self.assertFalse(state["enabled"])
        self.assertEqual(state["results"], [])

    def test_broken_json_returns_default(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "monitor_state.json"
            path.write_text("{roto", encoding="utf-8")
            state = load_state(path)
        self.assertEqual(state, default_state())

    def test_roundtrip(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "monitor_state.json"
            state = default_state()
            state["enabled"] = True
            state["bandejas"] = validate_bandejas([bandeja("AR")])
            state["schedule"] = validate_schedule([{"start": "08:00", "end": "20:00"}])
            record_result(state, LEAD_ID, "AR", STATUS_TOMADO, {"nombre": "x"})
            save_state(path, state)
            loaded = load_state(path)
        self.assertTrue(loaded["enabled"])
        self.assertEqual(loaded["bandejas"][0]["code"], "AR")
        self.assertEqual(loaded["results"][0]["status"], STATUS_TOMADO)
        self.assertEqual(loaded["results"][0]["details"], {"nombre": "x"})

    def test_invalid_bandeja_on_disk_dropped_but_results_kept(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "monitor_state.json"
            path.write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "bandejas": [{"code": "XX", "url": "ftp://x"}],
                        "results": [{"lead_id": LEAD_ID, "status": STATUS_TOMADO}],
                    }
                ),
                encoding="utf-8",
            )
            state = load_state(path)
        self.assertEqual(state["bandejas"], [])
        self.assertEqual(len(state["results"]), 1)


class ResultTrackingTests(unittest.TestCase):
    def test_terminal_statuses_not_reprocessed(self):
        state = default_state()
        for status in (STATUS_TOMADO, STATUS_TOMADO_POR_OTRO):
            record_result(state, LEAD_ID, "AR", status)
            self.assertFalse(should_process(state, LEAD_ID), status)

    def test_no_verificado_allows_single_retry(self):
        # Pick Up clicado pero sin cambio de propietario observado: el
        # reintento del ciclo siguiente relee el propietario antes de
        # clicar — no es un clic a ciegas.
        state = default_state()
        record_result(state, LEAD_ID, "AR", STATUS_NO_VERIFICADO)
        self.assertTrue(should_process(state, LEAD_ID))
        record_result(state, LEAD_ID, "AR", STATUS_NO_VERIFICADO)
        self.assertFalse(should_process(state, LEAD_ID))

    def test_detected_status_always_reprocessed(self):
        # `detectado` es el listado del modo prueba: al apagarlo el lead debe
        # poder tomarse, así que nunca es terminal.
        state = default_state()
        record_result(state, LEAD_ID, "AR", STATUS_DETECTADO)
        self.assertTrue(should_process(state, LEAD_ID))
        record_result(state, LEAD_ID, "AR", STATUS_DETECTADO)
        self.assertTrue(should_process(state, LEAD_ID))

    def test_error_allows_single_retry(self):
        state = default_state()
        record_result(state, LEAD_ID, "AR", STATUS_ERROR)
        self.assertTrue(should_process(state, LEAD_ID))
        record_result(state, LEAD_ID, "AR", STATUS_ERROR)
        self.assertFalse(should_process(state, LEAD_ID))
        self.assertEqual(state["results"][0]["attempts"], MAX_ATTEMPTS)

    def test_new_result_replaces_previous(self):
        state = default_state()
        record_result(state, LEAD_ID, "AR", STATUS_ERROR)
        record_result(state, LEAD_ID, "AR", STATUS_TOMADO)
        self.assertEqual(len(state["results"]), 1)
        self.assertEqual(state["results"][0]["status"], STATUS_TOMADO)

    def test_clear_results_preserves_monitor_configuration(self):
        state = default_state()
        state["enabled"] = True
        state["solo_listar"] = True
        state["bandejas"] = validate_bandejas([bandeja("AR")])
        state["schedule"] = validate_schedule([{"start": "08:00", "end": "20:00"}])
        state["last_cycle_at"] = "2026-10-10T14:24:09+00:00"
        state["paused_reason"] = "fuera_de_horario"
        record_result(state, LEAD_ID, "AR", STATUS_DETECTADO)

        before = {key: value for key, value in state.items() if key != "results"}
        removed = clear_results(state)

        self.assertEqual(removed, 1)
        self.assertEqual(state["results"], [])
        self.assertEqual({key: value for key, value in state.items() if key != "results"}, before)

    def test_record_result_keeps_extra_fields(self):
        """asignado_a queda en la entrada para verificar a quién se asignó."""
        state = default_state()
        entry = record_result(state, LEAD_ID, "AR", STATUS_TOMADO, {"nombre": "x"}, extra={"asignado_a": "Maria Perez"})
        self.assertEqual(entry["asignado_a"], "Maria Perez")
        self.assertEqual(state["results"][0]["asignado_a"], "Maria Perez")

    def test_results_capped(self):
        state = default_state()
        for index in range(MAX_RESULTS + 10):
            record_result(state, f"{index:015d}", "AR", STATUS_TOMADO)
        self.assertEqual(len(state["results"]), MAX_RESULTS)
        self.assertEqual(state["results"][-1]["lead_id"], f"{MAX_RESULTS + 9:015d}")

    def test_rejects_invalid_lead_id_and_status(self):
        state = default_state()
        with self.assertRaises(ValueError):
            record_result(state, "no-es-id", "AR", STATUS_TOMADO)
        with self.assertRaises(ValueError):
            record_result(state, LEAD_ID, "AR", "inventado")

    def test_touch_cycle_records_pause(self):
        state = default_state()
        touch_cycle(state, "fuera_de_horario")
        self.assertEqual(state["paused_reason"], "fuera_de_horario")
        self.assertIsNotNone(state["last_cycle_at"])

    def test_solo_listar_roundtrip(self):
        with TemporaryDirectory() as tmp:
            state = default_state()
            state["solo_listar"] = True
            save_state(Path(tmp) / "s.json", state)
            self.assertTrue(load_state(Path(tmp) / "s.json")["solo_listar"])
        self.assertFalse(default_state()["solo_listar"])


class ValidateEquipoTests(unittest.TestCase):
    """Franjas del equipo con bandejas: solape solo prohibido en la misma
    bandeja; bandejas distintas pueden cruzarse en el tiempo."""

    def test_franjas_conservan_bandejas(self):
        equipo = validate_equipo(
            [
                {
                    "nombre": "Roger",
                    "franjas": [
                        {"start": "10:00", "end": "12:00", "bandejas": ["AR"]},
                        {"start": "11:00", "end": "13:00", "bandejas": ["CO"]},
                    ],
                }
            ]
        )
        self.assertEqual(equipo[0]["franjas"][0]["bandejas"], ["AR"])
        self.assertEqual(equipo[0]["franjas"][1]["bandejas"], ["CO"])

    def test_franja_sin_bandejas_es_tolerada_pero_inerte(self):
        # Franjas viejas sin el campo: no cubren nada pero no rompen la carga.
        equipo = validate_equipo([{"nombre": "Ana", "franjas": [{"start": "09:00", "end": "10:00"}]}])
        self.assertEqual(equipo[0]["franjas"][0]["bandejas"], [])

    def test_solape_misma_bandeja_rechazado(self):
        with self.assertRaises(ValueError):
            validate_equipo(
                [
                    {"nombre": "Ana", "franjas": [{"start": "10:00", "end": "12:00", "bandejas": ["AR"]}]},
                    {"nombre": "Beto", "franjas": [{"start": "11:00", "end": "13:00", "bandejas": ["AR"]}]},
                ]
            )

    def test_solape_misma_bandeja_misma_persona_rechazado(self):
        with self.assertRaises(ValueError):
            validate_equipo(
                [
                    {
                        "nombre": "Ana",
                        "franjas": [
                            {"start": "10:00", "end": "12:00", "bandejas": ["AR"]},
                            {"start": "11:30", "end": "13:00", "bandejas": ["AR"]},
                        ],
                    }
                ]
            )

    def test_solape_en_bandejas_distintas_es_legal(self):
        equipo = validate_equipo(
            [
                {"nombre": "Roger", "franjas": [{"start": "10:00", "end": "12:00", "bandejas": ["AR"]}]},
                {"nombre": "Ana", "franjas": [{"start": "11:00", "end": "13:00", "bandejas": ["MX"]}]},
            ]
        )
        self.assertEqual(len(equipo), 2)

    def test_franja_multi_bandeja_valida(self):
        equipo = validate_equipo(
            [{"nombre": "Ana", "franjas": [{"start": "09:00", "end": "13:00", "bandejas": ["AR", "MX"]}]}]
        )
        self.assertEqual(equipo[0]["franjas"][0]["bandejas"], ["AR", "MX"])


class PrivacyTests(unittest.TestCase):
    def test_default_owner_derivation(self):
        self.assertEqual(default_unassigned_owner("CO"), "CO_LEAD_QUALIF")


if __name__ == "__main__":
    unittest.main()
