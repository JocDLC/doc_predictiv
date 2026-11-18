"""Matriz adversarial en navegador real sobre el fixture local.

Levanta un http.server con ``fixtures/laboratorio_whatsapp.html`` y un Edge
descartable (perfil temporal, puerto CDP propio); ejerce el contrato de
confirmación endurecido con AMBOS motores. Se omite si Edge, el driver o la
CLI de agent-browser no están disponibles — nunca toca Salesforce ni envía
mensajes reales.
"""

from __future__ import annotations

import http.server
import shutil
import socketserver
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

import agent_browser as ab
import laboratory_browser as lab_browser

FIXTURE = Path(__file__).parent / "fixtures" / "laboratorio_whatsapp.html"
FIXTURE_LEAD_ID = "00QFIXTURE00001AA"


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class _FixtureHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 — emula la URL de la ficha Salesforce
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(FIXTURE.read_bytes())

    def log_message(self, *_args):
        pass


def _edge_binary() -> str | None:
    for name in ("msedge", "microsoft-edge", "chrome", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


class LabFixtureLiveTests(unittest.TestCase):
    """Casos A04–A08 del spec adversarial contra el fixture, ambos motores."""

    @classmethod
    def setUpClass(cls):
        cls.edge = _edge_binary()
        if not cls.edge:
            raise unittest.SkipTest("Edge/Chrome no disponible para el fixture")
        try:
            cls.agent_command = ab.resolve_command("")
        except ab.AgentBrowserUnavailable:
            cls.agent_command = None
        cls.http_port = _free_port()
        cls.cdp_port = _free_port()
        cls.server = socketserver.TCPServer(("127.0.0.1", cls.http_port), _FixtureHandler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.edge_process = cls._launch_edge_class()

    @classmethod
    def tearDownClass(cls):
        # El launcher no es padre del navegador real: se mata el proceso que
        # escucha el puerto CDP (y su árbol) en vez del handle de Popen.
        for line in subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout.splitlines():
            if f"127.0.0.1:{cls.cdp_port}" in line and "LISTENING" in line:
                pid = line.split()[-1]
                if pid.isdigit():
                    subprocess.run(
                        ["taskkill", "/PID", pid, "/F", "/T"],
                        capture_output=True,
                    )
        if cls.edge_process is not None:
            try:
                cls.edge_process.kill()
            except Exception:  # noqa: BLE001
                pass
        cls.server.shutdown()
        cls.server.server_close()

    @classmethod
    def _launch_edge_class(cls):
        profile = tempfile.mkdtemp(prefix="lab-fixture-edge-")
        process = subprocess.Popen(
            [
                cls.edge,
                f"--remote-debugging-port={cls.cdp_port}",
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--no-default-browser-check",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                import urllib.request

                urllib.request.urlopen(f"http://127.0.0.1:{cls.cdp_port}/json/version", timeout=1)
                return process
            except Exception:  # noqa: BLE001
                # msedge.exe es launcher: el padre puede salir y el navegador
                # sigue; solo importa que el endpoint CDP responda.
                time.sleep(0.4)
        process.kill()
        cls.server.shutdown()
        raise unittest.SkipTest("Edge descartable no levantó el endpoint CDP")

    def _fixture_url(self, scenario: str, hist: str = "", delay: int = 100) -> str:
        path = f"http://127.0.0.1:{self.http_port}/r/Lead/{FIXTURE_LEAD_ID}/view"
        parts = [f"toast={scenario}", f"delay={delay}"]
        if hist:
            parts.append(f"hist={hist}")
        return path + "#" + "&".join(parts)

    # --- motores -----------------------------------------------------------

    def _agent_lab_browser(self):
        if not self.agent_command:
            self.skipTest("CLI agent-browser no disponible")
        transport = ab.AgentBrowserTransport(
            self.agent_command, f"127.0.0.1:{self.cdp_port}", session="lab-fixture", tab_label="labfix"
        )
        config = {
            "salesforce_url": f"http://127.0.0.1:{self.http_port}",
            "record_object_api_name": "Lead",
            "timeouts": {"page_load_seconds": 10},
        }
        browser = ab.AgentLabBrowser(transport, config)
        browser.connect()
        return browser

    def _selenium_lab_browser(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.edge.options import Options
        except ImportError:
            self.skipTest("selenium/edgedriver no disponible")
        options = Options()
        options.debugger_address = f"127.0.0.1:{self.cdp_port}"
        try:
            driver = webdriver.Edge(options=options)
        except Exception as error:  # noqa: BLE001 — driver ausente/desalineado
            self.skipTest(f"EdgeDriver no disponible: {type(error).__name__}")
        config = {"timeouts": {"page_load_seconds": 10}}
        return lab_browser.SeleniumLabBrowser(driver, config)

    # --- casos -------------------------------------------------------------

    def _confirmation_case(self, engine: str, scenario: str, expected_outcome: str):
        browser = self._agent_lab_browser() if engine == "agent_browser" else self._selenium_lab_browser()
        try:
            url = self._fixture_url(scenario)
            if engine == "agent_browser":
                browser.transport.open_url(url)
                time.sleep(1.0)
            else:
                browser.driver.get(url)
                time.sleep(1.0)
            armed = browser.arm_whatsapp_observation()
            self.assertTrue(armed.get("armed"))
            click = browser.guarded_click_whatsapp(FIXTURE_LEAD_ID)
            self.assertEqual(click, "clicked")
            evidence = browser.collect_whatsapp_evidence(4.0)
            browser.dispose_whatsapp_observation()
            self.assertEqual(
                evidence.get("outcome"),
                expected_outcome,
                f"{engine}/{scenario}: {evidence}",
            )
        finally:
            try:
                browser.dispose_whatsapp_observation()
            except Exception:  # noqa: BLE001
                pass
            try:
                browser.release()
            except Exception:  # noqa: BLE001
                pass

    def test_agent_browser_positive_confirms(self):
        self._confirmation_case("agent_browser", "positive", "confirmado")

    def test_agent_browser_negative_is_not_confirmed(self):
        self._confirmation_case("agent_browser", "negative", "no_confirmado")

    def test_agent_browser_unrelated_is_not_confirmed(self):
        self._confirmation_case("agent_browser", "unrelated", "no_confirmado")

    def test_agent_browser_stale_is_not_confirmed(self):
        self._confirmation_case("agent_browser", "stale", "no_confirmado")

    def test_agent_browser_silent_is_not_confirmed(self):
        self._confirmation_case("agent_browser", "none", "no_confirmado")

    def test_selenium_positive_confirms(self):
        self._confirmation_case("selenium", "positive", "confirmado")

    def test_selenium_negative_is_not_confirmed(self):
        self._confirmation_case("selenium", "negative", "no_confirmado")

    def test_selenium_stale_is_not_confirmed(self):
        self._confirmation_case("selenium", "stale", "no_confirmado")

    def test_literal_history_and_guarded_click(self):
        # A04: una línea "Modificar Otra información" legítima se conserva.
        if not self.agent_command:
            self.skipTest("CLI agent-browser no disponible")
        browser = self._agent_lab_browser()
        try:
            browser.transport.open_url(self._fixture_url("none", hist="Modificar+Otra+información||1+INT+previo"))
            time.sleep(1.0)
            text = browser.field_text(("Otra información",))
            self.assertIn("Modificar Otra información", text or "")
            self.assertIn("1 INT previo", text or "")
            # id esperado distinto del fixture: no debe clicar.
            self.assertEqual(browser.guarded_click_whatsapp("00Q000000000099AAA"), "id_mismatch")
        finally:
            browser.dispose_whatsapp_observation()
            try:
                browser.release()
            except Exception:  # noqa: BLE001
                pass

    def test_selenium_field_read_ignores_assistive(self):
        # El lápiz emite "Modificar Otra información": no debe colarse como
        # valor, y una línea legítima con ese texto se conserva.
        browser = self._selenium_lab_browser()
        try:
            browser.driver.get(self._fixture_url("none", hist="Modificar+Otra+información||1+INT+previo"))
            time.sleep(1.0)
            # Labels normalizados como OTHER_INFORMATION_LABELS.
            text = browser.field_text(("otra información", "otra informacion")) or ""
            lines = [line for line in text.splitlines() if line.strip()]
            # Una sola aparición: la legítima del valor, no la del lápiz.
            self.assertEqual(
                sum(1 for line in lines if "modificar" in line.lower()),
                1,
                f"valor leído: {text!r}",
            )
            self.assertIn("1 INT previo", text)
        finally:
            try:
                browser.release()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    unittest.main()
