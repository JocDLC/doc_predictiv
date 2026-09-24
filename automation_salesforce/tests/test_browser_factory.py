import unittest

import browser_factory
from browser_factory import release_driver


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


if __name__ == "__main__":
    unittest.main()
