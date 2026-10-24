import base64
import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ui_server import make_handler

QUEUE = {
    "operation": "distribuir_leads",
    "source_file": "bd.xlsx",
    "leads": [{"lead_id": "00Q000000000001AAA", "persona": "Ana Perez"}],
}


def make_xlsx() -> bytes:
    import openpyxl

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Leads"
    worksheet.append(["Lead ID", "Otra información"])
    worksheet.append(["00Q000000000001AAA", "Ana Perez"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class UiDistribucionTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler("token-x"))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def _call(self, method, path, payload=None, token="token-x"):
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body, method=method)
        if token:
            request.add_header("X-Bot-Token", token)
        if body:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def test_parse_returns_sheets_without_persisting(self):
        payload = {"filename": "bd.xlsx", "content_b64": base64.b64encode(make_xlsx()).decode()}
        status, body = self._call("POST", "/api/distribucion/parse", payload)
        self.assertEqual(status, 200)
        self.assertEqual(body["sheets"][0]["name"], "Leads")
        self.assertEqual(body["sheets"][0]["rows"][0]["Otra información"], "Ana Perez")

    def test_parse_requires_token_and_valid_file(self):
        status, _ = self._call("POST", "/api/distribucion/parse", {"filename": "a.xlsx", "content_b64": "eA=="}, token=None)
        self.assertEqual(status, 403)
        status, body = self._call(
            "POST", "/api/distribucion/parse", {"filename": "a.xlsx", "content_b64": base64.b64encode(b"basura").decode()}
        )
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_put_queue_persists_only_pairs_and_warns_monitor(self):
        with TemporaryDirectory() as tmp, patch(
            "ui_server.API_FILES", {"/api/distribucion-queue": Path(tmp) / "cola.json"}
        ):
            status, body = self._call("PUT", "/api/distribucion-queue", QUEUE)
            self.assertEqual(status, 200)
            self.assertIn("monitor_activo", body)
            written = json.loads((Path(tmp) / "cola.json").read_text(encoding="utf-8"))
            self.assertEqual(written["leads"], QUEUE["leads"])

    def test_put_queue_rejects_invalid(self):
        with TemporaryDirectory() as tmp, patch(
            "ui_server.API_FILES", {"/api/distribucion-queue": Path(tmp) / "cola.json"}
        ):
            status, _ = self._call("PUT", "/api/distribucion-queue", {"operation": "otra", "leads": [1]})
            self.assertEqual(status, 400)
            self.assertFalse((Path(tmp) / "cola.json").exists())

    def test_results_reads_missing_file_as_empty(self):
        with TemporaryDirectory() as tmp, patch(
            "ui_server.API_FILES", {"/api/distribucion-results": Path(tmp) / "r.json"}
        ):
            request = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/distribucion-results")
            request.add_header("X-Bot-Token", "token-x")
            with urllib.request.urlopen(request) as response:
                self.assertEqual(json.loads(response.read()), [])


if __name__ == "__main__":
    unittest.main()
