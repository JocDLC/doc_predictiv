import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from selenium.common.exceptions import TimeoutException

import salesforce_session


class SalesforceSessionTests(unittest.TestCase):
    def test_load_config_reads_utf8_json_from_module_root(self):
        config = {"salesforce_url": "https://synthetic.example", "label": "sesión sintética"}
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

            with patch.object(salesforce_session, "ROOT", Path(directory)):
                self.assertEqual(salesforce_session.load_config(), config)

    def test_local_path_expands_environment_and_user_components(self):
        with (
            patch("salesforce_session.os.path.expandvars", return_value="~/synthetic-profile") as expandvars,
            patch("salesforce_session.Path.expanduser", return_value=Path("synthetic-profile")) as expanduser,
        ):
            result = salesforce_session.local_path("$SYNTHETIC_ROOT/profile")

        expandvars.assert_called_once_with("$SYNTHETIC_ROOT/profile")
        expanduser.assert_called_once_with()
        self.assertEqual(result, Path("synthetic-profile"))

    def test_authentication_condition_accepts_only_authenticated_lightning_url(self):
        wait = Mock()
        with patch("salesforce_session.WebDriverWait", return_value=wait) as wait_class:
            driver = Mock()
            salesforce_session.wait_for_authentication(driver, 17)

        wait_class.assert_called_once_with(driver, 17)
        condition = wait.until.call_args.args[0]
        self.assertTrue(condition(SimpleNamespace(current_url="https://synthetic.lightning.force.com/lightning/page")))
        self.assertFalse(condition(SimpleNamespace(current_url="https://synthetic.lightning.force.com/login")))
        self.assertFalse(condition(SimpleNamespace(current_url="https://login.salesforce.com")))

    def test_lightning_ready_waits_for_complete_document(self):
        wait = Mock()
        with patch("salesforce_session.WebDriverWait", return_value=wait) as wait_class:
            driver = Mock()
            salesforce_session.wait_for_lightning_ready(driver, 23)

        wait_class.assert_called_once_with(driver, 23)
        condition = wait.until.call_args.args[0]
        driver.execute_script.side_effect = ["loading", "complete"]
        self.assertFalse(condition(driver))
        self.assertTrue(condition(driver))
        driver.execute_script.assert_called_with("return document.readyState")

    def test_is_authenticated_uses_short_probe_timeout(self):
        driver = Mock()
        with patch("salesforce_session.wait_for_authentication") as wait_for_authentication:
            self.assertTrue(salesforce_session.is_authenticated(driver))

        wait_for_authentication.assert_called_once_with(driver, 5)

    def test_is_authenticated_returns_false_on_timeout(self):
        with patch(
            "salesforce_session.wait_for_authentication",
            side_effect=TimeoutException("synthetic timeout"),
        ):
            self.assertFalse(salesforce_session.is_authenticated(Mock(), timeout_seconds=9))

    def test_authenticated_session_does_not_prompt_for_login_or_2fa(self):
        driver = Mock()
        config = {"salesforce_url": "https://synthetic.example"}
        with (
            patch("salesforce_session.is_authenticated", return_value=True),
            patch("builtins.input") as manual_prompt,
            patch("salesforce_session.wait_for_authentication") as authentication_wait,
            patch("builtins.print") as print_message,
        ):
            salesforce_session.prompt_for_manual_authentication(driver, config)

        driver.get.assert_called_once_with(config["salesforce_url"])
        manual_prompt.assert_not_called()
        authentication_wait.assert_not_called()
        print_message.assert_called_once()

    def test_unauthenticated_session_requires_manual_login_and_2fa(self):
        driver = Mock()
        config = {
            "salesforce_url": "https://synthetic.example",
            "timeouts": {"authentication_seconds": 41},
        }
        with (
            patch("salesforce_session.is_authenticated", return_value=False),
            patch("builtins.input", return_value="") as manual_prompt,
            patch("salesforce_session.wait_for_authentication") as authentication_wait,
        ):
            salesforce_session.prompt_for_manual_authentication(driver, config)

        driver.get.assert_called_once_with(config["salesforce_url"])
        prompt_text = manual_prompt.call_args.args[0]
        self.assertIn("2FA manualmente", prompt_text)
        authentication_wait.assert_called_once_with(driver, 41)

    def test_manual_authentication_timeout_is_not_hidden(self):
        driver = Mock()
        config = {
            "salesforce_url": "https://synthetic.example",
            "timeouts": {"authentication_seconds": 3},
        }
        with (
            patch("salesforce_session.is_authenticated", return_value=False),
            patch("builtins.input", return_value=""),
            patch(
                "salesforce_session.wait_for_authentication",
                side_effect=TimeoutException("synthetic timeout"),
            ),
        ):
            with self.assertRaises(TimeoutException):
                salesforce_session.prompt_for_manual_authentication(driver, config)


if __name__ == "__main__":
    unittest.main()
