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
        with patch("ui_server.restart_browser"):
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status, 202)

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

    def test_restart_browser_opens_the_app_tab_first_then_salesforce(self):
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
        ):
            ui_server.restart_browser(config)
        self.assertEqual(
            launch.call_args.args[3],
            ["http://127.0.0.1:8765/", "https://sf.example"],
        )

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
            patch("ui_server.subprocess.Popen") as popen,
        ):
            (Path(tmp) / "queues").mkdir()
            (Path(tmp) / "queues" / "cola_activa.json").write_text('{"leads": []}', encoding="utf-8")
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
            patch("ui_server.subprocess.Popen") as popen,
        ):
            status, payload = self._post_run()

        self.assertEqual(status, 503)
        self.assertIn("trabado", payload["error"])
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
