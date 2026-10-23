import unittest
from unittest.mock import patch

from lead_monitor import (
    owner_is_unassigned,
    run_bandeja_cycle,
    run_cycle,
    status_is_expected,
    take_lead,
)
from monitor_store import (
    STATUS_ERROR,
    STATUS_NO_VERIFICADO,
    STATUS_TOMADO,
    STATUS_TOMADO_POR_OTRO,
    default_state,
    validate_bandejas,
)
from report_reader import VisibleLead

LEAD_ID = "00Q000000000001AAA"
LEAD_ID_B = "00Q000000000002AAA"
VALID_URL = "https://example.lightning.force.com/lightning/r/Report/00O123/view"
CONFIG = {"salesforce_url": "https://example.lightning.force.com", "lead_list_fields": {}}


def bandeja(code="AR", **overrides):
    payload = {
        "code": code,
        "enabled": True,
        "url": VALID_URL,
        "unassigned_owner": "AR_LEAD_QUALIF",
        "expected_status": "Nuevo",
    }
    payload.update(overrides)
    return payload


def lead(lead_id=LEAD_ID, estado="Nuevo", **details):
    return VisibleLead(
        lead_id=lead_id,
        created_at="8/10/2026 10:00",
        details={"estado_candidato": estado, **details},
    )


class PredicatesTests(unittest.TestCase):
    def test_owner_match_ignores_whitespace_and_case(self):
        self.assertTrue(owner_is_unassigned(" AR_LEAD_QUALIF ", "AR_LEAD_QUALIF"))
        self.assertTrue(owner_is_unassigned("ar_lead_qualif", "AR_LEAD_QUALIF"))
        self.assertFalse(owner_is_unassigned("Maria Perez", "AR_LEAD_QUALIF"))

    def test_expected_status_normalizes(self):
        self.assertTrue(status_is_expected(" Nuevo ", "Nuevo"))
        self.assertTrue(status_is_expected("NUEVO", "Nuevo"))
        self.assertFalse(status_is_expected("En curso", "Nuevo"))


class TakeLeadTests(unittest.TestCase):
    def test_owner_text_strips_vista_previa(self):
        """El lookup de Propietario arrastra el enlace 'Vista previa'."""
        from lead_monitor import read_record_owner

        with patch("lead_monitor.find_field_text", return_value="Jose Manuel de la Colina Vista previa"):
            self.assertEqual(read_record_owner(object()), "Jose Manuel de la Colina")
        with patch("lead_monitor.find_field_text", return_value="Maria Perez\nVista previa"):
            self.assertEqual(read_record_owner(object()), "Maria Perez")

    def test_pickup_verified(self):
        owners = iter(["AR_LEAD_QUALIF", "Maria Perez"])
        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", side_effect=lambda *_: next(owners)),
            patch("lead_monitor.read_record_owner", return_value="Maria Perez"),
            patch("lead_monitor.press_pick_up", return_value="clicked"),
            patch("lead_monitor.finalize_pick_up", return_value=("panel_guardado/marca_ok", "")) as finalize,
        ):
            status, owner, _fin, _diag = take_lead(object(), CONFIG, bandeja(), LEAD_ID, 5)
        self.assertEqual(status, STATUS_TOMADO)
        self.assertEqual(owner, "Maria Perez")
        finalize.assert_called_once()

    def test_owner_already_changed(self):
        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value="Maria Perez"),
            patch("lead_monitor.press_pick_up") as pickup,
        ):
            status, _owner, _fin, _diag = take_lead(object(), CONFIG, bandeja(), LEAD_ID, 5)
        self.assertEqual(status, STATUS_TOMADO_POR_OTRO)
        pickup.assert_not_called()

    def test_owner_field_never_appears(self):
        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value=""),
            patch("lead_monitor.press_pick_up") as pickup,
        ):
            status, _owner, _fin, _diag = take_lead(object(), CONFIG, bandeja(), LEAD_ID, 5)
        self.assertEqual(status, STATUS_ERROR)
        pickup.assert_not_called()

    def test_button_missing(self):
        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value="AR_LEAD_QUALIF"),
            patch("lead_monitor.press_pick_up", return_value="not_found"),
        ):
            status, _owner, _fin, _diag = take_lead(object(), CONFIG, bandeja(), LEAD_ID, 5)
        self.assertEqual(status, STATUS_ERROR)

    def test_button_ambiguous(self):
        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value="AR_LEAD_QUALIF"),
            patch("lead_monitor.press_pick_up", return_value="ambiguous"),
        ):
            status, _owner, _fin, _diag = take_lead(object(), CONFIG, bandeja(), LEAD_ID, 5)
        self.assertEqual(status, STATUS_ERROR)

    def test_owner_unchanged_after_click_never_retries(self):
        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value="AR_LEAD_QUALIF"),
            patch("lead_monitor.read_record_owner", return_value="AR_LEAD_QUALIF"),
            patch("lead_monitor._reread_owner_after_refresh", return_value="AR_LEAD_QUALIF"),
            patch("lead_monitor.press_pick_up", return_value="clicked") as pickup,
            patch("lead_monitor.OWNER_VERIFY_TIMEOUT_SECONDS", 0.1),
            patch("lead_monitor.POLL_SECONDS", 0.01),
        ):
            status, _owner, _fin, _diag = take_lead(object(), CONFIG, bandeja(), LEAD_ID, 5)
        self.assertEqual(status, STATUS_NO_VERIFICADO)
        self.assertEqual(pickup.call_count, 1)

    def test_slow_save_recovered_by_refresh_reread(self):
        """El clic funcionó pero el campo quedó viejo: la relectura tras
        refrescar confirma al usuario de la sesión → tomado + finalize."""
        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value="AR_LEAD_QUALIF"),
            patch("lead_monitor.read_record_owner", return_value="Maria Perez"),
            patch("lead_monitor.wait_owner_changed", return_value=False),
            patch("lead_monitor._reread_owner_after_refresh", return_value="Maria Perez"),
            patch("lead_monitor.press_pick_up", return_value="clicked"),
            patch("lead_monitor.finalize_pick_up", return_value=("sin_panel/marca_ok", "")) as finalize,
            patch("lead_monitor.OWNER_VERIFY_TIMEOUT_SECONDS", 0.1),
            patch("lead_monitor.POLL_SECONDS", 0.01),
        ):
            status, owner, _fin, _diag = take_lead(
                object(), CONFIG, bandeja(), LEAD_ID, 5, bot_owner="Maria Perez"
            )
        self.assertEqual(status, STATUS_TOMADO)
        self.assertEqual(owner, "Maria Perez")
        finalize.assert_called_once()

    def test_refresh_reread_other_owner_no_finalize(self):
        """Carrera ganada por otra persona: con bot_owner conocido, un
        propietario distinto es tomado_por_otro — sin marca ni WhatsApp."""
        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value="AR_LEAD_QUALIF"),
            patch("lead_monitor.read_record_owner", return_value="Pedro Gomez"),
            patch("lead_monitor.wait_owner_changed", return_value=False),
            patch("lead_monitor._reread_owner_after_refresh", return_value="Pedro Gomez"),
            patch("lead_monitor.press_pick_up", return_value="clicked"),
            patch("lead_monitor.finalize_pick_up") as finalize,
            patch("lead_monitor.OWNER_VERIFY_TIMEOUT_SECONDS", 0.1),
            patch("lead_monitor.POLL_SECONDS", 0.01),
        ):
            status, owner, _fin, _diag = take_lead(
                object(), CONFIG, bandeja(), LEAD_ID, 5, bot_owner="Maria Perez"
            )
        self.assertEqual(status, STATUS_TOMADO_POR_OTRO)
        self.assertEqual(owner, "Pedro Gomez")
        finalize.assert_not_called()


def _field_reads(*texts):
    """Iterador de respuestas de ``field_result_if_found`` para los tests."""
    return iter([{"found": True, "text": text} for text in texts])


def _sticky(texts):
    """Iterador que repite el último texto — la pasada de limpieza WhatsApp
    relee el campo una vez más y un iterador finito se agotaría."""
    import itertools

    return itertools.chain(texts, itertools.repeat(texts[-1]))


def _typed_text(element):
    """Texto del último ``send_keys`` — si hubo re-tipeo, el último es el
    que disparó la búsqueda."""
    return element.send_keys.call_args.args[0]


class FinalizePickUpTests(unittest.TestCase):
    def test_panel_found_saves_without_typing(self):
        """Panel presente: solo pulsa Save; nada se escribe en la sección."""
        from lead_monitor import PANEL_PRESENT_SCRIPT, PANEL_SAVE_CLICK_SCRIPT, finalize_pick_up

        executed = []
        responses = {
            PANEL_PRESENT_SCRIPT: "found",
            PANEL_SAVE_CLICK_SCRIPT: "clicked",
        }
        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=lambda _d, s, *a: executed.append(s) or responses[s]),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(_field_reads("Nota previa\nAsignado"))),
            patch("lead_monitor._read_other_information_value", return_value="Nota previa\nAsignado"),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.wait_for_lightning_ready"),
            patch("lead_monitor.time.sleep"),
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "panel_guardado/marca_presente")
        # Nada de buscar inputs ni send_keys: presencia → Save → listo.
        self.assertEqual(executed, [PANEL_PRESENT_SCRIPT, PANEL_SAVE_CLICK_SCRIPT])
        edit.assert_not_called()  # la marca ya quedó en Otra información

    def test_panel_save_then_marks_other_information(self):
        """Tras el Save del panel, 'Asignado' se garantiza en Otra información."""
        from lead_monitor import PANEL_PRESENT_SCRIPT, PANEL_SAVE_CLICK_SCRIPT, finalize_pick_up

        responses = {
            PANEL_PRESENT_SCRIPT: "found",
            PANEL_SAVE_CLICK_SCRIPT: "clicked",
        }
        reads = _field_reads("Nota previa", "Nota previa\nAsignado")
        persisted = iter(["Nota previa", "Nota previa\nAsignado"])
        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=lambda _d, s, *a: responses[s]),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form") as save,
            patch("lead_monitor.wait_for_lightning_ready"),
            patch("lead_monitor.time.sleep"),
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "panel_guardado/marca_ok")
        self.assertEqual(edit.call_args.args[1], "Nota previa\nAsignado")
        save.assert_called_once()

    def test_mark_lost_by_panel_reload_is_retried(self):
        """Si el repintado tras el Save del panel pierde la escritura, se
        reintenta una vez y queda confirmada."""
        from lead_monitor import finalize_pick_up

        # Dos escrituras: la segunda lectura sigue sin la marca (perdida por
        # el repintado); la verificación final la confirma.
        reads = _field_reads("Nota previa", "Nota previa")
        persisted = iter(["Nota previa", "Nota previa", "Nota previa\nAsignado"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form") as save,
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/marca_ok")
        self.assertEqual(edit.call_count, 2)
        self.assertEqual(save.call_count, 2)

    def test_icon_glued_edit_label_is_stripped(self):
        """Regresión: la etiqueta del lápiz llegó pegada a un glifo de ícono
        ("✎ Modificar Otra información") y el strip por igualdad exacta la
        dejaba pasar → se persistía dentro del valor."""
        from lead_monitor import finalize_pick_up

        reads = _field_reads("✏ Modificar Otra información", "Asignado")
        persisted = iter([None, "Asignado"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form"),
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/marca_ok")
        self.assertEqual(edit.call_args.args[1], "Asignado")

    def test_persisted_label_pollution_is_repaired(self):
        """Verificación pedida: si el valor YA guardado trae la etiqueta del
        lápiz (contaminado en una corrida previa), se reescribe limpio aunque
        la marca Asignado ya esté."""
        from lead_monitor import finalize_pick_up

        reads = _field_reads("Modificar Otra información\nAsignado", "Asignado")
        persisted = iter(["Modificar Otra información\nAsignado", "Asignado"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form") as save,
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/marca_ok")
        self.assertEqual(edit.call_args.args[1], "Asignado")  # queda limpio
        save.assert_called_once()

    def test_unrendered_field_is_not_blank(self):
        """Regresión del bug real: lectura "" por campo no renderizado no es
        un campo vacío — se espera el render y se escribe sobre el valor real."""
        from lead_monitor import finalize_pick_up

        reads = iter(
            [False, {"found": True, "text": "Contenido real"}, {"found": True, "text": "Contenido real\nAsignado"}]
        )
        persisted = iter(["Contenido real", "Contenido real\nAsignado"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.scroll_toward_other_information", return_value=False),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form") as save,
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/marca_ok")
        # Escribe sobre el contenido real, no sobre "": nunca pisa datos.
        self.assertEqual(edit.call_args.args[1], "Contenido real\nAsignado")
        save.assert_called_once()

    def test_field_absent_reports_campo_ausente(self):
        """Si el campo nunca se renderiza, no se escribe a ciegas y queda
        registrado como campo_ausente."""
        from lead_monitor import finalize_pick_up

        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.FIELD_RENDER_WAIT_SECONDS", 0.02),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", return_value=False),
            patch("lead_monitor.scroll_toward_other_information", return_value=False),
            patch("lead_monitor.prepare_other_information") as edit,
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/campo_ausente")
        edit.assert_not_called()

    def test_mark_unconfirmed_after_two_writes(self):
        """Dos escrituras sin confirmar la marca: se reporta en el outcome."""
        from lead_monitor import finalize_pick_up

        reads = _field_reads("Nota previa", "Nota previa", "Nota previa")
        persisted = iter(["Nota previa", "Nota previa", "Nota previa"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form") as save,
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/marca_no_confirmada")
        self.assertEqual(edit.call_count, 2)
        self.assertEqual(save.call_count, 2)

    def test_mark_error_is_reported_not_swallowed(self):
        """Un fallo al editar queda en el outcome en vez de perderse en un
        ``except`` silencioso."""
        from selenium.common.exceptions import TimeoutException

        from lead_monitor import finalize_pick_up

        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.field_result_if_found", return_value={"found": True, "text": "Nota previa"}),
            patch("lead_monitor.prepare_other_information", side_effect=TimeoutException("boom")),
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/marca_error:editar:TimeoutException")

    def test_late_panel_is_saved_after_mark(self):
        """El panel puede renderizar pasada la ventana inicial (bajo carga):
        un chequeo tardío tras la marca lo detecta y lo guarda igual."""
        from lead_monitor import (
            PANEL_PRESENT_SCRIPT,
            PANEL_SAVE_CLICK_SCRIPT,
            finalize_pick_up,
        )

        # Determinístico: el panel solo "aparece" después de la fase de
        # marca — así la ventana inicial lo pierde y el chequeo tardío lo
        # halla, sin depender de cuántas veces itera cada loop.
        mark_phase_done = {"value": False}

        def read_value(_driver):
            mark_phase_done["value"] = True
            return "Asignado"

        def fake_exec(_driver, script, *args):
            if script is PANEL_PRESENT_SCRIPT:
                return "found" if mark_phase_done["value"] else "missing"
            if script is PANEL_SAVE_CLICK_SCRIPT:
                return "clicked"
            return []  # PANEL_DIAGNOSTIC_SCRIPT

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=fake_exec),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.001),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", return_value={"found": True, "text": "Asignado"}),
            patch("lead_monitor._read_other_information_value", side_effect=read_value),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.wait_for_lightning_ready"),
            patch("lead_monitor.time.sleep"),
        ):
            outcome, diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "panel_tardio_guardado/marca_presente")
        self.assertEqual(diag, "")
        edit.assert_not_called()

    def test_missing_panel_returns_dom_diagnostics(self):
        """Si el panel nunca se detecta, el diagnóstico devuelve los paneles
        visibles y la cadena DOM de los botones Save/SendEmail — esa firma
        revela el contenedor real para ajustar la detección."""
        from lead_monitor import PANEL_DIAGNOSTIC_SCRIPT, finalize_pick_up

        chains = [
            "panel:estatus de la llamada",
            "btn:save < button.slds < lightning-modal{fixed}",
        ]

        def fake_exec(_driver, script, *args):
            if script is PANEL_DIAGNOSTIC_SCRIPT:
                return chains
            return "missing"

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=fake_exec),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", return_value={"found": True, "text": "Asignado"}),
            patch("lead_monitor._read_other_information_value", return_value="Asignado"),
        ):
            outcome, diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/marca_presente")
        self.assertEqual(diag, "; ".join(chains))

    def test_panel_in_other_tab_is_saved(self):
        """En Service Console el panel puede renderizar en otro handle
        (subtab/ventana de utilidad): se busca en todas las pestañas, se
        guarda ahí y se vuelve al handle original."""
        from types import SimpleNamespace

        from lead_monitor import (
            PANEL_PRESENT_SCRIPT,
            PANEL_SAVE_CLICK_SCRIPT,
            finalize_pick_up,
        )

        driver = SimpleNamespace(
            current_window_handle="main",
            window_handles=["main", "consola"],
        )
        driver.switch_to = SimpleNamespace(
            window=lambda handle: setattr(driver, "current_window_handle", handle)
        )

        def fake_exec(drv, script, *args):
            if script is PANEL_PRESENT_SCRIPT:
                # El panel solo existe en la otra pestaña.
                return "found" if drv.current_window_handle == "consola" else "missing"
            if script is PANEL_SAVE_CLICK_SCRIPT:
                return "clicked"
            return []  # PANEL_DIAGNOSTIC_SCRIPT

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=fake_exec),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", return_value={"found": True, "text": "Asignado"}),
            patch("lead_monitor._read_other_information_value", return_value="Asignado"),
            patch("lead_monitor.time.sleep"),
        ):
            outcome, diag = finalize_pick_up(driver, 5)
        self.assertEqual(outcome, "panel_otra_tab_guardado/marca_presente")
        self.assertEqual(driver.current_window_handle, "main")  # restaurado

    def test_missing_panel_still_marks_other_information(self):
        """Sin panel Contact Client, 'Asignado' se escribe editando el campo."""
        from lead_monitor import finalize_pick_up

        reads = _field_reads("Nota previa", "Nota previa\nAsignado")
        persisted = iter(["Nota previa", "Nota previa\nAsignado"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form") as save,
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/marca_ok")
        edit.assert_called_once()
        self.assertIn("Asignado", edit.call_args.args[1])
        self.assertIn("Nota previa", edit.call_args.args[1])  # append, no pisa
        save.assert_called_once()

    def test_edit_button_label_is_never_written_into_the_field(self):
        """La lectura arrastra "Modificar Otra información": no debe quedar
        dentro del valor guardado (bug reportado en el lead real)."""
        from lead_monitor import finalize_pick_up

        reads = _field_reads("Modificar Otra información", "Asignado")
        persisted = iter([None, "Asignado"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form"),
        ):
            finalize_pick_up(object(), 5)
        self.assertEqual(edit.call_args.args[1], "Asignado")

    def test_edit_button_label_stripped_but_content_kept(self):
        from lead_monitor import finalize_pick_up

        reads = _field_reads("Modificar Otra información\nNota previa", "Nota previa\nAsignado")
        persisted = iter(["Nota previa", "Nota previa\nAsignado"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form"),
        ):
            finalize_pick_up(object(), 5)
        self.assertEqual(edit.call_args.args[1], "Nota previa\nAsignado")

    def test_panel_error_does_not_raise(self):
        """Un panel roto no degrada el `tomado` ya verificado."""
        from selenium.common.exceptions import WebDriverException

        from lead_monitor import finalize_pick_up

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=WebDriverException("boom")),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", return_value={"found": True, "text": "Asignado"}),
            patch("lead_monitor._read_other_information_value", return_value="Asignado"),
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "panel_error/marca_presente")


class WhatsappSendTests(unittest.TestCase):
    def test_preference_gate(self):
        """La rama aplica solo a AR + toggle + preferencia whatsapp."""
        from lead_monitor import _wants_whatsapp_send

        ar = {"code": "AR"}
        co = {"code": "CO"}
        details = {"preferencia_contacto": "vía whatsapp"}
        self.assertTrue(_wants_whatsapp_send(ar, details, True))
        self.assertTrue(_wants_whatsapp_send(ar, {"preferencia_contacto": "WhatsApp"}, True))
        self.assertFalse(_wants_whatsapp_send(ar, details, False))  # toggle apagado
        self.assertFalse(_wants_whatsapp_send(co, details, True))  # solo AR
        self.assertFalse(_wants_whatsapp_send(ar, {"preferencia_contacto": "llamada telefónica"}, True))
        self.assertFalse(_wants_whatsapp_send(ar, {}, True))
        self.assertFalse(_wants_whatsapp_send(ar, None, True))

    def test_attempt_line_format(self):
        from lead_monitor import _whatsapp_attempt_line

        line = _whatsapp_attempt_line()
        self.assertRegex(line, r"^1 INT Se envía WhatsApp \d{2}/\d{2}/\d{4} \d{2}:\d{2}$")

    def test_attempt_line_uses_country_offset(self):
        """El horario documentado es el del país del lead: con offset +2
        (AR) las 9:00 locales (CO) quedan escritas como 11:00."""
        from datetime import datetime

        from lead_monitor import _whatsapp_attempt_line

        fixed = datetime(2026, 10, 16, 9, 0)
        with patch("lead_monitor.datetime") as clock:
            clock.now.return_value = fixed
            self.assertEqual(_whatsapp_attempt_line(2), "1 INT Se envía WhatsApp 16/10/2026 11:00")
            self.assertEqual(_whatsapp_attempt_line(-1), "1 INT Se envía WhatsApp 16/10/2026 08:00")
            self.assertEqual(_whatsapp_attempt_line(0), "1 INT Se envía WhatsApp 16/10/2026 09:00")

    def test_whatsapp_lead_writes_attempt_and_sends(self):
        """Lead AR whatsapp: escribe la línea de intento (no Asignado) y
        envía — el outcome gana el tercer segmento wa_*."""
        from lead_monitor import finalize_pick_up

        reads = _field_reads("", "1 INT Se envía WhatsApp 14/10/2026 15:22", "1 INT Se envía WhatsApp 14/10/2026 15:22")
        persisted = _sticky(["", "1 INT Se envía WhatsApp 14/10/2026 15:22"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor._whatsapp_attempt_line", return_value="1 INT Se envía WhatsApp 14/10/2026 15:22"),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form"),
            patch("lead_monitor.send_whatsapp", return_value="wa_ok") as send,
        ):
            outcome, _diag = finalize_pick_up(object(), 5, whatsapp=True)
        self.assertEqual(outcome, "sin_panel/marca_ok/wa_ok")
        self.assertEqual(edit.call_args.args[1], "1 INT Se envía WhatsApp 14/10/2026 15:22")
        send.assert_called_once()

    def test_documented_lead_sends_without_rewriting(self):
        """Campo ya con `N INT` o Asignado: no duplica y el envío igual sale."""
        from lead_monitor import finalize_pick_up

        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", return_value={"found": True, "text": "2 INT Cliente contesta"}),
            patch("lead_monitor._read_other_information_value", return_value="2 INT Cliente contesta"),
            patch("lead_monitor.time.sleep"),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.send_whatsapp", return_value="wa_ok") as send,
        ):
            outcome, _diag = finalize_pick_up(object(), 5, whatsapp=True)
        self.assertEqual(outcome, "sin_panel/marca_presente/wa_ok")
        edit.assert_not_called()  # ya documentado: nunca se pisa
        send.assert_called_once()

    def test_non_whatsapp_lead_keeps_asignado_and_no_wa_segment(self):
        """whatsapp=False: comportamiento intacto, sin tercer segmento."""
        from lead_monitor import finalize_pick_up

        reads = _field_reads("", "Asignado")
        persisted = iter(["", "Asignado"])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form"),
            patch("lead_monitor.send_whatsapp") as send,
        ):
            outcome, _diag = finalize_pick_up(object(), 5, whatsapp=False)
        self.assertEqual(outcome, "sin_panel/marca_ok")
        self.assertEqual(edit.call_args.args[1], "Asignado")
        send.assert_not_called()

    def test_attempt_with_stray_asignado_is_cleaned(self):
        """El Save del panel (estatuto) o un flow pueden inyectar 'Asignado'
        tras la línea de intento — la rama WhatsApp lo elimina."""
        from lead_monitor import finalize_pick_up

        attempt = "1 INT Se envía WhatsApp 14/10/2026 15:22"
        reads = _field_reads(f"{attempt}\nAsignado", attempt, attempt)
        persisted = _sticky([f"{attempt}\nAsignado", attempt])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor._whatsapp_attempt_line", return_value=attempt),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form"),
            patch("lead_monitor.send_whatsapp", return_value="wa_ok"),
        ):
            outcome, _diag = finalize_pick_up(object(), 5, whatsapp=True)
        self.assertEqual(outcome, "sin_panel/marca_ok/wa_ok")
        self.assertEqual(edit.call_args.args[1], attempt)

    def test_whatsapp_lead_with_only_asignado_is_replaced(self):
        """Campo con solo 'Asignado' (toma previa o flow): se reemplaza por
        la línea de intento — la marca no convive con el intento."""
        from lead_monitor import finalize_pick_up

        attempt = "1 INT Se envía WhatsApp 14/10/2026 15:22"
        reads = _field_reads("Asignado", attempt, attempt)
        persisted = _sticky(["Asignado", attempt])
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(reads)),
            patch("lead_monitor._read_other_information_value", side_effect=lambda *_: next(persisted)),
            patch("lead_monitor._whatsapp_attempt_line", return_value=attempt),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.save_edit_form"),
            patch("lead_monitor.send_whatsapp", return_value="wa_ok"),
        ):
            outcome, _diag = finalize_pick_up(object(), 5, whatsapp=True)
        self.assertEqual(outcome, "sin_panel/marca_ok/wa_ok")
        self.assertEqual(edit.call_args.args[1], attempt)

    def test_send_whatsapp_confirms_and_closes_toast(self):
        from lead_monitor import (
            SEND_WHATSAPP_CLICK_SCRIPT,
            WA_TOAST_CLOSE_SCRIPT,
            WA_TOAST_PRESENT_SCRIPT,
            send_whatsapp,
        )

        executed = []
        responses = {
            SEND_WHATSAPP_CLICK_SCRIPT: "clicked",
            WA_TOAST_PRESENT_SCRIPT: "found",
            WA_TOAST_CLOSE_SCRIPT: "closed",
        }
        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=lambda _d, s, *a: executed.append(s) or responses[s]),
            patch("lead_monitor.time.sleep"),
        ):
            outcome = send_whatsapp(object())
        self.assertEqual(outcome, "wa_ok")
        self.assertEqual(executed, [SEND_WHATSAPP_CLICK_SCRIPT, WA_TOAST_PRESENT_SCRIPT, WA_TOAST_CLOSE_SCRIPT])

    def test_send_whatsapp_no_toast_never_retries(self):
        """Sin toast → wa_no_confirmado y el clic se hizo una sola vez
        (un segundo clic podría duplicar el mensaje)."""
        from lead_monitor import SEND_WHATSAPP_CLICK_SCRIPT, send_whatsapp

        clicks = []

        def fake_exec(_driver, script, *args):
            if script is SEND_WHATSAPP_CLICK_SCRIPT:
                clicks.append(script)
                return "clicked"
            return "missing"  # toast nunca aparece

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=fake_exec),
            patch("lead_monitor.WA_TOAST_WAIT_SECONDS", 0.02),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.time.sleep"),
        ):
            outcome = send_whatsapp(object())
        self.assertEqual(outcome, "wa_no_confirmado")
        self.assertEqual(len(clicks), 1)

    def test_send_whatsapp_button_missing(self):
        from lead_monitor import send_whatsapp

        with (
            patch("lead_monitor.execute_in_any_frame", return_value="sin_boton"),
            patch("lead_monitor.time.sleep"),
        ):
            outcome = send_whatsapp(object())
        self.assertEqual(outcome, "wa_sin_boton")


class RunBandejaCycleTests(unittest.TestCase):
    def _state(self):
        state = default_state()
        state["bandejas"] = validate_bandejas([bandeja()])
        # En producción el ciclo solo corre con turno vigente: la franja
        # propia de todo el día reproduce esa cobertura en los tests.
        state["schedule"] = [{"start": "00:00", "end": "23:59"}]
        return state

    def test_takes_visible_new_leads(self):
        state = self._state()
        leads = [lead(LEAD_ID), lead(LEAD_ID_B)]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(2, leads)),
            patch("lead_monitor.take_lead", return_value=(STATUS_TOMADO, "Maria Perez", "panel_guardado/marca_ok", "")) as take,
        ):
            events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        self.assertEqual(take.call_count, 2)
        self.assertEqual(len(events), 2)
        self.assertTrue(all(e["status"] == STATUS_TOMADO for e in events))
        self.assertEqual(len(state["results"]), 2)

    def test_skips_non_new_status(self):
        state = self._state()
        leads = [lead(LEAD_ID, estado="En curso")]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, leads)),
            patch("lead_monitor.take_lead") as take,
        ):
            events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        take.assert_not_called()
        self.assertEqual(events, [])

    def test_terminal_lead_not_reprocessed(self):
        state = self._state()
        leads = [lead(LEAD_ID)]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, leads)),
            patch("lead_monitor.take_lead", return_value=(STATUS_TOMADO, "Maria Perez", "panel_guardado/marca_ok", "")),
        ):
            run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
            events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        self.assertEqual(events, [])
        self.assertEqual(len(state["results"]), 1)

    def test_take_lead_failure_records_error(self):
        state = self._state()
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, [lead()])),
            patch("lead_monitor.take_lead", side_effect=ValueError("boom")),
        ):
            events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        self.assertEqual(events[0]["status"], STATUS_ERROR)

    def test_own_shift_disables_team_reassignment(self):
        """Dentro de la franja del monitor (usuario logueado) los leads son
        suyos: el equipo no se evalúa para reasignación."""
        state = self._state()
        state["schedule"] = [{"start": "00:00", "end": "23:59"}]
        state["equipo"] = [{"nombre": "Ana", "franjas": [{"start": "00:00", "end": "23:59"}]}]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, [lead()])),
            patch("lead_monitor.take_lead", return_value=(STATUS_TOMADO, "Maria Perez", "panel_guardado/marca_ok", "")) as take,
        ):
            run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        take.assert_called_once()
        self.assertIsNone(take.call_args.kwargs["equipo"])

    def test_team_shift_passes_equipo_to_take_lead(self):
        """Fuera de la franja del monitor, el equipo activo se pasa a la
        toma para que el lead se reasigne a la persona en turno."""
        state = self._state()
        state["schedule"] = []
        equipo = [{"nombre": "Ana", "franjas": [{"start": "00:00", "end": "23:59", "bandejas": ["AR"]}]}]
        state["equipo"] = equipo
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, [lead()])),
            patch("lead_monitor.take_lead", return_value=(STATUS_TOMADO, "Ana", "sin_panel/sin_comentario/reasignado", "")) as take,
        ):
            run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        take.assert_called_once()
        self.assertEqual(take.call_args.kwargs["equipo"], equipo)

    def test_bandeja_sin_cobertura_no_toma_el_lead(self):
        """La franja de equipo vigente es de OTRA bandeja (AR activa, lead
        MX): el lead queda detectado "sin cobertura" — nunca se toma ni se
        reasigna a quien no la cubre."""
        state = self._state()
        state["schedule"] = []
        state["equipo"] = [
            {"nombre": "Andres Antelo", "franjas": [{"start": "00:00", "end": "23:59", "bandejas": ["AR"]}]}
        ]
        mx_bandeja = bandeja("MX")
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, [lead()])),
            patch("lead_monitor.take_lead") as take,
        ):
            events = run_bandeja_cycle(object(), CONFIG, mx_bandeja, state, 5)
        take.assert_not_called()
        self.assertEqual(events[0]["status"], "detectado")
        self.assertEqual(events[0]["entry"]["motivo"], "sin_cobertura")

    def test_franja_multi_bandeja_cubre_ambas(self):
        """Una franja con varias bandejas habilita la toma en cualquiera."""
        state = self._state()
        state["schedule"] = []
        state["equipo"] = [
            {"nombre": "Ana", "franjas": [{"start": "00:00", "end": "23:59", "bandejas": ["AR", "MX"]}]}
        ]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, [lead()])),
            patch("lead_monitor.take_lead", return_value=(STATUS_TOMADO, "Ana", "x/reasignado", "")) as take,
        ):
            run_bandeja_cycle(object(), CONFIG, bandeja("MX"), state, 5)
        take.assert_called_once()

    def test_session_lost_event(self):
        state = self._state()
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=True),
            patch("lead_monitor.read_bandeja_leads") as read,
        ):
            events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        read.assert_not_called()
        self.assertEqual(events[0]["type"], "session_lost")

    def test_dry_run_lists_without_taking(self):
        """Modo prueba: los QUALIF quedan listados como `detectado` sin Pick Up."""
        state = self._state()
        state["solo_listar"] = True
        leads = [lead(LEAD_ID), lead(LEAD_ID_B)]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(2, leads)),
            patch("lead_monitor.take_lead") as take,
        ):
            events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        take.assert_not_called()
        self.assertEqual(len(events), 2)
        self.assertTrue(all(e["status"] == "detectado" for e in events))

    def test_dry_run_lists_qualif_with_any_status(self):
        """Modo prueba: todos los QUALIF visibles se listan, no solo los
        'Nuevo' — el filtro de estado acota únicamente la toma real."""
        state = self._state()
        state["solo_listar"] = True
        leads = [lead(LEAD_ID, estado="En curso"), lead(LEAD_ID_B)]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(2, leads)),
            patch("lead_monitor.take_lead") as take,
        ):
            events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        take.assert_not_called()
        self.assertEqual(len(events), 2)
        self.assertTrue(all(e["status"] == "detectado" for e in events))

    def test_dry_run_detected_lead_is_taken_when_mode_is_off(self):
        """Al apagar el modo prueba, un lead ya listado vuelve a procesarse."""
        state = self._state()
        state["solo_listar"] = True
        leads = [lead(LEAD_ID)]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, leads)),
        ):
            with patch("lead_monitor.take_lead") as take:
                run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
            take.assert_not_called()
            state["solo_listar"] = False
            with patch("lead_monitor.take_lead", return_value=(STATUS_TOMADO, "Maria Perez", "panel_guardado/marca_ok", "")) as take:
                events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
            take.assert_called_once()
        self.assertEqual(events[0]["status"], STATUS_TOMADO)


class ReturnToQueueTests(unittest.TestCase):
    def test_full_flow_returns_devuelto(self):
        from lead_monitor import (
            OWNER_DIALOG_OPEN_SCRIPT,
            OWNER_SEARCH_INPUT_SCRIPT,
            OPEN_OWNER_SCOPE_SCRIPT,
            PICK_QUEUE_RESULT_SCRIPT,
            PICK_QUEUE_SCOPE_SCRIPT,
            return_lead_to_queue,
        )
        from lead_closure import MODAL_CONFIRM_SCRIPT, RECORD_ACTION_SCRIPT

        search_input = unittest.mock.Mock()
        responses = {
            RECORD_ACTION_SCRIPT: "clicked",
            OWNER_DIALOG_OPEN_SCRIPT: "open",
            OPEN_OWNER_SCOPE_SCRIPT: "clicked",
            PICK_QUEUE_SCOPE_SCRIPT: "clicked",
            OWNER_SEARCH_INPUT_SCRIPT: search_input,
            PICK_QUEUE_RESULT_SCRIPT: "clicked",
            MODAL_CONFIRM_SCRIPT: "clicked",
        }
        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value="JOSE PEREZ"),
            patch("lead_monitor.execute_in_any_frame", side_effect=lambda _d, s, *a: responses[s]),
            patch("lead_monitor.read_record_owner", return_value="AR_LEAD_QUALIF"),
        ):
            status = return_lead_to_queue(object(), CONFIG, LEAD_ID, "AR_LEAD_QUALIF", 5)
        self.assertEqual(status, "devuelto")
        self.assertEqual(_typed_text(search_input), "AR_LEAD_QUALIF")

    def test_already_in_queue_skips_dialog(self):
        from lead_monitor import return_lead_to_queue

        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value="AR_LEAD_QUALIF"),
            patch("lead_monitor.execute_in_any_frame") as ex,
        ):
            status = return_lead_to_queue(object(), CONFIG, LEAD_ID, "AR_LEAD_QUALIF", 5)
        self.assertEqual(status, "ya_en_cola")
        ex.assert_not_called()

    def test_missing_action_is_error(self):
        from lead_monitor import return_lead_to_queue

        with (
            patch("lead_monitor.open_record"),
            patch("lead_monitor.wait_record_owner", return_value="JOSE PEREZ"),
            patch("lead_monitor.execute_in_any_frame", return_value="not_found"),
        ):
            status = return_lead_to_queue(object(), CONFIG, LEAD_ID, "AR_LEAD_QUALIF", 0.1)
        self.assertEqual(status, STATUS_ERROR)


class ReassignOwnerTests(unittest.TestCase):
    def test_encargada_activa_por_franja(self):
        from datetime import datetime

        from lead_monitor import _encargada_activa

        equipo = [
            {"nombre": "Ana", "franjas": [{"start": "09:00", "end": "14:00"}]},
            {"nombre": "Beto", "franjas": [{"start": "12:00", "end": "18:00"}]},
        ]
        self.assertEqual(_encargada_activa(equipo, datetime(2026, 10, 15, 10, 0))["nombre"], "Ana")
        # Solape entre personas: gana la primera de la lista.
        self.assertEqual(_encargada_activa(equipo, datetime(2026, 10, 15, 13, 0))["nombre"], "Ana")
        self.assertEqual(_encargada_activa(equipo, datetime(2026, 10, 15, 15, 0))["nombre"], "Beto")
        self.assertIsNone(_encargada_activa(equipo, datetime(2026, 10, 15, 20, 0)))
        self.assertIsNone(_encargada_activa([]))
        self.assertIsNone(_encargada_activa([{"nombre": "Ana", "franjas": []}]))

    def test_encargada_activa_filtra_por_bandeja(self):
        """La encargada solo vale para las bandejas que cubre su franja:
        franja AR no recibe leads MX (el bug de la reasignación cruzada)."""
        from datetime import datetime

        from lead_monitor import _encargada_activa

        equipo = [
            {"nombre": "Ana", "franjas": [{"start": "00:00", "end": "23:59", "bandejas": ["AR"]}]},
            {"nombre": "Beto", "franjas": [{"start": "00:00", "end": "23:59", "bandejas": ["AR", "MX"]}]},
            {"nombre": "Ceci", "franjas": [{"start": "00:00", "end": "23:59"}]},
        ]
        momento = datetime(2026, 10, 15, 10, 0)
        self.assertEqual(_encargada_activa(equipo, momento, bandeja="AR")["nombre"], "Ana")
        # MX salta a Beto: Ana no cubre MX y la franja de Ceci no tiene bandeja.
        self.assertEqual(_encargada_activa(equipo, momento, bandeja="MX")["nombre"], "Beto")
        self.assertIsNone(_encargada_activa(equipo, momento, bandeja="CO"))
        # Set de bandejas = "cualquiera de estas" (gate del ciclo).
        self.assertIsNotNone(_encargada_activa(equipo, momento, bandeja={"MX", "CO"}))

    def test_encargada_para_lead_salta_al_propio_usuario(self):
        from lead_monitor import _encargada_para_lead

        yo = {"nombre": "Jose Manuel de la Colina", "franjas": []}
        with patch("lead_monitor._encargada_activa", return_value=yo):
            self.assertIsNone(_encargada_para_lead([yo], "Jose Manuel de la Colina"))
        otra = {"nombre": "Micaela Caetano", "franjas": []}
        with patch("lead_monitor._encargada_activa", return_value=otra):
            self.assertIs(_encargada_para_lead([otra], "Jose Manuel de la Colina"), otra)
        with patch("lead_monitor._encargada_activa", return_value=None):
            self.assertIsNone(_encargada_para_lead([otra], "Jose Manuel de la Colina"))

    def test_reassign_owner_full_flow(self):
        from lead_closure import MODAL_CONFIRM_SCRIPT, RECORD_ACTION_SCRIPT
        from lead_monitor import (
            OWNER_DIALOG_OPEN_SCRIPT,
            OWNER_SEARCH_INPUT_SCRIPT,
            PICK_QUEUE_RESULT_SCRIPT,
            reassign_owner,
        )

        search_input = unittest.mock.Mock()
        responses = {
            RECORD_ACTION_SCRIPT: "clicked",
            OWNER_DIALOG_OPEN_SCRIPT: "open",
            OWNER_SEARCH_INPUT_SCRIPT: search_input,
            PICK_QUEUE_RESULT_SCRIPT: "clicked",
            MODAL_CONFIRM_SCRIPT: "clicked",
        }
        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=lambda _d, s, *a: responses[s]),
            patch("lead_monitor.read_record_owner", return_value="Micaela Caetano"),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertEqual(reassign_owner(object(), "Micaela Caetano", 5), "reasignado")
        self.assertEqual(_typed_text(search_input), "Micaela Caetano")

    def test_reassign_owner_waits_for_lookup_input(self):
        """El input del lookup se monta después del modal: si el primer
        sondeo devuelve None, se reintenta hasta que aparezca."""
        from lead_closure import MODAL_CONFIRM_SCRIPT, RECORD_ACTION_SCRIPT
        from lead_monitor import (
            OWNER_DIALOG_OPEN_SCRIPT,
            OWNER_SEARCH_INPUT_SCRIPT,
            PICK_QUEUE_RESULT_SCRIPT,
            reassign_owner,
        )

        search_input = unittest.mock.Mock()
        inputs = iter([None, search_input])
        responses = {
            RECORD_ACTION_SCRIPT: "clicked",
            OWNER_DIALOG_OPEN_SCRIPT: "open",
            OWNER_SEARCH_INPUT_SCRIPT: lambda: next(inputs),
            PICK_QUEUE_RESULT_SCRIPT: "clicked",
            MODAL_CONFIRM_SCRIPT: "clicked",
        }
        def fake_exec(_driver, script, *args):
            value = responses[script]
            return value() if callable(value) else value

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=fake_exec),
            patch("lead_monitor.read_record_owner", return_value="Micaela Caetano"),
            patch("lead_monitor.POLL_SECONDS", 0.001),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertEqual(reassign_owner(object(), "Micaela Caetano", 5), "reasignado")
        self.assertEqual(_typed_text(search_input), "Micaela Caetano")

    def test_reassign_owner_waits_for_confirm_button(self):
        """Tras elegir el registro el footer del modal tarda en re-renderizar
        el botón "Cambiar propietario": se sondea hasta que aparezca."""
        from lead_closure import MODAL_CONFIRM_SCRIPT, RECORD_ACTION_SCRIPT
        from lead_monitor import (
            OWNER_DIALOG_OPEN_SCRIPT,
            OWNER_SEARCH_INPUT_SCRIPT,
            PICK_QUEUE_RESULT_SCRIPT,
            reassign_owner,
        )

        search_input = unittest.mock.Mock()
        confirms = iter(["not_found", "not_found", "clicked"])
        responses = {
            RECORD_ACTION_SCRIPT: "clicked",
            OWNER_DIALOG_OPEN_SCRIPT: "open",
            OWNER_SEARCH_INPUT_SCRIPT: search_input,
            PICK_QUEUE_RESULT_SCRIPT: "clicked",
            MODAL_CONFIRM_SCRIPT: lambda: next(confirms),
        }
        def fake_exec(_driver, script, *args):
            value = responses[script]
            return value() if callable(value) else value

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=fake_exec),
            patch("lead_monitor.read_record_owner", return_value="Micaela Caetano"),
            patch("lead_monitor.POLL_SECONDS", 0.001),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertEqual(reassign_owner(object(), "Micaela Caetano", 5), "reasignado")

    def test_reassign_owner_modal_missing(self):
        from lead_monitor import reassign_owner

        with patch("lead_monitor.execute_in_any_frame", return_value="not_found"):
            self.assertEqual(reassign_owner(object(), "Micaela Caetano", 0.1), "reasignacion_error:modal")

    def test_reassign_owner_option_missing_dismisses(self):
        from lead_closure import MODAL_CONFIRM_SCRIPT, RECORD_ACTION_SCRIPT
        from lead_monitor import (
            OWNER_DIALOG_OPEN_SCRIPT,
            OWNER_SEARCH_INPUT_SCRIPT,
            PICK_QUEUE_RESULT_SCRIPT,
            reassign_owner,
        )

        responses = {
            RECORD_ACTION_SCRIPT: "clicked",
            OWNER_DIALOG_OPEN_SCRIPT: "open",
            OWNER_SEARCH_INPUT_SCRIPT: unittest.mock.Mock(),
            PICK_QUEUE_RESULT_SCRIPT: "not_found",
            MODAL_CONFIRM_SCRIPT: "clicked",  # el cancel del dismiss
        }
        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=lambda _d, s, *a: responses[s]),
            patch("lead_monitor.QUEUE_SEARCH_TIMEOUT_SECONDS", 0.01),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertEqual(reassign_owner(object(), "Inexistente", 5), "reasignacion_error:opcion")

    def test_reassign_owner_verify_fail(self):
        from lead_closure import MODAL_CONFIRM_SCRIPT, RECORD_ACTION_SCRIPT
        from lead_monitor import (
            OWNER_DIALOG_OPEN_SCRIPT,
            OWNER_SEARCH_INPUT_SCRIPT,
            PICK_QUEUE_RESULT_SCRIPT,
            reassign_owner,
        )

        responses = {
            RECORD_ACTION_SCRIPT: "clicked",
            OWNER_DIALOG_OPEN_SCRIPT: "open",
            OWNER_SEARCH_INPUT_SCRIPT: unittest.mock.Mock(),
            PICK_QUEUE_RESULT_SCRIPT: "clicked",
            MODAL_CONFIRM_SCRIPT: "clicked",
        }
        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=lambda _d, s, *a: responses[s]),
            patch("lead_monitor.read_record_owner", return_value="Jose Manuel de la Colina"),
            patch("lead_monitor.OWNER_VERIFY_TIMEOUT_SECONDS", 0.01),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertEqual(reassign_owner(object(), "Micaela Caetano", 5), "reasignacion_error:verificacion")

    def test_finalize_con_encargada_no_comenta_y_reasigna(self):
        """Lead con encargada distinta: sin comentario en Otra información
        (pendiente de definición), WhatsApp forzado a off aunque el flag
        venga en True, y segmento 'reasignado' al final del outcome."""
        from lead_monitor import finalize_pick_up

        encargada = {"nombre": "Micaela Caetano", "franjas": []}
        details = {"preferencia_contacto": "vía whatsapp"}
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.send_whatsapp") as send,
            patch("lead_monitor.reassign_owner", return_value="reasignado") as reassign,
        ):
            outcome, _diag = finalize_pick_up(object(), 5, whatsapp=True, encargada=encargada, details=details)
        self.assertEqual(outcome, "sin_panel/sin_comentario/reasignado")
        edit.assert_not_called()
        send.assert_not_called()
        reassign.assert_called_once_with(unittest.mock.ANY, "Micaela Caetano", 5)

    def test_reasignacion_mark_sale_de_la_preferencia_del_lead(self):
        """El método del comentario sale de preferencia_contacto del lead,
        no de la persona: whatsapp → Enviar Whatsapp, llamada/teléfono →
        Llamarlo, otro/vacío → Gestionarlo."""
        from lead_monitor import _reasignacion_mark

        self.assertEqual(_reasignacion_mark({"preferencia_contacto": "vía whatsapp"}), "Asignado - Enviar Whatsapp")
        self.assertEqual(
            _reasignacion_mark({"preferencia_contacto": "llamada telefónica"}), "Asignado - Llamarlo"
        )
        self.assertEqual(_reasignacion_mark({"preferencia_contacto": "correo"}), "Asignado - Gestionarlo")
        self.assertEqual(_reasignacion_mark({}), "Asignado - Gestionarlo")
        self.assertEqual(_reasignacion_mark(None), "Asignado - Gestionarlo")


class RunCycleTests(unittest.TestCase):
    def test_iterates_enabled_bandejas_only(self):
        state = default_state()
        state["bandejas"] = validate_bandejas([bandeja("AR"), bandeja("CO", enabled=False), bandeja("MX")])
        with patch("lead_monitor.run_bandeja_cycle", return_value=[]) as cycle:
            run_cycle(object(), CONFIG, state, 5)
        seen = [call.args[2]["code"] for call in cycle.call_args_list]
        self.assertEqual(seen, ["AR", "MX"])

    def test_failed_bandeja_does_not_stop_others(self):
        state = default_state()
        state["bandejas"] = validate_bandejas([bandeja("AR"), bandeja("CO")])
        calls = []

        def fake_cycle(_driver, _config, bandeja_arg, _state, _timeout, **_kwargs):
            calls.append(bandeja_arg["code"])
            if bandeja_arg["code"] == "AR":
                raise TimeoutError("timeout")
            return []

        with patch("lead_monitor.run_bandeja_cycle", side_effect=fake_cycle):
            events = run_cycle(object(), CONFIG, state, 5)
        self.assertEqual(calls, ["AR", "CO"])
        self.assertEqual(events[0]["type"], "bandeja_error")

    def test_session_lost_stops_remaining_bandejas(self):
        state = default_state()
        state["bandejas"] = validate_bandejas([bandeja("AR"), bandeja("CO")])

        def fake_cycle(_driver, _config, bandeja_arg, _state, _timeout, **_kwargs):
            return [{"type": "session_lost", "bandeja": bandeja_arg["code"]}]

        with patch("lead_monitor.run_bandeja_cycle", side_effect=fake_cycle) as cycle:
            events = run_cycle(object(), CONFIG, state, 5)
        self.assertEqual(cycle.call_count, 1)
        self.assertEqual(events[0]["type"], "session_lost")


if __name__ == "__main__":
    unittest.main()
