import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ui_server import SESSION_FILE, write_session_file


class UiServerTests(unittest.TestCase):
    def test_session_file_exposes_port_and_token_for_the_ui(self):
        with TemporaryDirectory() as temporary_directory:
            path = write_session_file(Path(temporary_directory), 8765, "token-de-prueba")
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(path.name, SESSION_FILE)
        self.assertEqual(payload, {"port": 8765, "token": "token-de-prueba"})


if __name__ == "__main__":
    unittest.main()
