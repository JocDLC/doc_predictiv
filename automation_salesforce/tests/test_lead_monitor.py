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
    def test_toma_simple_o_reasignada_no_escribe_comentarios(self):
        """Tomar un lead no documenta contacto ni edita texto previo."""
        from lead_monitor import finalize_pick_up

        for encargada in (None, {"nombre": "Ana Perez"}):
            for panel in ("panel_guardado", "sin_panel", "panel_error"):
                with (
                    self.subTest(encargada=encargada, panel=panel),
                    patch("lead_monitor._save_contact_panel_initial", return_value=panel),
                    patch("lead_monitor._save_contact_panel_late", return_value="sin_panel"),
                    patch("lead_monitor.execute_in_any_frame", return_value=[]),
                    patch("lead_monitor._ensure_take_mark") as mark,
                    patch("lead_monitor.prepare_other_information") as edit,
                    patch("lead_monitor.save_edit_form") as save,
                    patch("lead_monitor.send_whatsapp") as send,
                    patch("lead_monitor.reassign_owner", return_value="reasignado") as reassign,
                ):
                    outcome, _ = finalize_pick_up(
                        object(), 5, encargada=encargada,
                        details={"preferencia_contacto": "vía whatsapp"},
                    )
                    mark.assert_not_called()
                    edit.assert_not_called()
                    save.assert_not_called()
                    send.assert_not_called()
                    self.assertIn("/sin_comentario", outcome)
                    if encargada:
                        reassign.assert_called_once()
                    else:
                        reassign.assert_not_called()

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
            patch("lead_monitor.field_result_if_found", side_effect=lambda *_: next(_field_reads("Nota previa"))),
            patch("lead_monitor._read_other_information_value", return_value="Nota previa"),
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.wait_for_lightning_ready"),
            patch("lead_monitor.time.sleep"),
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "panel_guardado/sin_comentario")
        # Nada de buscar inputs ni send_keys: presencia → Save → listo.
        self.assertEqual(executed, [PANEL_PRESENT_SCRIPT, PANEL_SAVE_CLICK_SCRIPT])
        edit.assert_not_called()  # tampoco modifica las notas previas

    def test_injected_asignado_is_cleaned_for_own_take(self):
        """Compliance: la toma del bot no es un contacto — el 'Asignado'
        que el Save del panel (o un flow) inyecta en Otra información se
        elimina: un lead tomado por el bot no puede quedar como gestionado."""
        from lead_monitor import PANEL_PRESENT_SCRIPT, PANEL_SAVE_CLICK_SCRIPT, finalize_pick_up

        responses = {
            PANEL_PRESENT_SCRIPT: "found",
            PANEL_SAVE_CLICK_SCRIPT: "clicked",
        }
        reads = _field_reads("Asignado", "Asignado")
        persisted = iter(["Asignado", ""])
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
        self.assertEqual(outcome, "panel_guardado/asignado_quitado")
        edit.assert_called_once_with(unittest.mock.ANY, "", unittest.mock.ANY)
        save.assert_called_once()

    def test_injected_asignado_removed_preserving_notes(self):
        """'Nota previa\\nAsignado' → queda solo 'Nota previa': la
        limpieza quita la línea inyectada sin tocar el resto."""
        from lead_monitor import PANEL_PRESENT_SCRIPT, PANEL_SAVE_CLICK_SCRIPT, finalize_pick_up

        responses = {
            PANEL_PRESENT_SCRIPT: "found",
            PANEL_SAVE_CLICK_SCRIPT: "clicked",
        }
        reads = _field_reads("Nota previa\nAsignado", "Nota previa\nAsignado")
        persisted = iter(["Nota previa\nAsignado", "Nota previa"])
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
        self.assertEqual(outcome, "panel_guardado/asignado_quitado")
        edit.assert_called_once_with(unittest.mock.ANY, "Nota previa", unittest.mock.ANY)
        save.assert_called_once()

    def test_panel_save_preserves_other_information(self):
        """Tras Save no agrega Asignado ni altera las notas del auxiliar."""
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
        self.assertEqual(outcome, "panel_guardado/sin_comentario")
        edit.assert_not_called()
        save.assert_not_called()

    def test_mark_lost_by_panel_reload_is_retried(self):
        """Si el repintado tras el Save del panel pierde la escritura, se
        reintenta una vez y queda confirmada."""
        from lead_monitor import _ensure_take_mark

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
            outcome = _ensure_take_mark(object(), 5)
        self.assertEqual(outcome, "marca_ok")
        self.assertEqual(edit.call_count, 2)
        self.assertEqual(save.call_count, 2)

    def test_icon_glued_edit_label_is_stripped(self):
        """Regresión: la etiqueta del lápiz llegó pegada a un glifo de ícono
        ("✎ Modificar Otra información") y el strip por igualdad exacta la
        dejaba pasar → se persistía dentro del valor."""
        from lead_monitor import _ensure_take_mark

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
            outcome = _ensure_take_mark(object(), 5)
        self.assertEqual(outcome, "marca_ok")
        self.assertEqual(edit.call_args.args[1], "Asignado")

    def test_persisted_label_pollution_is_repaired(self):
        """Verificación pedida: si el valor YA guardado trae la etiqueta del
        lápiz (contaminado en una corrida previa), se reescribe limpio aunque
        la marca Asignado ya esté."""
        from lead_monitor import _ensure_take_mark

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
            outcome = _ensure_take_mark(object(), 5)
        self.assertEqual(outcome, "marca_ok")
        self.assertEqual(edit.call_args.args[1], "Asignado")  # queda limpio
        save.assert_called_once()

    def test_unrendered_field_is_not_blank(self):
        """Regresión del bug real: lectura "" por campo no renderizado no es
        un campo vacío — se espera el render y se escribe sobre el valor real."""
        from lead_monitor import _ensure_take_mark

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
            outcome = _ensure_take_mark(object(), 5)
        self.assertEqual(outcome, "marca_ok")
        # Escribe sobre el contenido real, no sobre "": nunca pisa datos.
        self.assertEqual(edit.call_args.args[1], "Contenido real\nAsignado")
        save.assert_called_once()

    def test_field_absent_reports_campo_ausente(self):
        """Si el campo nunca se renderiza, no se escribe a ciegas y queda
        registrado como campo_ausente."""
        from lead_monitor import _ensure_take_mark

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
            outcome = _ensure_take_mark(object(), 5)
        self.assertEqual(outcome, "campo_ausente")
        edit.assert_not_called()

    def test_mark_unconfirmed_after_two_writes(self):
        """Dos escrituras sin confirmar la marca: se reporta en el outcome."""
        from lead_monitor import _ensure_take_mark

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
            outcome = _ensure_take_mark(object(), 5)
        self.assertEqual(outcome, "marca_no_confirmada")
        self.assertEqual(edit.call_count, 2)
        self.assertEqual(save.call_count, 2)

    def test_mark_error_is_reported_not_swallowed(self):
        """Un fallo al editar queda en el outcome en vez de perderse en un
        ``except`` silencioso."""
        from selenium.common.exceptions import TimeoutException

        from lead_monitor import _ensure_take_mark

        with (
            patch("lead_monitor.execute_in_any_frame", return_value="missing"),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.LATE_PANEL_WAIT_SECONDS", 0),
            patch("lead_monitor.field_result_if_found", return_value={"found": True, "text": "Nota previa"}),
            patch("lead_monitor.prepare_other_information", side_effect=TimeoutException("boom")),
        ):
            outcome = _ensure_take_mark(object(), 5)
        self.assertEqual(outcome, "marca_error:editar:TimeoutException")

    def test_late_panel_is_saved_without_mark(self):
        """El panel puede renderizar pasada la ventana inicial (bajo carga):
        el chequeo tardío lo guarda sin depender de escribir una marca."""
        from lead_monitor import (
            PANEL_PRESENT_SCRIPT,
            PANEL_SAVE_CLICK_SCRIPT,
            finalize_pick_up,
        )

        def fake_exec(_driver, script, *args):
            if script is PANEL_PRESENT_SCRIPT:
                return "found"
            if script is PANEL_SAVE_CLICK_SCRIPT:
                return "clicked"
            return []  # PANEL_DIAGNOSTIC_SCRIPT

        with (
            patch("lead_monitor._save_contact_panel_initial", return_value="sin_panel"),
            patch("lead_monitor.execute_in_any_frame", side_effect=fake_exec),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.001),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", return_value={"found": True, "text": "Asignado"}),
            patch("lead_monitor._drop_injected_take_mark", return_value="sin_comentario") as drop,
            patch("lead_monitor.prepare_other_information") as edit,
            patch("lead_monitor.wait_for_lightning_ready"),
            patch("lead_monitor.time.sleep"),
        ):
            outcome, diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "panel_tardio_guardado/sin_comentario")
        drop.assert_called_once()
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
            patch("lead_monitor._drop_injected_take_mark", return_value="sin_comentario"),
        ):
            outcome, diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "sin_panel/sin_comentario")
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
            patch("lead_monitor._drop_injected_take_mark", return_value="sin_comentario"),
            patch("lead_monitor.time.sleep"),
        ):
            outcome, diag = finalize_pick_up(driver, 5)
        self.assertEqual(outcome, "panel_otra_tab_guardado/sin_comentario")
        self.assertEqual(driver.current_window_handle, "main")  # restaurado

    def test_missing_panel_does_not_mark_other_information(self):
        """Sin panel tampoco se escribe en Otra información."""
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
        self.assertEqual(outcome, "sin_panel/sin_comentario")
        edit.assert_not_called()
        save.assert_not_called()

    def test_edit_button_label_is_never_written_into_the_field(self):
        """La lectura arrastra "Modificar Otra información": no debe quedar
        dentro del valor guardado (bug reportado en el lead real)."""
        from lead_monitor import _ensure_take_mark

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
            _ensure_take_mark(object(), 5)
        self.assertEqual(edit.call_args.args[1], "Asignado")

    def test_edit_button_label_stripped_but_content_kept(self):
        from lead_monitor import _ensure_take_mark

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
            _ensure_take_mark(object(), 5)
        self.assertEqual(edit.call_args.args[1], "Nota previa\nAsignado")

    def test_panel_error_does_not_raise(self):
        """Un panel roto no degrada el `tomado` ya verificado."""
        from selenium.common.exceptions import WebDriverException

        from lead_monitor import finalize_pick_up

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=WebDriverException("boom")),
            patch("lead_monitor.PANEL_WAIT_SECONDS", 0.01),
            patch("lead_monitor.field_result_if_found", return_value={"found": True, "text": "Asignado"}),
            patch("lead_monitor._drop_injected_take_mark", return_value="sin_comentario"),
        ):
            outcome, _diag = finalize_pick_up(object(), 5)
        self.assertEqual(outcome, "panel_error/sin_comentario")


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

    def test_non_whatsapp_lead_does_not_write_or_send(self):
        """Sin envío real no hay documentación ni marca de toma."""
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
        self.assertEqual(outcome, "sin_panel/sin_comentario")
        edit.assert_not_called()
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
        lead_events = [e for e in events if e["type"] == "lead_result"]
        self.assertEqual(len(lead_events), 2)
        self.assertTrue(all(e["status"] == STATUS_TOMADO for e in lead_events))
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
        self.assertEqual([e for e in events if e["type"] == "lead_result"], [])

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
        self.assertEqual([e for e in events if e["type"] == "lead_result"], [])
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
        lead_events = [e for e in events if e["type"] == "lead_result"]
        self.assertEqual(lead_events[0]["status"], STATUS_ERROR)

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
        lead_events = [e for e in events if e["type"] == "lead_result"]
        self.assertEqual(lead_events[0]["status"], "detectado")
        self.assertEqual(lead_events[0]["entry"]["motivo"], "sin_cobertura")

    def test_franja_propia_por_bandeja_deja_pasar_al_equipo(self):
        """La franja propia vigente es de AR pero el ciclo corre sobre MX:
        el lead NO es del usuario logueado — se reasigna a quien cubre MX."""
        state = self._state()
        state["schedule"] = [{"start": "00:00", "end": "23:59", "bandejas": ["AR"]}]
        equipo = [{"nombre": "Ana", "franjas": [{"start": "00:00", "end": "23:59", "bandejas": ["MX"]}]}]
        state["equipo"] = equipo
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, [lead()])),
            patch("lead_monitor.take_lead", return_value=(STATUS_TOMADO, "Ana", "x/reasignado", "")) as take,
        ):
            run_bandeja_cycle(object(), CONFIG, bandeja("MX"), state, 5)
        take.assert_called_once()
        self.assertEqual(take.call_args.kwargs["equipo"], equipo)

    def test_franja_propia_por_bandeja_sin_cobertura(self):
        """Franja propia de AR, bandeja MX y nadie del equipo la cubre:
        el lead queda detectado 'sin cobertura', no lo toma el usuario."""
        state = self._state()
        state["schedule"] = [{"start": "00:00", "end": "23:59", "bandejas": ["AR"]}]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, [lead()])),
            patch("lead_monitor.take_lead") as take,
        ):
            events = run_bandeja_cycle(object(), CONFIG, bandeja("MX"), state, 5)
        take.assert_not_called()
        lead_events = [e for e in events if e["type"] == "lead_result"]
        self.assertEqual(lead_events[0]["status"], "detectado")
        self.assertEqual(lead_events[0]["entry"]["motivo"], "sin_cobertura")

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

    def test_lead_ingresado_en_turno_del_equipo_se_reasigna(self):
        """Bug de producción: turno propio activo AHORA (14:01) pero el
        lead entró 13:59, dentro de la franja del equipo → se pasa el
        equipo a take_lead para reasignarlo."""
        from datetime import datetime

        state = self._state()
        state["schedule"] = [
            {"start": "10:00", "end": "11:59"},
            {"start": "14:00", "end": "15:59"},
        ]
        equipo = [
            {
                "nombre": "Andres Antelo",
                "franjas": [
                    {"start": "08:00", "end": "09:59", "bandejas": ["AR"]},
                    {"start": "12:00", "end": "13:59", "bandejas": ["AR"]},
                ],
            }
        ]
        state["equipo"] = equipo
        fixed = datetime(2026, 10, 31, 14, 1)

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed

        leads = [lead(LEAD_ID, fecha_creacion="31/10/2026 01:59 PM")]
        with (
            patch("lead_monitor.datetime", FixedDatetime),
            patch("monitor_store.datetime", FixedDatetime),
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(1, leads)),
            patch(
                "lead_monitor.take_lead",
                return_value=(STATUS_TOMADO, "Andres Antelo", "x/reasignado", ""),
            ) as take,
        ):
            run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        take.assert_called_once()
        self.assertEqual(take.call_args.kwargs["equipo"], equipo)

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
        lead_events = [e for e in events if e["type"] == "lead_result"]
        self.assertEqual(len(lead_events), 2)
        self.assertTrue(all(e["status"] == "detectado" for e in lead_events))

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
        lead_events = [e for e in events if e["type"] == "lead_result"]
        self.assertEqual(len(lead_events), 2)
        self.assertTrue(all(e["status"] == "detectado" for e in lead_events))

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
        lead_events = [e for e in events if e["type"] == "lead_result"]
        self.assertEqual(lead_events[0]["status"], STATUS_TOMADO)

    def test_bandeja_scan_event_reports_rows_and_matches(self):
        """El evento bandeja_scan deja en el log cuántas filas se leyeron y
        cuántas matchearon el propietario sin asignar — el diagnóstico del
        caso "abre la bandeja pero no toma ni lista nada"."""
        state = self._state()
        leads = [lead(LEAD_ID)]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(7, leads)),
            patch("lead_monitor.take_lead", return_value=(STATUS_TOMADO, "Maria Perez", "panel_guardado/marca_ok", "")),
        ):
            events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        scan = next(e for e in events if e["type"] == "bandeja_scan")
        self.assertEqual(scan["rows"], 7)
        self.assertEqual(scan["unassigned"], 1)
        self.assertEqual(scan["unassigned_owner"], "AR_LEAD_QUALIF")
        self.assertIn("owners_seen", scan)

    def test_bandeja_scan_marks_status_skips(self):
        """Los QUALIF omitidos por estado distinto quedan contados en el
        evento de escaneo (antes se descartaban sin rastro)."""
        state = self._state()
        leads = [lead(LEAD_ID, estado="En curso"), lead(LEAD_ID_B, estado="Nuevo")]
        with (
            patch("lead_monitor.open_report"),
            patch("lead_monitor.report_session_lost", return_value=False),
            patch("lead_monitor.read_bandeja_leads", return_value=(2, leads)),
            patch("lead_monitor.take_lead", return_value=(STATUS_TOMADO, "Maria Perez", "panel_guardado/marca_ok", "")),
        ):
            events = run_bandeja_cycle(object(), CONFIG, state["bandejas"][0], state, 5)
        scan = next(e for e in events if e["type"] == "bandeja_scan")
        self.assertEqual(scan.get("skipped_status"), 1)


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

    def test_encargada_activa_fin_de_franja_inclusive(self):
        """El usuario escribe 12:00–13:59 queriendo cubrir 13:59
        inclusive; 14:00 ya queda fuera."""
        from datetime import datetime

        from lead_monitor import _encargada_activa

        equipo = [{"nombre": "Ana", "franjas": [{"start": "12:00", "end": "13:59"}]}]
        self.assertEqual(
            _encargada_activa(equipo, datetime(2026, 10, 15, 13, 59))["nombre"], "Ana"
        )
        self.assertIsNone(_encargada_activa(equipo, datetime(2026, 10, 15, 14, 0)))

    def test_encargada_para_lead_fecha_de_ayer_cae_a_hora_actual(self):
        """Una fecha de creación de OTRO día no decide la reasignación:
        cae al miembro cuya franja cubre la hora actual."""
        from datetime import datetime

        from lead_monitor import _encargada_para_lead

        equipo = [
            {"nombre": "Ana", "franjas": [{"start": "00:00", "end": "08:00", "bandejas": ["AR"]}]},
            {"nombre": "Beto", "franjas": [{"start": "12:00", "end": "23:59", "bandejas": ["AR"]}]},
        ]
        now = datetime(2026, 10, 31, 14, 0)  # Beto cubre ahora; Ana cubría a las 07:00
        details = {"fecha_creacion": "30/10/2026 07:00 AM"}
        self.assertEqual(
            _encargada_para_lead(equipo, "Jose Manuel", bandeja="AR", details=details, now=now)[
                "nombre"
            ],
            "Beto",
        )

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

    def test_encargada_para_lead_usa_hora_de_ingreso(self):
        """La encargada se elige por la hora de ingreso del lead a la
        cola (Fecha de creación), no por la hora en que el bot lo toma:
        el bot puede tardar minutos y caer en la franja siguiente."""
        from datetime import datetime

        from lead_monitor import _encargada_para_lead

        roger = {
            "nombre": "ROGER FABIAN VELASCO CAMERO",
            "franjas": [{"start": "11:00", "end": "12:39", "bandejas": ["AR"]}],
        }
        owner = "Jose Manuel de la Colina"
        # El bot lo toma el MISMO día que la fecha de creación: una
        # entrada de otro día no decide la reasignación.
        # Ingresó 10:57 y el bot lo toma 10:58: ninguna franja cubre ni
        # el ingreso ni la toma -> sin reasignación.
        self.assertIsNone(
            _encargada_para_lead(
                [roger], owner, bandeja="AR",
                details={"fecha_creacion": "30/10/2026 10:57 AM"},
                now=datetime(2026, 10, 30, 10, 58),
            )
        )
        # Ingresó 11:15: sí cae en la franja de Roger aunque el bot lo
        # tome a las 12:50, ya fuera de la franja -> igual va a Roger.
        self.assertIs(
            _encargada_para_lead(
                [roger], owner, bandeja="AR",
                details={"fecha_creacion": "30/10/2026 11:15 AM"},
                now=datetime(2026, 10, 30, 12, 50),
            ),
            roger,
        )

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

        with (
            patch("lead_monitor.execute_in_any_frame", return_value="not_found"),
            patch(
                "lead_monitor._reread_owner_after_refresh",
                return_value="Jose Manuel de la Colina",
            ),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertEqual(
                reassign_owner(unittest.mock.Mock(), "Micaela Caetano", 0.1),
                "reasignacion_error:modal",
            )

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
            patch(
                "lead_monitor._reread_owner_after_refresh",
                return_value="Jose Manuel de la Colina",
            ),
            patch("lead_monitor.QUEUE_SEARCH_TIMEOUT_SECONDS", 0.01),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertEqual(
                reassign_owner(unittest.mock.Mock(), "Inexistente", 5),
                "reasignacion_error:opcion",
            )

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
            patch(
                "lead_monitor._reread_owner_after_refresh",
                return_value="Jose Manuel de la Colina",
            ),
            patch("lead_monitor.OWNER_VERIFY_TIMEOUT_SECONDS", 0.01),
            patch("lead_monitor.POLL_SECONDS", 0.01),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertEqual(
                reassign_owner(unittest.mock.Mock(), "Micaela Caetano", 5),
                "reasignacion_error:verificacion",
            )

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

    def test_reasignacion_no_comenta_cualquiera_sea_la_preferencia(self):
        """La preferencia no genera comentarios de asignación."""
        from lead_monitor import finalize_pick_up

        for preferencia in ("vía whatsapp", "llamada telefónica", "correo", ""):
            with (
                self.subTest(preferencia=preferencia),
                patch("lead_monitor._save_contact_panel_initial", return_value="panel_guardado"),
                patch("lead_monitor._ensure_take_mark") as mark,
                patch("lead_monitor.prepare_other_information") as edit,
                patch("lead_monitor.send_whatsapp") as send,
                patch("lead_monitor.reassign_owner", return_value="reasignado") as reassign,
            ):
                outcome, _ = finalize_pick_up(
                    object(), 5, whatsapp=True, encargada={"nombre": "Ana Perez"},
                    details={"preferencia_contacto": preferencia},
                )
                self.assertEqual(outcome, "panel_guardado/sin_comentario/reasignado")
                mark.assert_not_called()
                edit.assert_not_called()
                send.assert_not_called()
                reassign.assert_called_once()

    def test_reassign_owner_action_button_appears_late(self):
        """El botón Cambiar propietario llega tarde por el re-render tras
        Save: se reintenta el clic hasta que aparece, sin releer el
        propietario porque el intento sale ``reasignado``."""
        from lead_closure import MODAL_CONFIRM_SCRIPT, RECORD_ACTION_SCRIPT
        from lead_monitor import (
            OWNER_DIALOG_OPEN_SCRIPT,
            OWNER_SEARCH_INPUT_SCRIPT,
            PICK_QUEUE_RESULT_SCRIPT,
            reassign_owner,
        )

        clicks = iter(["not_found", "not_found", "clicked"])
        responses = {
            OWNER_DIALOG_OPEN_SCRIPT: "open",
            OWNER_SEARCH_INPUT_SCRIPT: unittest.mock.Mock(),
            PICK_QUEUE_RESULT_SCRIPT: "clicked",
            MODAL_CONFIRM_SCRIPT: "clicked",
        }
        def fake_exec(_driver, script, *args):
            if script == RECORD_ACTION_SCRIPT:
                return next(clicks)
            return responses.get(script, "not_found")

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=fake_exec),
            patch("lead_monitor.read_record_owner", return_value="Micaela Caetano"),
            patch("lead_monitor._reread_owner_after_refresh") as reread,
            patch("lead_monitor.POLL_SECONDS", 0.001),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertEqual(
                reassign_owner(unittest.mock.Mock(), "Micaela Caetano", 5), "reasignado"
            )
        reread.assert_not_called()

    def test_open_change_owner_dialog_second_click_opens(self):
        """Si el modal no abre tras el primer clic, se permite un segundo
        clic (máximo 2) antes de rendirse."""
        from lead_closure import RECORD_ACTION_SCRIPT
        from lead_monitor import (
            OWNER_DIALOG_OPEN_SCRIPT,
            open_change_owner_dialog,
        )

        state = {"clicks": 0}
        def fake_exec(_driver, script, *args):
            if script == RECORD_ACTION_SCRIPT:
                state["clicks"] += 1
                return "clicked"
            if script == OWNER_DIALOG_OPEN_SCRIPT:
                return "open" if state["clicks"] == 2 else "closed"
            return "clicked"  # cancel del dismiss

        with (
            patch("lead_monitor.execute_in_any_frame", side_effect=fake_exec),
            patch("lead_monitor.OWNER_DIALOG_OPEN_WAIT_SECONDS", 0.01),
            patch("lead_monitor.POLL_SECONDS", 0.001),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertTrue(open_change_owner_dialog(unittest.mock.Mock(), 5))

    def test_reassign_owner_reread_already_assigned(self):
        """El intento falla pero la relectura muestra que el lead ya quedó
        a nombre de la encargada → ``reasignado`` sin segundo intento."""
        import lead_monitor

        with (
            patch(
                "lead_monitor._reassign_attempt",
                return_value="reasignacion_error:verificacion",
            ) as attempt,
            patch(
                "lead_monitor._reread_owner_after_refresh",
                return_value="Micaela Caetano",
            ) as reread,
        ):
            self.assertEqual(
                lead_monitor.reassign_owner(unittest.mock.Mock(), "Micaela Caetano", 5),
                "reasignado",
            )
        self.assertEqual(attempt.call_count, 1)
        reread.assert_called_once()

    def test_reassign_owner_second_attempt_succeeds(self):
        """La relectura muestra al usuario del bot → segundo intento."""
        import lead_monitor

        with (
            patch(
                "lead_monitor._reassign_attempt",
                side_effect=["reasignacion_error:verificacion", "reasignado"],
            ) as attempt,
            patch(
                "lead_monitor._reread_owner_after_refresh",
                return_value="Jose Manuel de la Colina",
            ),
        ):
            self.assertEqual(
                lead_monitor.reassign_owner(unittest.mock.Mock(), "Micaela Caetano", 5),
                "reasignado",
            )
        self.assertEqual(attempt.call_count, 2)

    def test_reassign_owner_both_attempts_fail(self):
        """Ambos intentos fallan → devuelve el outcome del segundo."""
        import lead_monitor

        with (
            patch(
                "lead_monitor._reassign_attempt",
                side_effect=["reasignacion_error:modal", "reasignacion_error:opcion"],
            ) as attempt,
            patch(
                "lead_monitor._reread_owner_after_refresh",
                return_value="Jose Manuel de la Colina",
            ) as reread,
        ):
            self.assertEqual(
                lead_monitor.reassign_owner(unittest.mock.Mock(), "Micaela Caetano", 5),
                "reasignacion_error:opcion",
            )
        self.assertEqual(attempt.call_count, 2)
        reread.assert_called_once()

    _SEARCH_PRESENT = object()

    def _verify_persona_option(self, open_modal=True, search_input=_SEARCH_PRESENT, pick=True):
        """Corre verify_persona_option con el modal mockeado y devuelve
        (outcome, dismiss): la regla es que SIEMPRE cancela y NUNCA
        confirma (se verifica en todos los caminos)."""
        import lead_monitor

        if search_input is self._SEARCH_PRESENT:
            search_input = unittest.mock.Mock()
        with (
            patch("lead_monitor.open_change_owner_dialog", return_value=open_modal),
            patch("lead_monitor._wait_owner_search_input", return_value=search_input),
            patch("lead_monitor._pick_owner_option", return_value=pick),
            patch("lead_monitor._dismiss_owner_dialog") as dismiss,
            patch("lead_monitor._confirm_owner_dialog") as confirm,
        ):
            outcome = lead_monitor.verify_persona_option(unittest.mock.Mock(), "Ana Perez", 5)
        confirm.assert_not_called()
        return outcome, dismiss

    def test_verify_persona_option_ok_always_dismisses(self):
        """Nombre encontrado en el lookup → opcion_ok y el modal se
        cancela igual: la simulación nunca confirma."""
        outcome, dismiss = self._verify_persona_option(pick=True)
        self.assertEqual(outcome, "opcion_ok")
        dismiss.assert_called_once()

    def test_verify_persona_option_modal_missing_no_dismiss(self):
        """Si el modal no abrió no hay nada que cancelar."""
        outcome, dismiss = self._verify_persona_option(open_modal=False)
        self.assertEqual(outcome, "reasignacion_error:modal")
        dismiss.assert_not_called()

    def test_verify_persona_option_search_missing_dismisses(self):
        """Sin input de búsqueda → reasignacion_error:busqueda y cancela."""
        outcome, dismiss = self._verify_persona_option(search_input=None)
        self.assertEqual(outcome, "reasignacion_error:busqueda")
        dismiss.assert_called_once()

    def test_verify_persona_option_option_missing_dismisses(self):
        """El nombre no aparece en el lookup → reasignacion_error:opcion
        y el modal se cancela (nunca queda abierto)."""
        outcome, dismiss = self._verify_persona_option(pick=False)
        self.assertEqual(outcome, "reasignacion_error:opcion")
        dismiss.assert_called_once()

    def test_verify_persona_option_forwards_diagnostics(self):
        """El dict de diagnóstico llega a _pick_owner_option para que el
        caller vea qué mostraba el desplegable cuando la opción no sale."""
        import lead_monitor

        diagnostics = {}
        with (
            patch("lead_monitor.open_change_owner_dialog", return_value=True),
            patch("lead_monitor._wait_owner_search_input", return_value=unittest.mock.Mock()),
            patch("lead_monitor._pick_owner_option", return_value=False) as pick,
            patch("lead_monitor._dismiss_owner_dialog"),
        ):
            lead_monitor.verify_persona_option(unittest.mock.Mock(), "Ana Perez", 5, diagnostics)
        self.assertIs(pick.call_args.args[-1], diagnostics)


class PickOwnerOptionTests(unittest.TestCase):
    def test_focuses_input_before_typing(self):
        """El combobox de Lightning ignora send_keys sin foco: click primero."""
        import lead_monitor

        search_input = unittest.mock.Mock()
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="clicked"),
            patch("lead_monitor.time.sleep"),
        ):
            self.assertTrue(
                lead_monitor._pick_owner_option(unittest.mock.Mock(), search_input, "Ana Perez", 1)
            )
        names = [call[0] for call in search_input.mock_calls]
        self.assertEqual(names[:3], ["click", "clear", "send_keys"])

    def test_fills_diagnostics_when_option_never_appears(self):
        """Sin opción: el diagnóstico vuelca lo que veía el desplegable."""
        import lead_monitor

        diagnostics = {}
        with (
            patch("lead_monitor.execute_in_any_frame", return_value="not_found"),
            patch("lead_monitor.time.sleep"),
            patch(
                "lead_monitor._owner_lookup_snapshot",
                return_value={"inputValue": "Ana Perez", "options": ["x", "y"]},
            ),
        ):
            self.assertFalse(
                lead_monitor._pick_owner_option(
                    unittest.mock.Mock(), unittest.mock.Mock(), "Ana Perez", 0.01, diagnostics
                )
            )
        self.assertEqual(diagnostics["inputValue"], "Ana Perez")
        self.assertEqual(diagnostics["options"], ["x", "y"])


class EquipoParaLeadTests(unittest.TestCase):
    def _state(self):
        state = default_state()
        state["schedule"] = [
            {"start": "10:00", "end": "11:59", "bandejas": ["AR"]},
            {"start": "14:00", "end": "15:59", "bandejas": ["AR"]},
        ]
        state["equipo"] = [
            {
                "nombre": "Andres Antelo",
                "franjas": [
                    {"start": "08:00", "end": "09:59", "bandejas": ["AR"]},
                    {"start": "12:00", "end": "13:59", "bandejas": ["AR"]},
                ],
            }
        ]
        return state

    def test_entrada_en_franja_del_equipo_devuelve_equipo(self):
        """Caso productivo: turno propio activo ahora (14:01) pero el lead
        entró 13:59, en franja de Andres → reasignar al equipo."""
        from datetime import datetime

        from lead_monitor import _equipo_para_lead

        state = self._state()
        now = datetime.now().replace(hour=14, minute=1, second=0, microsecond=0)
        details = {"fecha_creacion": now.strftime("%d/%m/%Y") + " 01:59 PM"}
        self.assertEqual(_equipo_para_lead(state, "AR", details, now), state["equipo"])

    def test_entrada_en_franja_propia_devuelve_none(self):
        """El lead entró 14:30, dentro de la franja propia → queda con el
        usuario logueado aunque ahora sea otra hora."""
        from datetime import datetime

        from lead_monitor import _equipo_para_lead

        state = self._state()
        now = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
        details = {"fecha_creacion": now.strftime("%d/%m/%Y") + " 02:30 PM"}
        self.assertIsNone(_equipo_para_lead(state, "AR", details, now))

    def test_entrada_de_ayer_cae_al_comportamiento_actual(self):
        """Fecha de creación de otro día no decide: ahora (14:01) la
        franja propia cubre → lead propio."""
        from datetime import datetime, timedelta

        from lead_monitor import _equipo_para_lead

        state = self._state()
        now = datetime.now().replace(hour=14, minute=1, second=0, microsecond=0)
        yesterday = (now - timedelta(days=1)).strftime("%d/%m/%Y") + " 01:59 PM"
        self.assertIsNone(
            _equipo_para_lead(state, "AR", {"fecha_creacion": yesterday}, now)
        )

    def test_entrada_inparseable_cae_al_comportamiento_actual(self):
        """Sin fecha usable vale la regla de siempre: franja propia
        vigente ahora → lead propio."""
        from datetime import datetime

        from lead_monitor import _equipo_para_lead

        state = self._state()
        now = datetime.now().replace(hour=14, minute=1, second=0, microsecond=0)
        self.assertIsNone(
            _equipo_para_lead(state, "AR", {"fecha_creacion": "sin formato"}, now)
        )
        self.assertIsNone(_equipo_para_lead(state, "AR", None, now))

    def test_entrada_sin_cobertura_cae_al_comportamiento_actual(self):
        """Entrada 07:00 sin franja (ni propia ni de equipo) y ahora
        13:00, fuera del turno propio → reasignar al equipo."""
        from datetime import datetime

        from lead_monitor import _equipo_para_lead

        state = self._state()
        now = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
        details = {"fecha_creacion": now.strftime("%d/%m/%Y") + " 07:00 AM"}
        self.assertEqual(_equipo_para_lead(state, "AR", details, now), state["equipo"])


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
