import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import browser_factory
from browser_factory import (
    ATTACH_SESSION_TIMEOUT_SECONDS,
    COMMAND_TIMEOUT_SECONDS,
    create_driver,
    launch_persistent_browser,
    open_url_in_browser,
    release_driver,
)


class FakeDriver:
    def __init__(self, attached=False):
        self.attached_to_persistent_browser = attached
        self.quit_called = False

    def quit(self):
        self.quit_called = True


class BrowserFactoryTests(unittest.TestCase):
    def test_release_driver_quits_a_browser_it_opened(self):
        driver = FakeDriver(attached=False)

        release_driver(driver)

        self.assertTrue(driver.quit_called)

    def test_release_driver_keeps_the_persistent_browser_open(self):
        driver = FakeDriver(attached=True)

        release_driver(driver)

        self.assertFalse(driver.quit_called)

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

    def test_attached_driver_uses_short_session_timeout_then_restores(self):
        client_config = SimpleNamespace(timeout=None)
        driver = SimpleNamespace(
            command_executor=SimpleNamespace(client_config=client_config),
            switch_to=SimpleNamespace(new_window=lambda *_: None),
        )
        with (
            patch("browser_factory.debugger_is_listening", return_value=True),
            patch("selenium.webdriver.Edge", return_value=driver) as edge,
        ):
            result = create_driver("edge", Path("msedge.exe"), Path("perfil"), "127.0.0.1:9222")
        passed_config = edge.call_args.kwargs["client_config"]
        self.assertEqual(passed_config.timeout, ATTACH_SESSION_TIMEOUT_SECONDS)
        self.assertEqual(client_config.timeout, COMMAND_TIMEOUT_SECONDS)
        self.assertTrue(result.attached_to_persistent_browser)

    def test_attached_driver_failure_raises_clear_error(self):
        from selenium.common.exceptions import WebDriverException

        with (
            patch("browser_factory.debugger_is_listening", return_value=True),
            patch("selenium.webdriver.Edge", side_effect=WebDriverException("timeout")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Reiniciar navegador|reinici"):
                create_driver("edge", Path("msedge.exe"), Path("perfil"), "127.0.0.1:9222")


if __name__ == "__main__":
    unittest.main()
