import json
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import browser_factory
from browser_factory import (
    _create_driver_with_timeout,
    _same_site,
    create_driver,
    debugger_tab_urls,
    launch_persistent_browser,
    open_missing_tabs,
    open_url_in_browser,
    release_driver,
)


class FakeDriver:
    def __init__(self, attached=False):
        self.attached_to_persistent_browser = attached
        self.quit_called = False
        self.close_called = False

    def quit(self):
        self.quit_called = True

    def close(self):
        self.close_called = True


class BrowserFactoryTests(unittest.TestCase):
    def test_release_driver_quits_a_browser_it_opened(self):
        driver = FakeDriver(attached=False)

        release_driver(driver)

        self.assertTrue(driver.quit_called)

    def test_release_driver_frees_the_session_of_an_attached_browser(self):
        # quit() en un driver adjunto no cierra la ventana (no la creó el
        # driver): libera la sesión y mata al chromedriver huérfano.
        driver = FakeDriver(attached=True)

        release_driver(driver)

        self.assertTrue(driver.quit_called)
        self.assertTrue(driver.close_called)

    def test_debugger_is_listening_rejects_unreachable_address(self):
        self.assertFalse(browser_factory.debugger_is_listening("127.0.0.1:1", 0.2))

    def test_debugger_is_listening_rejects_malformed_address(self):
        self.assertFalse(browser_factory.debugger_is_listening("sin-puerto", 0.2))

    def test_launch_persistent_browser_appends_urls(self):
        with patch("browser_factory.subprocess.Popen") as popen:
            launch_persistent_browser(
                Path("msedge.exe"),
                Path("perfil"),
                "127.0.0.1:9222",
                ["https://salesforce", "http://127.0.0.1:8765/"],
            )
        command = popen.call_args.args[0]
        self.assertIn("--remote-debugging-port=9222", command)
        self.assertEqual(command[-2:], ["https://salesforce", "http://127.0.0.1:8765/"])

    def test_open_url_reuses_the_dedicated_profile(self):
        with patch("browser_factory.subprocess.Popen") as popen:
            open_url_in_browser(Path("msedge.exe"), Path("perfil"), "http://127.0.0.1:8765/")
        command = popen.call_args.args[0]
        self.assertIn("--user-data-dir=perfil", command)
        self.assertEqual(command[-1], "http://127.0.0.1:8765/")

    def test_driver_creation_abandons_a_hung_session(self):
        with (
            self.assertRaisesRegex(RuntimeError, "no respondió"),
            patch("browser_factory._kill_orphaned_driver_processes") as kill,
        ):
            _create_driver_with_timeout(lambda options: time.sleep(5), object(), 0.05)
        kill.assert_called_once()

    def test_driver_creation_propagates_constructor_errors(self):
        def broken(options):
            raise ValueError("falló")

        with self.assertRaisesRegex(ValueError, "falló"):
            _create_driver_with_timeout(broken, object(), 5)

    def test_attached_driver_marks_persistent_browser(self):
        driver = SimpleNamespace(switch_to=SimpleNamespace(new_window=lambda *_: None))
        with (
            patch("browser_factory.debugger_is_listening", return_value=True),
            patch("selenium.webdriver.Edge", return_value=driver),
        ):
            result = create_driver("edge", Path("msedge.exe"), Path("perfil"), "127.0.0.1:9222")
        self.assertTrue(result.attached_to_persistent_browser)

    def test_attached_driver_failure_raises_clear_error(self):
        from selenium.common.exceptions import WebDriverException

        with (
            patch("browser_factory.debugger_is_listening", return_value=True),
            patch("selenium.webdriver.Edge", side_effect=WebDriverException("timeout")),
        ):
            with self.assertRaisesRegex(RuntimeError, "navegador persistente"):
                create_driver("edge", Path("msedge.exe"), Path("perfil"), "127.0.0.1:9222")

    def test_tab_urls_returns_only_page_targets(self):
        payload = json.dumps([
            {"type": "page", "url": "http://127.0.0.1:8765/"},
            {"type": "page", "url": "https://sf.example/lightning/r/Lead/00Q1/view"},
            {"type": "service_worker", "url": "chrome://serviceworker"},
        ]).encode()
        response = unittest.mock.MagicMock()
        response.read.return_value = payload
        response.__enter__.return_value = response
        with patch("browser_factory.urllib.request.urlopen", return_value=response):
            urls = debugger_tab_urls("127.0.0.1:9222")
        self.assertEqual(
            urls,
            ["http://127.0.0.1:8765/", "https://sf.example/lightning/r/Lead/00Q1/view"],
        )

    def test_same_site_matches_by_host_not_by_page(self):
        self.assertTrue(
            _same_site("https://sf.example/lightning/r/Lead/00Q1/view", "https://sf.example")
        )
        self.assertTrue(_same_site("http://127.0.0.1:8765/index.html", "http://127.0.0.1:8765/"))
        self.assertFalse(_same_site("https://otro.example", "https://sf.example"))
        self.assertFalse(_same_site("about:blank", "http://127.0.0.1:8765/"))

    def test_open_missing_tabs_skips_tabs_already_open(self):
        opened = []
        existing = iter([
            ["http://127.0.0.1:8765/", "https://sf.example/lightning/r/Lead/00Q1/view"],
        ])
        with (
            patch("browser_factory.debugger_tab_urls", side_effect=lambda *a, **k: next(existing, [])),
            patch("browser_factory.open_url_in_browser", side_effect=lambda *a: opened.append(a[2])),
            patch("browser_factory.time.sleep"),
        ):
            result = open_missing_tabs(
                Path("msedge.exe"),
                Path("perfil"),
                "127.0.0.1:9222",
                ["http://127.0.0.1:8765/", "https://sf.example"],
            )
        self.assertEqual(result, [])

    def test_open_missing_tabs_opens_only_the_one_that_is_missing(self):
        opened = []
        with (
            patch(
                "browser_factory.debugger_tab_urls",
                return_value=["https://sf.example/lightning/o/Lead/list"],
            ),
            patch("browser_factory.open_url_in_browser", side_effect=lambda *a: opened.append(a[2])),
            patch("browser_factory.time.sleep"),
        ):
            result = open_missing_tabs(
                Path("msedge.exe"),
                Path("perfil"),
                "127.0.0.1:9222",
                ["http://127.0.0.1:8765/", "https://sf.example"],
            )
        self.assertEqual(result, ["http://127.0.0.1:8765/"])
        self.assertEqual(opened, ["http://127.0.0.1:8765/"])


if __name__ == "__main__":
    unittest.main()
