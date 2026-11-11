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
        status, _ = self._call(
            "POST", "/api/distribucion/parse", {"filename": "a.xlsx", "content_b64": "eA=="}, token=None
        )
        self.assertEqual(status, 403)
        status, body = self._call(
            "POST",
            "/api/distribucion/parse",
            {"filename": "a.xlsx", "content_b64": base64.b64encode(b"basura").decode()},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_put_queue_persists_only_pairs_and_warns_monitor(self):
        with (
            TemporaryDirectory() as tmp,
            patch("ui_server.API_FILES", {"/api/distribucion-queue": Path(tmp) / "cola.json"}),
        ):
            status, body = self._call("PUT", "/api/distribucion-queue", QUEUE)
            self.assertEqual(status, 200)
            self.assertIn("monitor_activo", body)
            written = json.loads((Path(tmp) / "cola.json").read_text(encoding="utf-8"))
            self.assertEqual(written["leads"], QUEUE["leads"])

    def test_put_queue_rejects_invalid(self):
        with (
            TemporaryDirectory() as tmp,
            patch("ui_server.API_FILES", {"/api/distribucion-queue": Path(tmp) / "cola.json"}),
        ):
            status, _ = self._call("PUT", "/api/distribucion-queue", {"operation": "otra", "leads": [1]})
            self.assertEqual(status, 400)
            self.assertFalse((Path(tmp) / "cola.json").exists())

    def test_put_queue_accepts_and_persists_modo_prueba(self):
        queue = {**QUEUE, "modo": "prueba"}
        with (
            TemporaryDirectory() as tmp,
            patch("ui_server.API_FILES", {"/api/distribucion-queue": Path(tmp) / "cola.json"}),
        ):
            status, _ = self._call("PUT", "/api/distribucion-queue", queue)
            self.assertEqual(status, 200)
            written = json.loads((Path(tmp) / "cola.json").read_text(encoding="utf-8"))
            self.assertEqual(written["modo"], "prueba")

    def test_put_queue_rejects_modo_desconocido(self):
        with (
            TemporaryDirectory() as tmp,
            patch("ui_server.API_FILES", {"/api/distribucion-queue": Path(tmp) / "cola.json"}),
        ):
            status, _ = self._call("PUT", "/api/distribucion-queue", {**QUEUE, "modo": "demo"})
            self.assertEqual(status, 400)
            self.assertFalse((Path(tmp) / "cola.json").exists())

    def test_results_reads_missing_file_as_empty(self):
        with (
            TemporaryDirectory() as tmp,
            patch("ui_server.API_FILES", {"/api/distribucion-results": Path(tmp) / "r.json"}),
        ):
            request = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/distribucion-results")
            request.add_header("X-Bot-Token", "token-x")
            with urllib.request.urlopen(request) as response:
                self.assertEqual(json.loads(response.read()), [])


class UiDistribucionEquipoTests(unittest.TestCase):
    """GET/PUT del equipo del día del reparto equitativo."""

    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler("token-x"))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path_patch = patch("ui_server.equipo_reparto_path", return_value=Path(self.tmp.name) / "equipo.json")
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)

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

    def test_get_vacio_y_roundtrip(self):
        status, body = self._call("GET", "/api/distribucion-equipo")
        self.assertEqual(status, 200)
        self.assertEqual(body, [])
        equipo = [{"nombre": "Ana", "trabaja": True}, {"nombre": "Beto", "trabaja": False}]
        status, body = self._call("PUT", "/api/distribucion-equipo", {"equipo": equipo})
        self.assertEqual(status, 200)
        self.assertEqual(body, equipo)
        status, body = self._call("GET", "/api/distribucion-equipo")
        self.assertEqual(status, 200)
        self.assertEqual(body, equipo)

    def test_put_valida_y_dedup(self):
        status, _ = self._call("PUT", "/api/distribucion-equipo", {"equipo": [{"nombre": "", "trabaja": True}]})
        self.assertEqual(status, 400)
        status, _ = self._call("PUT", "/api/distribucion-equipo", {"equipo": [{"nombre": "Ana"}]})
        self.assertEqual(status, 400)
        status, body = self._call(
            "PUT",
            "/api/distribucion-equipo",
            {"equipo": [{"nombre": "José", "trabaja": True}, {"nombre": "jose", "trabaja": False}]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, [{"nombre": "José", "trabaja": True}])
        self.assertTrue((Path(self.tmp.name) / "equipo.json").exists())

    def test_equipo_requires_token(self):
        status, _ = self._call("GET", "/api/distribucion-equipo", token=None)
        self.assertEqual(status, 403)
        status, _ = self._call("PUT", "/api/distribucion-equipo", {"equipo": []}, token=None)
        self.assertEqual(status, 403)


class UiDistribucionRepartoTests(unittest.TestCase):
    """POST /api/distribucion/reparto: el algoritmo corre server-side."""

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

    def test_reparto_devuelve_asignaciones_resumen_y_whatsapp(self):
        filas = [
            {"lead_id": "00Q000000000001AAA", "auxiliar": "Ana", "whatsapp": True},
            {"lead_id": "00Q000000000002AAA", "auxiliar": "Carlos Ausente", "whatsapp": False},
        ]
        status, body = self._call("POST", "/api/distribucion/reparto", {"filas": filas, "trabajan": ["Ana", "Beto"]})
        self.assertEqual(status, 200)
        asignaciones = body["asignaciones"]
        self.assertEqual((asignaciones[0]["destino"], asignaciones[0]["accion"]), ("Ana", "se_queda"))
        self.assertEqual((asignaciones[1]["destino"], asignaciones[1]["accion"]), ("Beto", "se_mueve"))
        self.assertEqual(body["resumen"]["Ana"], {"cupos": 1, "se_quedan": 1, "entran": 0})
        self.assertEqual(body["resumen"]["Beto"], {"cupos": 1, "se_quedan": 0, "entran": 1})
        self.assertEqual(body["whatsapp_list"], [{"lead_id": "00Q000000000001AAA", "persona": "Ana"}])

    def test_reparto_valida_entrada(self):
        status, _ = self._call(
            "POST",
            "/api/distribucion/reparto",
            {"filas": [{"lead_id": "00Q000000000001AAA"}], "trabajan": []},
        )
        self.assertEqual(status, 400)
        status, _ = self._call("POST", "/api/distribucion/reparto", {"filas": [], "trabajan": ["Ana"]})
        self.assertEqual(status, 400)
        status, _ = self._call(
            "POST",
            "/api/distribucion/reparto",
            {"filas": [{"lead_id": "   "}], "trabajan": ["Ana"]},
        )
        self.assertEqual(status, 400)
        status, _ = self._call("POST", "/api/distribucion/reparto", ["no", "objeto"])
        self.assertEqual(status, 400)

    def test_reparto_requires_token(self):
        status, _ = self._call(
            "POST",
            "/api/distribucion/reparto",
            {"filas": [{"lead_id": "00Q000000000001AAA"}], "trabajan": ["Ana"]},
            token=None,
        )
        self.assertEqual(status, 403)


class UiDistribucionExportarTests(unittest.TestCase):
    """POST /api/distribucion/exportar: el .xlsx se genera en memoria."""

    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler("token-x"))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def _export(self, payload, token="token-x"):
        body = json.dumps(payload).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/distribucion/exportar", data=body, method="POST"
        )
        if token:
            request.add_header("X-Bot-Token", token)
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read()

    def test_export_distribucion_genera_xlsx_valido(self):
        filas = [
            {
                "lead_id": "00Q000000000001AAA",
                "nombre": "Juan Perez",
                "auxiliar": "Carlos Ausente",
                "destino": "Ana",
                "accion": "se_mueve",
            },
            {
                "lead_id": "00Q000000000002AAA",
                "nombre": "Maria Gomez",
                "auxiliar": "Ana",
                "destino": "Ana",
                "accion": "se_queda",
            },
        ]
        status, headers, content = self._export({"tipo": "distribucion", "filas": filas})
        self.assertEqual(status, 200)
        self.assertIn("spreadsheetml.sheet", headers.get("Content-Type", ""))
        self.assertIn("distribucion_", headers.get("Content-Disposition", ""))
        self.assertIn(".xlsx", headers.get("Content-Disposition", ""))
        import openpyxl

        workbook = openpyxl.load_workbook(io.BytesIO(content))
        rows = list(workbook.active.iter_rows(values_only=True))
        self.assertEqual(rows[0], ("Lead ID", "Lead", "Auxiliar actual", "Nueva persona", "Acción"))
        self.assertEqual(rows[1], ("00Q000000000001AAA", "Juan Perez", "Carlos Ausente", "Ana", "se mueve"))
        self.assertEqual(rows[2], ("00Q000000000002AAA", "Maria Gomez", "Ana", "Ana", "se queda"))

    def test_export_whatsapp_solo_dos_columnas(self):
        filas = [{"lead_id": "00Q000000000001AAA", "destino": "Beto", "whatsapp": True}]
        status, headers, content = self._export({"tipo": "whatsapp", "filas": filas})
        self.assertEqual(status, 200)
        self.assertIn("reasignacion_whatsapp_", headers.get("Content-Disposition", ""))
        import openpyxl

        workbook = openpyxl.load_workbook(io.BytesIO(content))
        rows = list(workbook.active.iter_rows(values_only=True))
        self.assertEqual(rows[0], ("Lead ID", "Nueva persona"))
        self.assertEqual(rows[1], ("00Q000000000001AAA", "Beto"))

    def test_export_valida_tipo_y_filas(self):
        status, _, body = self._export({"tipo": "otro", "filas": [{"lead_id": "00Q000000000001AAA"}]})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))
        status, _, _ = self._export({"tipo": "distribucion", "filas": []})
        self.assertEqual(status, 400)
        status, _, _ = self._export({"tipo": "distribucion", "filas": [{"lead_id": "  "}]})
        self.assertEqual(status, 400)

    def test_export_requires_token(self):
        status, _, _ = self._export({"tipo": "distribucion", "filas": [{"lead_id": "00Q000000000001AAA"}]}, token=None)
        self.assertEqual(status, 403)


class UiDistribucionRunTests(unittest.TestCase):
    """POST /run-distribucion: cada corrida arranca con resultados limpios."""

    def _post(self, path, payload, token="token-x"):
        body = json.dumps(payload).encode() if payload is not None else b""
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body, method="POST")
        request.add_header("X-Bot-Token", token)
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def test_run_reinicia_el_archivo_de_resultados(self):
        """Simular y después ejecutar no debe mezclar corridas: al lanzar
        la corrida real el resultado viejo se descarta — la tabla muestra
        solo lo de esta corrida."""
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
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler("token-x"))
            self.port = self.server.server_address[1]
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            try:
                queues = Path(tmp) / "queues"
                queues.mkdir()
                (queues / "cola_distribucion_activa.json").write_text(
                    json.dumps(
                        {
                            "operation": "distribuir_leads",
                            "modo": "real",
                            "leads": [{"lead_id": "00Q000000000001AAA", "persona": "Ana"}],
                        }
                    ),
                    encoding="utf-8",
                )
                stale = queues / "cola_distribucion_activa.resultado.json"
                stale.write_text(
                    json.dumps([{"lead_id": "00Q000000000001AAA", "status": "prueba_ok:reasignar"}]),
                    encoding="utf-8",
                )
                popen.return_value.poll.return_value = None
                status, _ = self._post("/run-distribucion", {})
                self.assertEqual(status, 202)
                self.assertFalse(stale.exists())
            finally:
                self.server.shutdown()
                self.server.server_close()
        ui_server.current_process = None


if __name__ == "__main__":
    unittest.main()
