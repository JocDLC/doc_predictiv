import inspect
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import run_close_queue
from run_close_queue import close_one_lead, persist_and_verify

LEAD = {"lead_id": "00Q000000000001AAA", "reason": "ilocalizable"}
CONFIG = {
    "salesforce_url": "https://sf.example",
    "record_object_api_name": "Lead",
    "timeouts": {"page_load_seconds": 5, "authentication_seconds": 5},
}
OPEN_STATE = {"estado": "Nuevo", "propietario": "Auxiliar X", "comentario": ""}
SAVED_STATE = {"estado": "Cerrado", "propietario": "Auxiliar X", "comentario": "Ilocalizable"}
FINAL_STATE = {"estado": "Cerrado", "propietario": "AR_LEAD_COLD", "comentario": "Ilocalizable"}
EMPTY_STATE = {"estado": "", "propietario": "", "comentario": ""}
CONTRACT_ILOCALIZABLE = {
    "comentario": "Ilocalizable",
    "cualificacion": "Rechazo no argumentado",
    "subcualificacion": "Ilocalizable",
}


class FakeSwitchTo:
    def default_content(self):
        pass


class FakeDriver:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)

    switch_to = FakeSwitchTo()

    def save_screenshot(self, path):
        Path(path).write_bytes(b"png")


class CloseOneLeadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.results_path = Path(self.temporary.name) / "cola_cierre.resultado.json"
        self.screenshots = Path(self.temporary.name) / "capturas"
        self.driver = FakeDriver()

    def tearDown(self):
        self.temporary.cleanup()

    def run_lead(self, states, **overrides):
        """Ejecuta close_one_lead con el DOM mockeado y lecturas sucesivas."""
        logger = overrides.get("logger") or unittest.mock.Mock()
        patches = {
            "read_closure_state": unittest.mock.Mock(side_effect=states),
            "wait_for_lightning_ready": unittest.mock.Mock(),
            "open_qualification_edit": overrides.get("open_qualification_edit", unittest.mock.Mock()),
            "set_comentario": overrides.get("set_comentario", unittest.mock.Mock()),
            "select_picklist_option": overrides.get("select", unittest.mock.Mock()),
            "save_edit_form": overrides.get("save_edit_form", unittest.mock.Mock()),
            "edit_form_matches": overrides.get("edit_matches", unittest.mock.Mock(return_value=True)),
            "verify_persisted_fields": overrides.get("verify_fields", unittest.mock.Mock(return_value=True)),
            "convert_lead": overrides.get("convert_lead", unittest.mock.Mock()),
            "confirm_conversion": overrides.get("confirm_conversion", unittest.mock.Mock()),
            "find_field_value": overrides.get("find_field_value", unittest.mock.Mock(return_value="INT 1")),
            "find_field_text": overrides.get("find_field_text", unittest.mock.Mock(return_value="")),
            "prepare_other_information": overrides.get("prepare_other_information", unittest.mock.Mock()),
            "capture_failure": unittest.mock.Mock(return_value=Path("cap.png")),
        }
        with unittest.mock.patch.multiple(run_close_queue, **patches), patch("run_close_queue.time.sleep"):
            entry = close_one_lead(
                self.driver,
                LEAD,
                CONFIG,
                self.results_path,
                self.screenshots,
                logger,
                "run_x",
                country=overrides.get("country", "argentina"),
            )
        return entry, patches

    def test_missing_initial_state_or_owner_never_edits_or_converts(self):
        for country in ("argentina", "colombia_mexico"):
            for state in (EMPTY_STATE, {**OPEN_STATE, "propietario": ""}, {**OPEN_STATE, "estado": ""}):
                with self.subTest(country=country, state=state):
                    entry, patches = self.run_lead([state], country=country)
                    self.assertEqual(entry["status"], "revision")
                    patches["open_qualification_edit"].assert_not_called()
                    patches["prepare_other_information"].assert_not_called()
                    patches["save_edit_form"].assert_not_called()
                    patches["convert_lead"].assert_not_called()

    def test_mexico_already_closed_never_opens_editor_or_converts(self):
        state = {**FINAL_STATE, "comentario": "1 INT Resultado previo", "motivo": "Texto previo\nIlocalizable"}
        entry, patches = self.run_lead([state], country="colombia_mexico")
        self.assertEqual(entry["status"], "ya_cerrado")
        patches["prepare_other_information"].assert_not_called()
        patches["open_qualification_edit"].assert_not_called()
        patches["convert_lead"].assert_not_called()

    def test_closed_without_verified_picklists_never_resumes_conversion(self):
        state = {**SAVED_STATE, "motivo": "Ilocalizable"}
        entry, patches = self.run_lead(
            [state], country="colombia_mexico", verify_fields=unittest.mock.Mock(return_value=False)
        )
        self.assertEqual(entry["status"], "revision")
        patches["prepare_other_information"].assert_not_called()
        patches["open_qualification_edit"].assert_not_called()
        patches["convert_lead"].assert_not_called()

    def test_happy_path_reaches_cerrado_verificado(self):
        entry, patches = self.run_lead([OPEN_STATE, SAVED_STATE, FINAL_STATE])

        self.assertEqual(entry["status"], "cerrado_verificado")
        self.assertEqual(entry["reason"], "ilocalizable")
        self.assertEqual(entry["run_id"], "run_x")
        patches["save_edit_form"].assert_called_once()
        patches["convert_lead"].assert_called_once()
        patches["confirm_conversion"].assert_called_once()

    def test_ilocalizable_subqualification_receives_ordered_candidates(self):
        entry, patches = self.run_lead([OPEN_STATE, SAVED_STATE, FINAL_STATE])

        self.assertEqual(entry["status"], "cerrado_verificado")
        subqualification_call = patches["select_picklist_option"].call_args_list[1]
        self.assertEqual(
            subqualification_call.args[2],
            ("Ilocalizable", "Permanece ilocalizable"),
        )

    def test_milestone_conversion_pendiente_written_before_conversion(self):
        """Si confirm_conversion falla, el resultado queda conversion_pendiente."""
        confirm = unittest.mock.Mock(side_effect=ValueError("modal ausente"))
        entry, _ = self.run_lead([OPEN_STATE, SAVED_STATE], confirm_conversion=confirm)

        self.assertEqual(entry["status"], "conversion_pendiente")
        saved = json.loads(self.results_path.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["status"], "conversion_pendiente")

    def test_already_closed_lead_not_touched(self):
        entry, patches = self.run_lead([FINAL_STATE])

        self.assertEqual(entry["status"], "ya_cerrado")
        patches["open_qualification_edit"].assert_not_called()
        patches["save_edit_form"].assert_not_called()
        patches["convert_lead"].assert_not_called()

    def test_duplicate_lead_goes_to_revision(self):
        state = {**OPEN_STATE, "comentario": "Lead Duplicado"}
        entry, patches = self.run_lead([state])

        self.assertEqual(entry["status"], "revision")
        patches["open_qualification_edit"].assert_not_called()

    def test_closed_with_different_reason_goes_to_revision(self):
        state = {"estado": "Cerrado", "propietario": "Otro", "comentario": "Otro motivo"}
        entry, patches = self.run_lead([state])

        self.assertEqual(entry["status"], "revision")
        patches["save_edit_form"].assert_not_called()

    def test_closed_with_same_reason_resumes_at_conversion(self):
        """Cerrado + motivo correcto pero sin AR_LEAD_COLD: solo Convert → Yes."""
        partial = {"estado": "Cerrado", "propietario": "Auxiliar X", "comentario": "Ilocalizable"}
        entry, patches = self.run_lead([partial, FINAL_STATE])

        self.assertEqual(entry["status"], "cerrado_verificado")
        patches["save_edit_form"].assert_not_called()
        patches["open_qualification_edit"].assert_not_called()
        patches["convert_lead"].assert_called_once()

    def test_edit_failure_records_error(self):
        open_edit = unittest.mock.Mock(side_effect=ValueError("no editable"))
        entry, _ = self.run_lead([OPEN_STATE], open_qualification_edit=open_edit)

        self.assertEqual(entry["status"], "error")

    def test_form_rerender_retries_field_edit_once(self):
        """Si Lightning limpió el formulario (re-render), reintenta la edición."""
        matches = unittest.mock.Mock(side_effect=[False, True, True])
        entry, patches = self.run_lead([OPEN_STATE, SAVED_STATE, FINAL_STATE], edit_matches=matches)

        self.assertEqual(entry["status"], "cerrado_verificado")
        self.assertEqual(patches["open_qualification_edit"].call_count, 2)
        self.assertEqual(patches["set_comentario"].call_count, 2)

    def test_unpersisted_save_records_error(self):
        entry, _ = self.run_lead(
            [OPEN_STATE],
            verify_fields=unittest.mock.Mock(return_value=False),
        )

        self.assertEqual(entry["status"], "error")

    def test_save_timeout_recovers_by_reloading(self):
        from selenium.common.exceptions import TimeoutException

        save = unittest.mock.Mock(side_effect=TimeoutException())
        verify = unittest.mock.Mock(return_value=True)
        entry, patches = self.run_lead(
            [OPEN_STATE, SAVED_STATE, FINAL_STATE],
            save_edit_form=save,
            verify_fields=verify,
        )

        self.assertEqual(entry["status"], "cerrado_verificado")
        self.assertIn("https://sf.example/lightning/r/Lead/00Q000000000001AAA/view", self.driver.urls)

    def test_lost_answer_after_yes_is_conversion_no_verificada(self):
        confirm = unittest.mock.Mock()  # Yes clicado, pero la lectura final falla
        with patch("run_close_queue.read_closure_state") as read_state:
            read_state.side_effect = [OPEN_STATE, SAVED_STATE, WebDriverTimeout()]
            patches = {
                "wait_for_lightning_ready": unittest.mock.Mock(),
                "open_qualification_edit": unittest.mock.Mock(),
                "set_comentario": unittest.mock.Mock(),
                "select_picklist_option": unittest.mock.Mock(),
                "edit_form_matches": unittest.mock.Mock(return_value=True),
                "verify_persisted_fields": unittest.mock.Mock(return_value=True),
                "convert_lead": unittest.mock.Mock(),
                "confirm_conversion": confirm,
                "find_field_value": unittest.mock.Mock(return_value="INT 1"),
                "find_field_text": unittest.mock.Mock(return_value=""),
                "capture_failure": unittest.mock.Mock(return_value=Path("cap.png")),
            }
            with (
                unittest.mock.patch.multiple(run_close_queue, **patches),
                patch("run_close_queue.save_edit_form"),
                patch("run_close_queue.time.sleep"),
            ):
                entry = close_one_lead(
                    self.driver,
                    LEAD,
                    CONFIG,
                    self.results_path,
                    self.screenshots,
                    unittest.mock.Mock(),
                    "run_x",
                )
        self.assertEqual(entry["status"], "conversion_no_verificada")

    def test_final_owner_mismatch_is_not_success(self):
        wrong_owner = {"estado": "Cerrado", "propietario": "OTRA_COLA", "comentario": "Ilocalizable"}
        entry, _ = self.run_lead([OPEN_STATE, SAVED_STATE] + [wrong_owner] * 10)

        self.assertEqual(entry["status"], "conversion_no_verificada")

    def test_final_verification_waits_for_expected_owner(self):
        """El propietario cambia tras Cerrado: espera hasta el resultado final."""
        pending = {"estado": "Cerrado", "propietario": "Auxiliar X", "comentario": "Ilocalizable"}
        states = [OPEN_STATE, SAVED_STATE, pending, pending, FINAL_STATE]
        entry, patches = self.run_lead(states)

        self.assertEqual(entry["status"], "cerrado_verificado")
        self.assertEqual(patches["read_closure_state"].call_count, 5)

    def test_final_verification_tolerates_loading_state(self):
        """Campos vacíos durante la carga no detienen la espera del resultado final."""
        states = [OPEN_STATE, SAVED_STATE, EMPTY_STATE, EMPTY_STATE, FINAL_STATE]
        entry, _ = self.run_lead(states)

        self.assertEqual(entry["status"], "cerrado_verificado")

    def test_final_verification_times_out_without_repeated_yes(self):
        """Si el propietario nunca llega, registra no verificada y no reintenta."""
        pending = {"estado": "Cerrado", "propietario": "Auxiliar X", "comentario": "Ilocalizable"}
        states = [OPEN_STATE, SAVED_STATE] + [pending] * 10
        entry, patches = self.run_lead(states)

        self.assertEqual(entry["status"], "conversion_no_verificada")
        patches["confirm_conversion"].assert_called_once()
        patches["convert_lead"].assert_called_once()

    def test_final_verification_does_not_reload_while_owner_is_pending(self):
        """Con Cerrado visible, no recarga continuamente: relee en la misma página."""
        pending = {"estado": "Cerrado", "propietario": "Auxiliar X", "comentario": "Ilocalizable"}
        states = [OPEN_STATE, SAVED_STATE, pending, pending, FINAL_STATE]
        entry, patches = self.run_lead(states)

        self.assertEqual(entry["status"], "cerrado_verificado")
        self.assertLessEqual(self.driver.urls.count("https://sf.example/lightning/r/Lead/00Q000000000001AAA/view"), 2)

    def test_colombia_mexico_appends_motive_to_otra_informacion(self):
        """En Colombia/México el motivo se anexa a Otra información y el campo
        Comentario (donde viven los intentos) queda intacto."""
        from comment_reader import COMMENT_LABELS, OTHER_INFORMATION_LABELS

        def field_value(_driver, _timeout, labels):
            return "" if tuple(labels) == tuple(OTHER_INFORMATION_LABELS) else "INT 1 previo"

        def field_text(_driver, labels):
            if tuple(labels) == tuple(OTHER_INFORMATION_LABELS):
                return "Ilocalizable"  # Otra información tras anexar el motivo
            return "INT 1 previo"      # Comentario conserva los intentos

        col_open = {
            "estado": "Nuevo", "propietario": "Auxiliar X",
            "comentario": "INT 1 previo", "motivo": "",
        }
        col_saved = {**col_open, "estado": "Cerrado", "motivo": "Ilocalizable"}
        col_final = {
            "estado": "Cerrado", "propietario": "AR_LEAD_COLD",
            "comentario": "INT 1 previo", "motivo": "Ilocalizable",
        }
        entry, patches = self.run_lead(
            [col_open, col_saved, col_final],
            country="colombia_mexico",
            find_field_value=unittest.mock.Mock(side_effect=field_value),
            find_field_text=unittest.mock.Mock(side_effect=field_text),
        )

        self.assertEqual(entry["status"], "cerrado_verificado")
        self.assertEqual(entry["country"], "colombia_mexico")
        # El motivo va al editor de Otra información, no al Comentario.
        patches["prepare_other_information"].assert_called_once()
        call = patches["prepare_other_information"].call_args
        self.assertEqual(call.kwargs["labels"], OTHER_INFORMATION_LABELS)
        self.assertEqual(call.args[1], "Ilocalizable")
        patches["set_comentario"].assert_not_called()
        # El formulario de Cualificación verifica que Comentario quedó intacto.
        match_call = patches["edit_form_matches"].call_args
        self.assertEqual(match_call.args[2], COMMENT_LABELS)
        self.assertEqual(match_call.args[3], "INT 1 previo")

    def test_colombia_mexico_preserves_previous_text_in_otra_informacion(self):
        """Si Otra información ya tiene texto, el motivo se agrega al final."""
        from comment_reader import OTHER_INFORMATION_LABELS

        previo = "Gestión anterior del asesor"
        appended = f"{previo}\nIlocalizable"

        def field_value(_driver, _timeout, labels):
            if tuple(labels) == tuple(OTHER_INFORMATION_LABELS):
                return previo
            return "INT 1 previo"

        def field_text(_driver, labels):
            if tuple(labels) == tuple(OTHER_INFORMATION_LABELS):
                return appended
            return "INT 1 previo"

        col_open = {
            "estado": "Nuevo", "propietario": "Auxiliar X",
            "comentario": "INT 1 previo", "motivo": previo,
        }
        col_saved = {**col_open, "estado": "Cerrado", "motivo": appended}
        col_final = {
            "estado": "Cerrado", "propietario": "AR_LEAD_COLD",
            "comentario": "INT 1 previo", "motivo": appended,
        }
        entry, patches = self.run_lead(
            [col_open, col_saved, col_final],
            country="colombia_mexico",
            find_field_value=unittest.mock.Mock(side_effect=field_value),
            find_field_text=unittest.mock.Mock(side_effect=field_text),
        )

        self.assertEqual(entry["status"], "cerrado_verificado")
        call = patches["prepare_other_information"].call_args
        # El texto completo conserva el contenido previo + la línea del motivo.
        self.assertEqual(call.args[1], appended)
        patches["set_comentario"].assert_not_called()

    def test_colombia_mexico_fails_if_attempts_field_changed(self):
        """Si Comentario (intentos) cambió al guardar, el cierre se detiene."""
        from comment_reader import OTHER_INFORMATION_LABELS

        preserved_reads = iter(["INT 1 previo", "", "INT alterado"])

        def field_text(_driver, labels):
            if tuple(labels) == tuple(OTHER_INFORMATION_LABELS):
                return "Ilocalizable"
            return "INT 1 previo"

        col_open = {
            "estado": "Nuevo", "propietario": "Auxiliar X",
            "comentario": "INT 1 previo", "motivo": "",
        }
        col_saved = {**col_open, "estado": "Cerrado", "motivo": "Ilocalizable"}
        entry, _ = self.run_lead(
            [col_open, col_saved],
            country="colombia_mexico",
            find_field_value=unittest.mock.Mock(
                side_effect=lambda *_args: next(preserved_reads)
            ),
            find_field_text=unittest.mock.Mock(side_effect=field_text),
        )

        self.assertEqual(entry["status"], "error")

    def test_int_count_is_never_checked(self):
        """La decisión del auxiliar no depende del número de INT: el runner no
        consulta next_attempt_number ni cuenta intentos para autorizar."""
        source = inspect.getsource(run_close_queue)
        self.assertNotIn("next_attempt_number", source)
        self.assertNotIn("INT", inspect.getsource(close_one_lead))


def WebDriverTimeout():
    from selenium.common.exceptions import TimeoutException

    return TimeoutException()


class PersistAndVerifyTests(unittest.TestCase):
    def test_returns_false_when_otra_informacion_changed(self):
        driver = FakeDriver()
        with (
            patch("run_close_queue.save_edit_form"),
            patch("run_close_queue.verify_persisted_fields", return_value=True),
            patch(
                "run_close_queue.read_closure_state",
                return_value={
                    "estado": "Cerrado",
                    "propietario": "Auxiliar X",
                    "comentario": "Ilocalizable",
                },
            ),
            patch("run_close_queue.find_field_value", return_value="otro texto"),
            patch("run_close_queue.wait_for_lightning_ready"),
            patch("run_close_queue.time.sleep"),
        ):
            saved, _reloads = persist_and_verify(driver, "https://sf/lead/1", CONTRACT_ILOCALIZABLE, "hash-original", 5)
        self.assertFalse(saved)


if __name__ == "__main__":
    unittest.main()
