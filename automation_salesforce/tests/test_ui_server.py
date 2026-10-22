import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ui_server import SESSION_FILE, freeze_active_queue, make_handler, write_session_file


class UiServerTests(unittest.TestCase):
    def test_session_file_exposes_port_and_token_for_the_ui(self):
        with TemporaryDirectory() as temporary_directory:
            path = write_session_file(Path(temporary_directory), 8765, "token-de-prueba")
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(path.name, SESSION_FILE)
        self.assertEqual(payload, {"port": 8765, "token": "token-de-prueba"})

    def test_load_or_create_token_reuses_the_saved_token(self):
        """Un reinicio no deja vieja la página abierta: el token se conserva."""
        import ui_server

        with TemporaryDirectory() as tmp:
            (Path(tmp) / SESSION_FILE).write_text(
                json.dumps({"port": 8765, "token": "token-fijo"}), encoding="utf-8"
            )
            self.assertEqual(ui_server.load_or_create_token(Path(tmp)), "token-fijo")

    def test_load_or_create_token_generates_only_when_missing(self):
        import ui_server

        with TemporaryDirectory() as tmp:
            first = ui_server.load_or_create_token(Path(tmp))
            self.assertTrue(first)
            # Un archivo inválido tampoco rompe: genera uno nuevo.
            (Path(tmp) / SESSION_FILE).write_text("{roto", encoding="utf-8")
            second = ui_server.load_or_create_token(Path(tmp))
            self.assertTrue(second)

    def test_instance_lock_blocks_a_second_server(self):
        """En Windows el doble bind del puerto era posible: el lock lo evita."""
        import ui_server

        if ui_server.msvcrt is None:
            self.skipTest("msvcrt solo existe en Windows")
        with TemporaryDirectory() as tmp:
            first = ui_server.acquire_instance_lock(Path(tmp))
            self.assertIsNotNone(first)
            self.assertIsNone(ui_server.acquire_instance_lock(Path(tmp)))
            first.close()
            # Liberado el lock, una instancia nueva puede tomarlo.
            third = ui_server.acquire_instance_lock(Path(tmp))
            self.assertIsNotNone(third)
            third.close()


class UiServerApiTests(unittest.TestCase):
    """El servidor sirve la app y expone los archivos operativos por token."""

    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler("token-x"))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def _get(self, path, token=None):
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        if token:
            request.add_header("X-Bot-Token", token)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def test_root_serves_the_ui_with_the_token_injected(self):
        with patch("ui_server.UI_PAGE") as page:
            page.is_file.return_value = True
            page.read_text.return_value = "<html>token=__BOT_SERVER_TOKEN__</html>"
            status, body = self._get("/")

        self.assertEqual(status, 200)
        self.assertIn(b"token=token-x", body)

    def test_api_requires_the_session_token(self):
        status, _ = self._get("/api/results")
        self.assertEqual(status, 403)

        status, _ = self._get("/api/results", token="token-x")
        self.assertEqual(status, 200)

    def test_api_reads_missing_files_as_empty_list(self):
        with TemporaryDirectory() as tmp, patch("ui_server.API_FILES", {"/api/results": Path(tmp) / "r.json"}):
            status, body = self._get("/api/results", token="token-x")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), [])

    def test_put_queue_writes_only_whitelisted_file(self):
        body = json.dumps({"leads": [{"lead_id": "00Q1", "attempts": []}]}).encode()
        with TemporaryDirectory() as tmp, patch("ui_server.API_FILES", {"/api/queue": Path(tmp) / "q.json"}):
            request = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/queue",
                data=body,
                method="PUT",
                headers={"X-Bot-Token": "token-x", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status, 200)
            written = json.loads((Path(tmp) / "q.json").read_text(encoding="utf-8"))
            self.assertEqual(written["leads"][0]["lead_id"], "00Q1")

    def test_put_rejects_invalid_payload(self):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/queue",
            data=b'{"sin_leads": true}',
            method="PUT",
            headers={"X-Bot-Token": "token-x", "Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code, 400)

    def test_reload_requires_token_and_accepts_post(self):
        """El reload agenda la salida limpia (exit 0) que el guardián relanza."""
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/reload",
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code, 403)

        fired = threading.Event()
        with patch("ui_server._force_clean_exit", side_effect=fired.set) as clean_exit:
            request = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/reload",
                method="POST",
                headers={"X-Bot-Token": "token-x"},
            )
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status, 200)
            # El timer daemon dispara la salida limpia tras responder.
            self.assertTrue(fired.wait(3))
            clean_exit.assert_called_once()

    def test_restart_browser_requires_token_and_accepts_post(self):
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/restart-browser", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code, 403)

        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/restart-browser",
            method="POST",
            headers={"X-Bot-Token": "token-x"},
        )
        completed = threading.Event()
        with patch("ui_server.restart_browser", side_effect=lambda config: completed.set()) as restart:
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status, 202)
            self.assertTrue(completed.wait(5), "El hilo debe finalizar dentro del mock de reinicio")
            restart.assert_called_once()

    def test_probe_retries_a_transient_attach_failure(self):
        """Un fallo rápido (driver cerrándose, página cargando) reintenta una
        vez antes de declarar el puerto no sano — no amerita reinicio."""
        import ui_server

        cfg = {"browser": "edge", "profile_directory": "perfil"}
        driver = unittest.mock.Mock()
        with (
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.create_driver", side_effect=[ValueError("race"), driver]) as create,
            patch("ui_server.release_driver"),
            patch("ui_server.time.sleep"),
        ):
            self.assertTrue(ui_server.debugger_session_attachable(cfg, "127.0.0.1:9222"))
        self.assertEqual(create.call_count, 2)

    def test_probe_does_not_retry_a_wedged_port(self):
        """El timeout de sesión es la señal de puerto trabado: falla directo."""
        import ui_server

        cfg = {"browser": "edge", "profile_directory": "perfil"}
        wedged = RuntimeError("No se pudo conectar al navegador persistente: puerto trabado")
        with (
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.create_driver", side_effect=wedged) as create,
            patch("ui_server.time.sleep"),
        ):
            self.assertFalse(ui_server.debugger_session_attachable(cfg, "127.0.0.1:9222"))
        create.assert_called_once()

    def test_restart_browser_refuses_while_the_bot_runs(self):
        import ui_server

        runner = unittest.mock.Mock()
        runner.poll.return_value = None
        ui_server.current_process = runner
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/restart-browser",
                method="POST",
                headers={"X-Bot-Token": "token-x"},
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request)
            self.assertEqual(ctx.exception.code, 409)
        finally:
            ui_server.current_process = None

    def test_restart_browser_refuses_while_monitor_cycle_active(self):
        import ui_server

        ui_server.monitor_cycle_active = True
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/restart-browser",
                method="POST",
                headers={"X-Bot-Token": "token-x"},
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request)
            self.assertEqual(ctx.exception.code, 409)
            self.assertIn("monitor", ctx.exception.read().decode("utf-8"))
        finally:
            ui_server.monitor_cycle_active = False

    def test_restart_browser_opens_only_the_missing_tabs(self):
        import ui_server

        config = {
            "browser": "edge",
            "debugger_address": "127.0.0.1:9222",
            "profile_directory": "perfil",
            "salesforce_url": "https://sf.example",
        }
        with (
            patch("ui_server.find_listening_pid", return_value=None),
            patch("ui_server.subprocess.run"),
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.launch_persistent_browser") as launch,
            patch("ui_server.wait_for_debugger", return_value=True),
            patch("ui_server.wait_for_restored_tabs") as wait_tabs,
            patch("ui_server.open_missing_tabs", return_value=["http://127.0.0.1:8765/"]) as open_tabs,
        ):
            ui_server.restart_browser(config)
        # El relanzado no pasa URLs: la sesión restaurada ya puede traerlas.
        self.assertEqual(launch.call_args.args[3:], ())
        # Antes de deduplicar se espera a que /json/list refleje las
        # pestañas restauradas (si no, se abrirían duplicadas).
        wait_tabs.assert_called_once_with("127.0.0.1:9222")
        self.assertEqual(
            open_tabs.call_args.args[3],
            ["http://127.0.0.1:8765/", "https://sf.example"],
        )

    def test_restart_browser_skips_tabs_when_the_debugger_never_responds(self):
        import ui_server

        config = {
            "browser": "edge",
            "debugger_address": "127.0.0.1:9222",
            "profile_directory": "perfil",
            "salesforce_url": "https://sf.example",
        }
        with (
            patch("ui_server.find_listening_pid", return_value=None),
            patch("ui_server.subprocess.run"),
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.launch_persistent_browser"),
            patch("ui_server.wait_for_debugger", return_value=False),
            patch("ui_server.open_missing_tabs") as open_tabs,
        ):
            ui_server.restart_browser(config)
        open_tabs.assert_not_called()

    def test_find_listening_pid_parses_netstat(self):
        import ui_server

        netstat_out = (
            "  TCP    127.0.0.1:9222         0.0.0.0:0              LISTENING       4242\n"
            "  TCP    127.0.0.1:8765         0.0.0.0:0              LISTENING       9999\n"
        )
        with patch("ui_server.subprocess.run") as run:
            run.return_value.stdout = netstat_out
            self.assertEqual(ui_server.find_listening_pid("9222"), "4242")
            self.assertIsNone(ui_server.find_listening_pid("1234"))

    def test_freeze_active_queue_writes_immutable_run_copy(self):
        with TemporaryDirectory() as tmp:
            queue_directory = Path(tmp)
            (queue_directory / "cola_activa.json").write_text(
                json.dumps({"leads": [{"lead_id": "00Q1", "attempts": []}], "source_file": "f.csv"}),
                encoding="utf-8",
            )

            frozen = freeze_active_queue(queue_directory, "run_20261001T000000Z_ab12cd")

            payload = json.loads(frozen.read_text(encoding="utf-8"))
            self.assertEqual(frozen.name, "run_20261001T000000Z_ab12cd.json")
            self.assertEqual(payload["run_id"], "run_20261001T000000Z_ab12cd")
            self.assertIn("frozen_at", payload)
            self.assertEqual(payload["source_file"], "f.csv")
            # La cola activa original no se modifica.
            active = json.loads((queue_directory / "cola_activa.json").read_text(encoding="utf-8"))
            self.assertNotIn("run_id", active)

    def _post_run(self):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/run",
            method="POST",
            headers={"X-Bot-Token": "token-x"},
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_run_freezes_the_queue_and_passes_run_id_to_the_runner(self):
        import ui_server

        with (
            TemporaryDirectory() as tmp,
            patch.object(ui_server, "ROOT", Path(tmp)),
            patch.object(ui_server, "load_config", return_value={}),
            patch("ui_server.debugger_is_listening", return_value=True),
            patch("ui_server.debugger_http_ready", return_value=True),
            patch("ui_server.debugger_session_attachable", return_value=True),
            patch("ui_server.subprocess.Popen") as popen,
        ):
            (Path(tmp) / "queues").mkdir()
            (Path(tmp) / "queues" / "cola_activa.json").write_text(
                json.dumps(
                    {
                        "country": "colombia_mexico",
                        "leads": [
                            {
                                "lead_id": "00Q000000000001AAA",
                                "attempts": [
                                    {
                                        "result": "No contesta",
                                        "date": "1/10/2026",
                                        "time": "10:00",
                                        "call_id": "MX-001",
                                    },
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            popen.return_value.poll.return_value = None
            status, payload = self._post_run()

            self.assertEqual(status, 202)
            argv = popen.call_args.args[0]
            self.assertIn("--run-id", argv)
            self.assertIn(payload["run_id"], argv)
            frozen = Path(tmp) / "queues" / f"{payload['run_id']}.json"
            self.assertTrue(frozen.is_file())
            self.assertEqual(json.loads(frozen.read_text())["run_id"], payload["run_id"])
        ui_server.current_process = None

    def test_run_rejects_empty_documentation_even_after_a_previous_process(self):
        import ui_server

        previous = unittest.mock.Mock(returncode=2)
        previous.poll.return_value = 2
        with (
            TemporaryDirectory() as tmp,
            patch.object(ui_server, "ROOT", Path(tmp)),
            patch.object(ui_server, "current_process", previous),
            patch.object(ui_server, "load_config", return_value={}),
            patch("ui_server.debugger_is_listening", return_value=True),
            patch("ui_server.debugger_http_ready", return_value=True),
            patch("ui_server.debugger_session_attachable", return_value=True),
            patch("ui_server.subprocess.Popen") as popen,
        ):
            queue_directory = Path(tmp) / "queues"
            queue_directory.mkdir()
            (queue_directory / "cola_activa.json").write_text('{"leads": []}', encoding="utf-8")
            status, payload = self._post_run()
            self.assertEqual(status, 400)
            self.assertIn("cola", payload["error"].lower())
            popen.assert_not_called()

    def test_run_rejects_when_the_dedicated_browser_is_closed(self):
        import ui_server

        with (
            TemporaryDirectory() as tmp,
            patch.object(ui_server, "ROOT", Path(tmp)),
            patch.object(ui_server, "load_config", return_value={}),
            patch("ui_server.debugger_is_listening", return_value=False),
            patch("ui_server.subprocess.Popen") as popen,
        ):
            status, payload = self._post_run()

        self.assertEqual(status, 503)
        self.assertIn("no está abierto", payload["error"])
        popen.assert_not_called()
        self.assertFalse((Path(tmp) / "queues").exists())

    def test_run_rejects_when_the_debugger_port_is_wedged(self):
        import ui_server

        with (
            TemporaryDirectory() as tmp,
            patch.object(ui_server, "ROOT", Path(tmp)),
            patch.object(ui_server, "load_config", return_value={}),
            patch("ui_server.debugger_is_listening", return_value=True),
            patch("ui_server.debugger_http_ready", return_value=False),
            patch("ui_server.debugger_session_attachable", return_value=False),
            patch("ui_server.restart_browser") as restart,
            patch("ui_server.subprocess.Popen") as popen,
        ):
            status, payload = self._post_run()

        self.assertEqual(status, 503)
        self.assertIn("trabado", payload["error"])
        restart.assert_called_once()
        popen.assert_not_called()

    def test_run_recovers_a_wedged_debugger_by_restarting_the_browser_once(self):
        import ui_server

        with (
            TemporaryDirectory() as tmp,
            patch.object(ui_server, "ROOT", Path(tmp)),
            patch.object(ui_server, "load_config", return_value={}),
            patch("ui_server.debugger_is_listening", return_value=True),
            # El puerto responde /json pero la sesión de Selenium no se crea:
            # es el estado trabado real. Tras el reinicio la sonda ya pasa.
            patch("ui_server.debugger_http_ready", return_value=True),
            patch(
                "ui_server.debugger_session_attachable",
                side_effect=[False, True],
            ) as probe,
            patch("ui_server.restart_browser") as restart,
            patch("ui_server.subprocess.Popen") as popen,
        ):
            (Path(tmp) / "queues").mkdir()
            (Path(tmp) / "queues" / "cola_activa.json").write_text(
                json.dumps(
                    {
                        "country": "argentina",
                        "leads": [
                            {
                                "lead_id": "00Q000000000001AAA",
                                "attempts": [
                                    {
                                        "result": "No contesta",
                                        "date": "1/10/2026",
                                        "time": "10:00",
                                        "call_id": "AR-001",
                                    },
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            popen.return_value.poll.return_value = None
            status, payload = self._post("/run")

            self.assertEqual(status, 202)
            restart.assert_called_once()
            self.assertEqual(probe.call_count, 2)
            popen.assert_called_once()
        ui_server.current_process = None
        ui_server.current_operation = None

    def _post(self, path):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            method="POST",
            headers={"X-Bot-Token": "token-x"},
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def _put(self, path, payload):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload).encode(),
            method="PUT",
            headers={"X-Bot-Token": "token-x", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def _valid_close_queue(self):
        return {
            "operation": "close_leads",
            "generated_at": "t",
            "leads": [{"lead_id": "00Q000000000001AAA", "reason": "ilocalizable"}],
        }

    def test_put_close_queue_validates_reasons(self):
        with TemporaryDirectory() as tmp, patch("ui_server.API_FILES", {"/api/close-queue": Path(tmp) / "c.json"}):
            status, payload = self._put("/api/close-queue", self._valid_close_queue())
            self.assertEqual(status, 200)

            bad = {"operation": "close_leads", "leads": [{"lead_id": "00Q000000000001AAA", "reason": "x"}]}
            status, payload = self._put("/api/close-queue", bad)
            self.assertEqual(status, 400)
            self.assertIn("motivo", payload["error"])

            missing_op = {"leads": [{"lead_id": "00Q000000000001AAA", "reason": "ilocalizable"}]}
            status, _ = self._put("/api/close-queue", missing_op)
            self.assertEqual(status, 400)

    def test_close_results_endpoint_reads_only_whitelisted_file(self):
        status, _ = self._get("/api/close-results")
        self.assertEqual(status, 403)
        with TemporaryDirectory() as tmp, patch("ui_server.API_FILES", {"/api/close-results": Path(tmp) / "r.json"}):
            status, body = self._get("/api/close-results", token="token-x")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), [])

    def test_run_close_freezes_and_launches_close_runner(self):
        import ui_server

        with (
            TemporaryDirectory() as tmp,
            patch.object(ui_server, "ROOT", Path(tmp)),
            patch.object(ui_server, "load_config", return_value={}),
            patch("ui_server.debugger_is_listening", return_value=True),
            patch("ui_server.debugger_http_ready", return_value=True),
            patch("ui_server.debugger_session_attachable", return_value=True),
            patch("ui_server.subprocess.Popen") as popen,
        ):
            (Path(tmp) / "queues").mkdir()
            (Path(tmp) / "queues" / "cola_cierre_activa.json").write_text(
                json.dumps(self._valid_close_queue()), encoding="utf-8"
            )
            popen.return_value.poll.return_value = None
            status, payload = self._post("/run-close")

            self.assertEqual(status, 202)
            argv = popen.call_args.args[0]
            self.assertIn("run_close_queue.py", argv[1])
            self.assertIn("--run-id", argv)
            frozen = Path(tmp) / "queues" / f"cierre_{payload['run_id']}.json"
            self.assertTrue(frozen.is_file())
            self.assertEqual(json.loads(frozen.read_text())["run_id"], payload["run_id"])
            self.assertEqual(ui_server.current_operation, "cierre")
        ui_server.current_process = None
        ui_server.current_operation = None

    def test_run_close_rejects_invalid_queue_without_spawn(self):
        import ui_server

        with (
            TemporaryDirectory() as tmp,
            patch.object(ui_server, "ROOT", Path(tmp)),
            patch.object(ui_server, "load_config", return_value={}),
            patch("ui_server.debugger_is_listening", return_value=True),
            patch("ui_server.debugger_http_ready", return_value=True),
            patch("ui_server.debugger_session_attachable", return_value=True),
            patch("ui_server.subprocess.Popen") as popen,
        ):
            (Path(tmp) / "queues").mkdir()
            (Path(tmp) / "queues" / "cola_cierre_activa.json").write_text(
                json.dumps({"operation": "close_leads", "leads": [{"lead_id": "x", "reason": "?"}]}),
                encoding="utf-8",
            )
            status, payload = self._post("/run-close")

        self.assertEqual(status, 400)
        self.assertIn("inválida", payload["error"])
        popen.assert_not_called()

    def test_run_close_rejects_missing_queue_without_spawn(self):
        import ui_server

        with (
            TemporaryDirectory() as tmp,
            patch.object(ui_server, "ROOT", Path(tmp)),
            patch.object(ui_server, "load_config", return_value={}),
            patch("ui_server.debugger_is_listening", return_value=True),
            patch("ui_server.debugger_http_ready", return_value=True),
            patch("ui_server.debugger_session_attachable", return_value=True),
            patch("ui_server.subprocess.Popen") as popen,
        ):
            (Path(tmp) / "queues").mkdir()
            status, payload = self._post("/run-close")

        self.assertEqual(status, 400)
        popen.assert_not_called()

    def test_status_reports_operation_while_running(self):
        import ui_server

        runner = unittest.mock.Mock()
        runner.poll.return_value = None
        ui_server.current_process = runner
        ui_server.current_operation = "cierre"
        try:
            status, body = self._get("/status")
        finally:
            ui_server.current_process = None
            ui_server.current_operation = None
        self.assertEqual(json.loads(body)["operation"], "cierre")


class UiServerMonitorTests(unittest.TestCase):
    """Endpoints y ciclo del Monitor de Bandeja."""

    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler("token-x"))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def _request(self, method, path, payload=None, token="token-x"):
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method)
        if token:
            request.add_header("X-Bot-Token", token)
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, data=body) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def _state_file(self, tmp):
        return Path(tmp) / "monitor_state.json"

    def test_monitor_state_requires_token(self):
        status, _ = self._request("GET", "/api/monitor", token=None)
        self.assertEqual(status, 403)

    def test_monitor_state_payload(self):

        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            status, payload = self._request("GET", "/api/monitor")
        self.assertEqual(status, 200)
        self.assertFalse(payload["enabled"])
        self.assertEqual(payload["bandejas"], [])
        self.assertEqual(payload["schedule"], [])

    def test_toggle_flips_and_persists_enabled(self):

        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            status, payload = self._request("POST", "/api/monitor/toggle")
            self.assertEqual(status, 200)
            self.assertTrue(payload["enabled"])
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertTrue(saved["enabled"])

            status, payload = self._request("POST", "/api/monitor/toggle", {"enabled": False})
            self.assertFalse(payload["enabled"])

    def test_monitor_config_validates_bandejas(self):

        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            good = {
                "bandejas": [
                    {
                        "code": "AR",
                        "enabled": True,
                        "url": "https://sf.example/lightning/r/Report/00O1/view",
                    }
                ]
            }
            status, _ = self._request("PUT", "/api/monitor/config", good)
            self.assertEqual(status, 200)
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertEqual(saved["bandejas"][0]["unassigned_owner"], "AR_LEAD_QUALIF")

            bad = {"bandejas": [{"code": "AR", "url": "http://no-seguro"}]}
            status, payload = self._request("PUT", "/api/monitor/config", bad)
            self.assertEqual(status, 400)
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertEqual(len(saved["bandejas"]), 1)  # la inválida no pisa la válida

    def test_monitor_schedule_validates_and_persists(self):

        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            status, _ = self._request(
                "PUT", "/api/monitor/schedule", {"schedule": [{"start": "08:00", "end": "20:00"}]}
            )
            self.assertEqual(status, 200)
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertEqual(saved["schedule"], [{"start": "08:00", "end": "20:00"}])

            status, payload = self._request(
                "PUT",
                "/api/monitor/schedule",
                {"schedule": [{"start": "18:00", "end": "09:00"}]},
            )
            self.assertEqual(status, 400)

    def test_monitor_equipo_validates_and_persists(self):
        equipo = [
            {
                "nombre": "Micaela Caetano",
                "franjas": [{"start": "09:00", "end": "12:00"}],
            }
        ]
        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            status, _ = self._request("PUT", "/api/monitor/equipo", {"equipo": equipo})
            self.assertEqual(status, 200)
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertEqual(saved["equipo"], equipo)

            status, _ = self._request(
                "PUT",
                "/api/monitor/equipo",
                {"equipo": [{"nombre": "", "franjas": []}]},
            )
            self.assertEqual(status, 400)
            status, _ = self._request(
                "PUT",
                "/api/monitor/equipo",
                {"equipo": [{"nombre": "Ana", "franjas": [{"start": "18:00", "end": "09:00"}]}]},
            )
            self.assertEqual(status, 400)
            # Ninguna inválida pisó el equipo válido.
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertEqual(saved["equipo"], equipo)

    def test_ui_prefs_roundtrip(self):
        """Las preferencias de UI persisten del lado del servidor: la vista
        de columnas sobrevive aunque el usuario cambie de navegador o su
        perfil borre el localStorage."""
        with TemporaryDirectory() as tmp, patch(
            "ui_server.ui_prefs_path", return_value=Path(tmp) / "ui_prefs.json"
        ):
            status, payload = self._request("GET", "/api/ui-prefs")
            self.assertEqual(status, 200)
            self.assertEqual(payload["prefs"], {})

            cols = {"hidden": ["email"], "order": ["num", "hace"], "widths": {"num": 40}}
            status, _ = self._request("PUT", "/api/ui-prefs", {"prefs": {"monitorColsV1": cols}})
            self.assertEqual(status, 200)

            status, payload = self._request("GET", "/api/ui-prefs")
            self.assertEqual(payload["prefs"]["monitorColsV1"], cols)

            # Un segundo PUT mergea sin borrar lo anterior.
            status, _ = self._request("PUT", "/api/ui-prefs", {"prefs": {"monitorSound": False}})
            self.assertEqual(status, 200)
            status, payload = self._request("GET", "/api/ui-prefs")
            self.assertEqual(payload["prefs"]["monitorColsV1"], cols)
            self.assertIs(payload["prefs"]["monitorSound"], False)

    def test_ui_prefs_validates_input(self):
        with TemporaryDirectory() as tmp, patch(
            "ui_server.ui_prefs_path", return_value=Path(tmp) / "ui_prefs.json"
        ):
            status, _ = self._request("PUT", "/api/ui-prefs", {"otro": {}})
            self.assertEqual(status, 400)
            status, _ = self._request("PUT", "/api/ui-prefs", {"prefs": {"../evil": 1}})
            self.assertEqual(status, 400)
            status, _ = self._request("PUT", "/api/ui-prefs", {"prefs": {"": 1}})
            self.assertEqual(status, 400)

    def test_ui_prefs_requires_token(self):
        status, _ = self._request("GET", "/api/ui-prefs", token=None)
        self.assertEqual(status, 403)
        status, _ = self._request("PUT", "/api/ui-prefs", {"prefs": {"a": 1}}, token=None)
        self.assertEqual(status, 403)

    def test_cycle_merge_preserves_user_changes_made_mid_cycle(self):
        """El ciclo lee el estado al arrancar: al escribir no debe pisar el
        toggle ni el "Limpiar lista" que el usuario hizo mientras corría."""
        import ui_server
        from monitor_store import default_state, save_state

        with TemporaryDirectory() as tmp:
            state_file = self._state_file(tmp)
            disk = default_state()
            disk["results"] = [{"lead_id": "L1", "status": "detectado"}]
            save_state(state_file, disk)

            # Lo que el ciclo leyó al empezar y lo que produjo.
            cycle_state = default_state()
            cycle_state["results"] = [
                {"lead_id": "L1", "status": "tomado"},  # actualizado por el ciclo
                {"lead_id": "L2", "status": "detectado"},  # nuevo del ciclo
            ]
            cycle_state["last_cycle_at"] = "2026-10-10T20:00:00+00:00"
            cycle_state["paused_reason"] = None
            pre_results = {"L1": {"lead_id": "L1", "status": "detectado"}}

            # El usuario actuó durante el ciclo: apagó el modo prueba y limpió.
            with patch("ui_server.monitor_state_path", return_value=state_file):
                fresh = ui_server.monitor_read_state({})
                fresh["solo_listar"] = False
                fresh["enabled"] = True
                fresh["results"] = []
                ui_server.monitor_write_state({}, fresh)

                merged = ui_server._merge_cycle_state({}, cycle_state, pre_results)

            self.assertFalse(merged["solo_listar"])  # no resucita el valor viejo
            self.assertTrue(merged["enabled"])
            self.assertEqual(
                merged["results"], [{"lead_id": "L1", "status": "tomado"}, {"lead_id": "L2", "status": "detectado"}]
            )
            self.assertEqual(merged["last_cycle_at"], "2026-10-10T20:00:00+00:00")

    def test_events_requires_token_via_query(self):

        request = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/events")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 403)

    def test_events_stream_delivers_broadcast(self):
        import ui_server

        request = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/events?token=token-x")
        response = urllib.request.urlopen(request, timeout=5)
        try:
            self.assertEqual(response.headers.get("Content-Type"), "text/event-stream")
            first = response.readline()  # ": conectado"
            ui_server.broadcast_event({"type": "monitor", "status": "tomado"})
            lines = [first, response.readline(), response.readline()]
            data = next(line for line in lines if line.startswith(b"data:"))
            self.assertIn(b'"tomado"', data)
        finally:
            response.close()

    def test_broadcast_tolerates_disconnected_subscriber(self):
        import ui_server

        broken = unittest.mock.Mock()
        broken.put_nowait.side_effect = Exception("closed")
        ui_server.event_subscribers.append(broken)
        try:
            ui_server.broadcast_event({"type": "ping"})
        finally:
            ui_server.event_subscribers.remove(broken)

    def test_manual_check_endpoint_accepts_and_rejects_duplicates(self):
        with patch("ui_server.start_manual_check", return_value=True) as start:
            status, _ = self._request("POST", "/api/monitor/check")
            self.assertEqual(status, 202)
            start.assert_called_once()
        with patch("ui_server.start_manual_check", return_value=False):
            status, payload = self._request("POST", "/api/monitor/check")
            self.assertEqual(status, 409)
            self.assertIn("revision", payload["error"])

    def test_manual_check_requires_token(self):
        status, _ = self._request("POST", "/api/monitor/check", token=None)
        self.assertEqual(status, 403)

    def test_dry_run_endpoint_persists_flag(self):
        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            status, payload = self._request("POST", "/api/monitor/dry-run", {"solo_listar": True})
            self.assertEqual(status, 200)
            self.assertTrue(payload["solo_listar"])
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertTrue(saved["solo_listar"])

    def test_dry_run_requires_token(self):
        status, _ = self._request("POST", "/api/monitor/dry-run", {"solo_listar": True}, token=None)
        self.assertEqual(status, 403)

    def test_whatsapp_endpoint_persists_flag(self):
        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            status, payload = self._request("POST", "/api/monitor/whatsapp", {"enviar_whatsapp": True})
            self.assertEqual(status, 200)
            self.assertTrue(payload["enviar_whatsapp"])
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertTrue(saved["enviar_whatsapp"])
            # Apagado por defecto y toggle sin body invierte el estado.
            status, payload = self._request("POST", "/api/monitor/whatsapp")
            self.assertEqual(status, 200)
            self.assertFalse(payload["enviar_whatsapp"])

    def test_whatsapp_requires_token(self):
        status, _ = self._request("POST", "/api/monitor/whatsapp", {"enviar_whatsapp": True}, token=None)
        self.assertEqual(status, 403)

    def test_monitor_payload_includes_enviar_whatsapp(self):
        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            _, payload = self._request("GET", "/api/monitor")
            self.assertIn("enviar_whatsapp", payload)
            self.assertFalse(payload["enviar_whatsapp"])

    def test_clear_monitor_results_preserves_configuration(self):
        from monitor_store import STATUS_DETECTADO, default_state, record_result, save_state, validate_bandejas

        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            state = default_state()
            state["enabled"] = True
            state["solo_listar"] = True
            state["bandejas"] = validate_bandejas(
                [
                    {
                        "code": "AR",
                        "enabled": True,
                        "url": "https://sf.example/lightning/r/Report/00O1/view",
                    }
                ]
            )
            state["schedule"] = [{"start": "08:00", "end": "20:00"}]
            record_result(state, "00Q000000000001AAA", "AR", STATUS_DETECTADO)
            save_state(self._state_file(tmp), state)

            status, payload = self._request("POST", "/api/monitor/clear-results")

            self.assertEqual(status, 200)
            self.assertEqual(payload, {"status": "lista limpiada", "removed": 1})
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertEqual(saved["results"], [])
            self.assertTrue(saved["enabled"])
            self.assertTrue(saved["solo_listar"])
            self.assertEqual(saved["bandejas"], state["bandejas"])
            self.assertEqual(saved["schedule"], state["schedule"])

    def test_clear_monitor_results_rejects_cycle_in_progress(self):
        import ui_server
        from monitor_store import STATUS_DETECTADO, default_state, record_result, save_state

        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            state = default_state()
            record_result(state, "00Q000000000001AAA", "AR", STATUS_DETECTADO)
            save_state(self._state_file(tmp), state)
            self.assertTrue(ui_server.cycle_lock.acquire(blocking=False))
            try:
                status, payload = self._request("POST", "/api/monitor/clear-results")
            finally:
                ui_server.cycle_lock.release()

            self.assertEqual(status, 409)
            self.assertIn("revision", payload["error"])
            saved = json.loads(self._state_file(tmp).read_text(encoding="utf-8"))
            self.assertEqual(len(saved["results"]), 1)

    def test_clear_monitor_results_requires_token(self):
        status, _ = self._request("POST", "/api/monitor/clear-results", token=None)
        self.assertEqual(status, 403)

    def test_run_rejected_while_monitor_cycle_active(self):
        """El bot de documentación/cierre no puede arrancar con el monitor a mitad de ciclo."""
        import ui_server

        ui_server.monitor_cycle_active = True
        try:
            for route in ("/run", "/run-close"):
                status, payload = self._request("POST", route)
                self.assertEqual(status, 409, route)
                self.assertIn("Monitor de Bandeja", payload["error"])
        finally:
            ui_server.monitor_cycle_active = False

    def test_status_reports_monitor_cycle(self):
        import ui_server

        ui_server.monitor_cycle_active = True
        try:
            status, payload = self._request("GET", "/status", token=None)
            self.assertEqual(status, 200)
            self.assertTrue(payload["monitor_cycle"])
        finally:
            ui_server.monitor_cycle_active = False

    def test_monitor_payload_includes_solo_listar_and_cycle(self):
        with TemporaryDirectory() as tmp, patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
            status, payload = self._request("GET", "/api/monitor")
        self.assertEqual(status, 200)
        self.assertFalse(payload["solo_listar"])
        self.assertIn("cycle_running", payload)
        self.assertIn("bot_running", payload)


class MonitorTickTests(unittest.TestCase):
    """Un ciclo del monitor con el navegador simulado."""

    def setUp(self):
        import ui_server

        ui_server.monitor_driver = None

    def tearDown(self):
        import ui_server

        ui_server.monitor_driver = None
        ui_server.monitor_cycle_active = False
        ui_server.monitor_window_handle = None

    def _config(self, tmp):
        return {
            "browser": "edge",
            "profile_directory": "perfil",
            "ui_output_directory": "ui_output",
            "timeouts": {"page_load_seconds": 5},
        }

    def _enabled_state(self, tmp):
        from monitor_store import validate_bandejas

        state_path = Path(tmp) / "monitor_state.json"
        from monitor_store import default_state, save_state

        state = default_state()
        state["enabled"] = True
        # Sin franjas (propias o del equipo) el monitor no toma nada: el
        # estado "habilitado" del test incluye una franja que cubre todo el
        # día para que el ciclo corra.
        state["schedule"] = [{"start": "00:00", "end": "23:59"}]
        state["bandejas"] = validate_bandejas(
            [
                {
                    "code": "AR",
                    "enabled": True,
                    "url": "https://sf.example/lightning/r/Report/00O1/view",
                }
            ]
        )
        save_state(state_path, state)
        return patch("ui_server.monitor_state_path", return_value=state_path)

    def test_tick_does_nothing_when_disabled(self):
        import ui_server

        with TemporaryDirectory() as tmp:
            with patch("ui_server.monitor_state_path", return_value=self._state_file(tmp)):
                events = ui_server.monitor_tick(self._config(tmp))
            self.assertEqual(events, [])

    def _state_file(self, tmp):
        return Path(tmp) / "monitor_state.json"

    def test_tick_pauses_while_a_run_is_active(self):
        import ui_server

        runner = unittest.mock.Mock()
        runner.poll.return_value = None
        ui_server.current_process = runner
        try:
            with TemporaryDirectory() as tmp, self._enabled_state(tmp), patch("ui_server.detect_browser") as detect:
                events = ui_server.monitor_tick(self._config(tmp))
                self.assertEqual(events, [])
                detect.assert_not_called()
                saved = json.loads((Path(tmp) / "monitor_state.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["paused_reason"], "run_activo")
        finally:
            ui_server.current_process = None

    def test_tick_pauses_outside_schedule(self):
        import ui_server

        with TemporaryDirectory() as tmp, self._enabled_state(tmp):
            state_path = Path(tmp) / "monitor_state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["schedule"] = [{"start": "00:00", "end": "00:01"}]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with patch("ui_server.detect_browser") as detect:
                events = ui_server.monitor_tick(self._config(tmp))
            self.assertEqual(events, [])
            detect.assert_not_called()
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["paused_reason"], "fuera_de_horario")

    def test_tick_pauses_without_any_shift(self):
        """Sin franja propia ni del equipo no hay turno: el monitor no toma
        leads — esperan en la cola."""
        import ui_server

        with TemporaryDirectory() as tmp, self._enabled_state(tmp):
            state_path = Path(tmp) / "monitor_state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["schedule"] = []
            state["equipo"] = []
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with patch("ui_server.detect_browser") as detect:
                events = ui_server.monitor_tick(self._config(tmp))
            self.assertEqual(events, [])
            detect.assert_not_called()
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["paused_reason"], "fuera_de_horario")

    def test_tick_runs_when_team_shift_active(self):
        """Sin franja propia pero con franja del equipo vigente: el ciclo
        corre (los leads se reasignan a esa persona)."""
        import ui_server

        with TemporaryDirectory() as tmp, self._enabled_state(tmp):
            state_path = Path(tmp) / "monitor_state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["schedule"] = []
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with (
                patch(
                    "ui_server._encargada_activa",
                    return_value={"nombre": "Ana", "franjas": [{"start": "00:00", "end": "23:59"}]},
                ),
                patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
                patch("ui_server.create_driver", return_value=object()),
                patch("ui_server.ensure_monitor_window"),
                patch("ui_server.release_driver"),
                patch("ui_server.run_cycle", return_value=[]) as cycle,
            ):
                ui_server.monitor_tick(self._config(tmp))
                cycle.assert_called_once()

    def test_manual_check_without_shift_lists_only(self):
        """Revisión manual sin turno vigente: corre en modo prueba — lista
        `detectado` sin tomar leads ni persistir el flag."""
        import ui_server

        with TemporaryDirectory() as tmp, self._enabled_state(tmp):
            state_path = Path(tmp) / "monitor_state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["schedule"] = []
            state["equipo"] = []
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with (
                patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
                patch("ui_server.create_driver", return_value=object()),
                patch("ui_server.ensure_monitor_window"),
                patch("ui_server.release_driver"),
                patch("ui_server.run_cycle", return_value=[]) as cycle,
            ):
                ui_server._monitor_cycle(self._config(tmp), force=True)
            cycle.assert_called_once()
            self.assertTrue(cycle.call_args.args[2]["solo_listar"])
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertFalse(saved["solo_listar"])

    def test_auto_restart_after_repeated_wedged_cycles(self):
        """Tras AUTO_RESTART_AFTER_FAILURES ciclos seguidos sin conectar al
        navegador, el dedicado se reinicia solo (una vez)."""
        import time

        import ui_server

        ui_server.consecutive_browser_failures = 0
        # Pasado el cooldown pero dentro del reinicio programado de 4 h —
        # así el único restart posible es el automático por fallos.
        ui_server.browser_started_monotonic = (
            time.monotonic() - ui_server.AUTO_RESTART_COOLDOWN_SECONDS - 1
        )
        try:
            with TemporaryDirectory() as tmp, self._enabled_state(tmp):
                with (
                    patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
                    patch(
                        "ui_server.create_driver",
                        side_effect=RuntimeError("El puerto de depuración parece trabado"),
                    ),
                    patch("ui_server.restart_browser") as restart,
                ):
                    for _ in range(ui_server.AUTO_RESTART_AFTER_FAILURES + 1):
                        ui_server.monitor_tick(self._config(tmp))
                restart.assert_called_once()
        finally:
            ui_server.consecutive_browser_failures = 0
            ui_server.browser_started_monotonic = time.monotonic()

    def test_auto_restart_waits_for_threshold(self):
        """Menos ciclos fallidos que el umbral no reinician nada."""
        import time

        import ui_server

        ui_server.consecutive_browser_failures = 0
        ui_server.browser_started_monotonic = (
            time.monotonic() - ui_server.AUTO_RESTART_COOLDOWN_SECONDS - 1
        )
        try:
            with TemporaryDirectory() as tmp, self._enabled_state(tmp):
                with (
                    patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
                    patch(
                        "ui_server.create_driver",
                        side_effect=RuntimeError("El puerto de depuración parece trabado"),
                    ),
                    patch("ui_server.restart_browser") as restart,
                ):
                    for _ in range(ui_server.AUTO_RESTART_AFTER_FAILURES - 1):
                        ui_server.monitor_tick(self._config(tmp))
                restart.assert_not_called()
        finally:
            ui_server.consecutive_browser_failures = 0
            ui_server.browser_started_monotonic = time.monotonic()

    def test_auto_restart_respects_recent_restart_cooldown(self):
        """Si el navegador se reinició hace menos del cooldown, no se
        reinicia en bucle aunque los ciclos sigan fallando."""
        import time

        import ui_server

        ui_server.consecutive_browser_failures = 0
        ui_server.browser_started_monotonic = time.monotonic()
        try:
            with TemporaryDirectory() as tmp, self._enabled_state(tmp):
                with (
                    patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
                    patch(
                        "ui_server.create_driver",
                        side_effect=RuntimeError("El puerto de depuración parece trabado"),
                    ),
                    patch("ui_server.restart_browser") as restart,
                ):
                    for _ in range(ui_server.AUTO_RESTART_AFTER_FAILURES + 2):
                        ui_server.monitor_tick(self._config(tmp))
                restart.assert_not_called()
        finally:
            ui_server.consecutive_browser_failures = 0
            ui_server.browser_started_monotonic = time.monotonic()

    def test_restart_browser_closes_leftover_blank_tab(self):
        """El relanzado abre about:blank como URL inicial: se cierra cuando
        quedan otras pestañas, para no acumular una vacía por reinicio."""
        import ui_server

        config = {
            "browser": "edge",
            "debugger_address": "127.0.0.1:9222",
            "profile_directory": "perfil",
            "salesforce_url": "https://sf.example",
        }
        targets = [
            {"id": "blank", "url": "about:blank"},
            {"id": "app", "url": "http://127.0.0.1:8765/"},
            {"id": "sf", "url": "https://sf.example"},
        ]
        with (
            patch("ui_server.find_listening_pid", return_value=None),
            patch("ui_server.subprocess.run"),
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.launch_persistent_browser"),
            patch("ui_server.wait_for_debugger", return_value=True),
            patch("ui_server.wait_for_restored_tabs"),
            patch("ui_server.open_missing_tabs"),
            patch("ui_server.debugger_tab_targets", return_value=targets),
            patch("ui_server.close_stuck_debugger_targets") as close_targets,
        ):
            ui_server.restart_browser(config)
        close_targets.assert_called_once_with("127.0.0.1:9222", url_prefixes=("about:blank",))

    def test_restart_browser_keeps_blank_when_it_is_the_only_tab(self):
        """Si about:blank es la única pestaña no se cierra: tumbaría el
        navegador entero."""
        import ui_server

        config = {
            "browser": "edge",
            "debugger_address": "127.0.0.1:9222",
            "profile_directory": "perfil",
            "salesforce_url": "https://sf.example",
        }
        with (
            patch("ui_server.find_listening_pid", return_value=None),
            patch("ui_server.subprocess.run"),
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.launch_persistent_browser"),
            patch("ui_server.wait_for_debugger", return_value=True),
            patch("ui_server.wait_for_restored_tabs"),
            patch("ui_server.open_missing_tabs"),
            patch("ui_server.debugger_tab_targets", return_value=[{"id": "b", "url": "about:blank"}]),
            patch("ui_server.close_stuck_debugger_targets") as close_targets,
        ):
            ui_server.restart_browser(config)
        close_targets.assert_not_called()

    def test_tick_runs_cycle_and_toasts_on_taken(self):
        import ui_server

        events_result = [{"type": "lead_result", "bandeja": "AR", "status": "tomado", "entry": {}}]
        with (
            TemporaryDirectory() as tmp,
            self._enabled_state(tmp),
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.create_driver", return_value=object()) as create,
            patch("ui_server.ensure_monitor_window"),
            patch("ui_server.release_driver") as release,
            patch("ui_server.run_cycle", return_value=events_result),
            patch("ui_server.windows_toast") as toast,
            patch("ui_server.broadcast_event") as broadcast,
        ):
            events = ui_server.monitor_tick(self._config(tmp))
        self.assertEqual(events, events_result)
        create.assert_called_once()
        release.assert_not_called()  # la sesión del monitor sobrevive al ciclo
        toast.assert_called_once()
        lead_results = [c.args[0] for c in broadcast.call_args_list if c.args[0]["type"] == "lead_result"]
        self.assertEqual(lead_results, events_result)

    def test_tick_toasts_once_per_fresh_detected_lead(self):
        """El aviso "lead nuevo en bandeja" suena una vez por lead: un
        detectado que ya figura en la lista no vuelve a tostar en cada ciclo."""
        import ui_server
        from monitor_store import record_result

        detected = [
            {
                "type": "lead_result",
                "bandeja": "AR",
                "status": "detectado",
                "entry": {"lead_id": "00Q000000000001AAA"},
            }
        ]

        def _cycle(driver, config, state, timeout_seconds, diag_dir=None):
            # Como el ciclo real: registra la entrada en state.results.
            record_result(state, "00Q000000000001AAA", "AR", "detectado")
            return list(detected)

        with (
            TemporaryDirectory() as tmp,
            self._enabled_state(tmp),
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.create_driver", return_value=object()),
            patch("ui_server.ensure_monitor_window"),
            patch("ui_server.release_driver"),
            patch("ui_server.run_cycle", side_effect=_cycle),
            patch("ui_server.windows_toast") as toast,
            patch("ui_server.broadcast_event"),
        ):
            ui_server.monitor_tick(self._config(tmp))
            self.assertEqual(toast.call_count, 1)
            self.assertIn("nuevo", toast.call_args.args[1])

            ui_server.monitor_tick(self._config(tmp))
            self.assertEqual(toast.call_count, 1)

    def test_tick_cycle_error_waits_next_interval(self):
        import ui_server

        with (
            TemporaryDirectory() as tmp,
            self._enabled_state(tmp),
            patch("ui_server.detect_browser", side_effect=RuntimeError("no browser")),
            patch("ui_server.windows_toast") as toast,
        ):
            events = ui_server.monitor_tick(self._config(tmp))
            self.assertEqual(events[0]["type"], "cycle_error")
            toast.assert_not_called()
            saved = json.loads((Path(tmp) / "monitor_state.json").read_text(encoding="utf-8"))
            self.assertTrue(saved["paused_reason"].startswith("error:"))

    def test_forced_tick_ignores_toggle_and_schedule(self):
        """La revisión manual corre aunque el monitor esté apagado y fuera de franja."""
        import ui_server

        with TemporaryDirectory() as tmp, self._enabled_state(tmp):
            state_path = Path(tmp) / "monitor_state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["enabled"] = False
            state["schedule"] = [{"start": "00:00", "end": "00:01"}]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with (
                patch("ui_server.within_schedule", return_value=False),
                patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
                patch("ui_server.create_driver", return_value=object()),
                patch("ui_server.ensure_monitor_window"),
                patch("ui_server.release_driver"),
                patch("ui_server.run_cycle", return_value=[]) as cycle,
            ):
                ui_server.monitor_tick(self._config(tmp), force=True)
                cycle.assert_called_once()

    def test_forced_tick_still_respects_active_run_and_missing_bandejas(self):
        import ui_server

        runner = unittest.mock.Mock()
        runner.poll.return_value = None
        ui_server.current_process = runner
        try:
            with TemporaryDirectory() as tmp, self._enabled_state(tmp):
                with patch("ui_server.detect_browser") as detect:
                    ui_server.monitor_tick(self._config(tmp), force=True)
                detect.assert_not_called()
                saved = json.loads((Path(tmp) / "monitor_state.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["paused_reason"], "run_activo")
        finally:
            ui_server.current_process = None

    def test_start_manual_check_refuses_overlapping_cycles(self):
        import ui_server

        self.assertTrue(ui_server.cycle_lock.acquire(blocking=False))
        try:
            self.assertFalse(ui_server.start_manual_check({}))
        finally:
            ui_server.cycle_lock.release()

    def test_ensure_monitor_window_creates_and_reuses_dedicated_window(self):
        """La ventana del monitor se crea una vez y se reusa: no toca las del usuario."""
        import ui_server

        driver = unittest.mock.Mock()
        driver.window_handles = ["main", "monitor-win"]
        driver.current_window_handle = "monitor-win"
        ui_server.monitor_window_handle = None
        try:
            self.assertEqual(ui_server.ensure_monitor_window(driver), "monitor-win")
            driver.switch_to.new_window.assert_called_once_with("window")
            # Segundo ciclo: la ventana ya existe, solo hay que activarla.
            driver.switch_to.new_window.reset_mock()
            ui_server.ensure_monitor_window(driver)
            driver.switch_to.new_window.assert_not_called()
            driver.switch_to.window.assert_called_with("monitor-win")
        finally:
            ui_server.monitor_window_handle = None

    def test_ensure_monitor_window_adopts_the_restored_window(self):
        """Tras reiniciar el navegador, la ventana restaurada se adopta en vez de duplicarse."""
        import ui_server

        report = "https://sf.example/lightning/r/Report/00O1/view"
        driver = unittest.mock.Mock()
        driver.window_handles = ["main-tab", "CDwindow-REST1"]
        driver.bot_work_tab_handle = "main-tab"
        ui_server.monitor_window_handle = "stale-handle"
        try:
            with patch(
                "ui_server.debugger_tab_targets",
                return_value=[
                    {"id": "OTHER1", "url": "http://127.0.0.1:8765/"},
                    {"id": "REST1", "url": report},
                ],
            ):
                result = ui_server.ensure_monitor_window(
                    driver,
                    adopt_urls=[report],
                    debugger_address="127.0.0.1:9222",
                )
            self.assertEqual(result, "CDwindow-REST1")
            driver.switch_to.new_window.assert_not_called()
            driver.switch_to.window.assert_any_call("CDwindow-REST1")
        finally:
            ui_server.monitor_window_handle = None

    def test_ensure_monitor_window_adopts_window_left_on_a_lead(self):
        """Tras un Pick Up la ventana del monitor queda en un Lead, no en un reporte."""
        import ui_server

        lead_url = "https://sf.example/lightning/r/Lead/00QbD00000vBrugUAC/view"
        driver = unittest.mock.Mock()
        driver.window_handles = ["work", "monitor-restored"]
        driver.bot_work_tab_handle = "work"
        ui_server.monitor_window_handle = "stale-handle"
        try:
            with patch(
                "ui_server.debugger_tab_targets",
                return_value=[{"id": "monitor-restored", "url": lead_url}],
            ):
                result = ui_server.ensure_monitor_window(
                    driver,
                    adopt_urls=[lead_url, "https://sf.example/lightning/r/Report/00O1/view"],
                    debugger_address="127.0.0.1:9222",
                )
            self.assertEqual(result, "monitor-restored")
            driver.switch_to.new_window.assert_not_called()
        finally:
            ui_server.monitor_window_handle = None

    def test_ensure_monitor_window_creates_new_when_nothing_to_adopt(self):
        """Sin ventana restaurada que adoptar, se crea una nueva."""
        import ui_server

        driver = unittest.mock.Mock()
        driver.window_handles = ["main-tab"]
        driver.bot_work_tab_handle = "main-tab"
        driver.current_window_handle = "new-win"
        ui_server.monitor_window_handle = None
        try:
            with patch("ui_server.debugger_tab_targets", return_value=[]):
                ui_server.ensure_monitor_window(
                    driver,
                    adopt_urls=["https://sf.example/report"],
                    debugger_address="127.0.0.1:9222",
                )
            driver.switch_to.new_window.assert_called_once_with("window")
        finally:
            ui_server.monitor_window_handle = None

    def test_ensure_monitor_window_closes_the_blank_work_tab(self):
        """La pestaña about:blank que abre create_driver no queda huérfana."""
        import ui_server

        driver = unittest.mock.Mock()
        driver.window_handles = ["work-tab", "monitor-win"]
        driver.current_window_handle = "work-tab"
        driver.bot_work_tab_handle = "work-tab"
        ui_server.monitor_window_handle = "monitor-win"
        try:
            ui_server.ensure_monitor_window(driver)
            driver.close.assert_called_once()  # solo cierra la pestaña de trabajo
            driver.switch_to.window.assert_called_with("monitor-win")
        finally:
            ui_server.monitor_window_handle = None

    def test_release_driver_can_keep_the_monitor_window(self):
        """close_tab=False libera la sesión sin cerrar la ventana del monitor."""
        from browser_factory import release_driver

        driver = unittest.mock.Mock()
        driver.attached_to_persistent_browser = True
        release_driver(driver, close_tab=False)
        driver.close.assert_not_called()
        driver.quit.assert_called_once()

    def test_monitor_driver_reuses_a_live_session(self):
        """El próximo ciclo no paga otra NEW_SESSION: la sesión viva se reusa."""
        import ui_server

        driver = unittest.mock.Mock()  # current_url responde: sesión viva
        ui_server.monitor_driver = driver
        result = ui_server._monitor_driver(self._config(""), "edge", Path("msedge.exe"), "127.0.0.1:9222")
        self.assertIs(result, driver)

    def test_monitor_driver_recreates_a_dead_session(self):
        """Una sesión que ya no responde se descarta y se crea una sola vez."""
        import ui_server

        class DeadDriver:
            attached_to_persistent_browser = False

            @property
            def current_url(self):
                raise ConnectionError("muerta")

            def quit(self):
                pass

        ui_server.monitor_driver = DeadDriver()
        fresh = unittest.mock.Mock()
        with (
            patch("ui_server.create_driver", return_value=fresh) as create,
            patch("ui_server.release_driver"),
        ):
            result = ui_server._monitor_driver(self._config(""), "edge", Path("msedge.exe"), "127.0.0.1:9222")
        self.assertIs(result, fresh)
        create.assert_called_once()

    def test_second_tick_reuses_the_monitor_session(self):
        """Dos ciclos seguidos = una sola creación de sesión (antes: dos)."""
        import ui_server

        driver = unittest.mock.Mock()
        driver.current_url = "https://sf.example/lightning/r/Report/00O1/view"
        with (
            TemporaryDirectory() as tmp,
            self._enabled_state(tmp),
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.create_driver", return_value=driver) as create,
            patch("ui_server.ensure_monitor_window"),
            patch("ui_server.run_cycle", return_value=[]),
            patch("ui_server.broadcast_event"),
        ):
            config = self._config(tmp)
            ui_server.monitor_tick(config)
            ui_server.monitor_tick(config)
        create.assert_called_once()

    def test_restart_browser_discards_the_monitor_session(self):
        """Tras matar el navegador la sesión persistente queda inválida."""
        import ui_server

        ui_server.monitor_driver = unittest.mock.Mock()
        config = {"browser": "edge", "debugger_address": "127.0.0.1:9222", "profile_directory": "perfil"}
        with (
            patch("ui_server.find_listening_pid", return_value=None),
            patch("ui_server.subprocess.run"),
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.launch_persistent_browser"),
            patch("ui_server.wait_for_debugger", return_value=False),
        ):
            ui_server.restart_browser(config)
        self.assertIsNone(ui_server.monitor_driver)
        self.assertIsNone(ui_server.monitor_window_handle)

    def test_restart_browser_kills_dedicated_profile_when_no_listener(self):
        """Un Edge del perfil con --remote-debugging-port=0 no escucha el
        puerto esperado: sin buscarlo por user-data-dir el relanzamiento
        chocaría con el lock del perfil."""
        import ui_server

        config = {
            "browser": "edge",
            "debugger_address": "127.0.0.1:9222",
            "profile_directory": "perfil",
            "salesforce_url": "https://sf.example",
        }
        calls = []
        with (
            patch("ui_server.find_listening_pid", return_value=None),
            patch("ui_server.dedicated_profile_pids", return_value=["4242"]),
            patch("ui_server.subprocess.run", side_effect=lambda *a, **k: calls.append(a[0])),
            patch("ui_server.detect_browser", return_value=("edge", Path("msedge.exe"))),
            patch("ui_server.launch_persistent_browser") as launch,
            patch("ui_server.wait_for_debugger", return_value=False),
        ):
            ui_server.restart_browser(config)
        self.assertTrue(any("4242" in call for call in calls))
        launch.assert_called_once()

    def test_dedicated_profile_pids_matches_user_data_dir(self):
        """El listado por proceso reconoce el perfil dedicado con y sin
        comillas, y no confunde perfiles hermanos ni otros ejecutables."""
        import types
        import ui_server

        output = "\n".join(
            [
                '111|"C:\\Edge\\msedge.exe" --user-data-dir="C:\\Perfil\\edge-profile" --remote-debugging-port=0',
                "222|msedge.exe --user-data-dir=C:\\Otro\\perfil",
                "333|msedge.exe --type=renderer",
            ]
        )
        with patch(
            "ui_server.subprocess.run",
            return_value=types.SimpleNamespace(stdout=output),
        ):
            pids = ui_server.dedicated_profile_pids(Path("C:/Perfil/edge-profile"))
        self.assertEqual(pids, ["111"])


if __name__ == "__main__":
    unittest.main()
