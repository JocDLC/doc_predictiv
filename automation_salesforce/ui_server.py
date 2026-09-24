"""Servidor local mínimo para que la UI dispare el bot sin usar la terminal.

Escucha solo en ``127.0.0.1`` y exige un token aleatorio por sesión que la UI
lee de ``ui_output/bot_session.json`` con el permiso de carpeta que ya tiene.
Solo permite lanzar el runner de la cola activa: no ejecuta comandos
arbitrarios. Todo queda en la máquina local.
"""

from __future__ import annotations

import json
import secrets
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from salesforce_session import ROOT, load_config

SERVER_PORT = 8765
ACTIVE_QUEUE = "cola_activa.json"
SESSION_FILE = "bot_session.json"

current_process: subprocess.Popen | None = None


def write_session_file(ui_output_directory: Path, port: int, token: str) -> Path:
    """Publica puerto y token donde la UI puede leerlos (carpeta ya vinculada)."""
    ui_output_directory.mkdir(parents=True, exist_ok=True)
    session_path = ui_output_directory / SESSION_FILE
    session_path.write_text(
        json.dumps({"port": port, "token": token}, indent=2),
        encoding="utf-8",
    )
    return session_path


def make_handler(token: str):
    class BotRequestHandler(BaseHTTPRequestHandler):
        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            # Sin el token de la sesión ninguna otra página local puede disparar el bot.
            return self.headers.get("X-Bot-Token") == token

        def do_OPTIONS(self) -> None:  # preflight CORS para el header del token
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "X-Bot-Token")
            self.send_header("Access-Control-Allow-Methods", "POST, GET")
            self.end_headers()

        def do_GET(self) -> None:
            if self.path != "/status":
                self._send(404, {"error": "ruta desconocida"})
                return
            running = current_process is not None and current_process.poll() is None
            self._send(200, {
                "running": running,
                "exit_code": None if running or current_process is None else current_process.returncode,
            })

        def do_POST(self) -> None:
            global current_process
            if not self._authorized():
                self._send(403, {"error": "token inválido o ausente"})
                return
            if self.path != "/run":
                self._send(404, {"error": "ruta desconocida"})
                return
            if current_process is not None and current_process.poll() is None:
                self._send(409, {"status": "ya esta corriendo"})
                return
            queue_path = ROOT / "queues" / ACTIVE_QUEUE
            current_process = subprocess.Popen(
                [sys.executable, str(ROOT / "run_document_queue.py"), "--auto", str(queue_path)],
                cwd=str(ROOT),
            )
            self._send(202, {"status": "iniciado", "queue": ACTIVE_QUEUE})

        def log_message(self, *_args) -> None:
            pass

    return BotRequestHandler


def main() -> int:
    global current_process
    config = load_config()
    ui_output_directory = ROOT / config.get("ui_output_directory", "ui_output")
    token = secrets.token_hex(16)
    session_path = write_session_file(ui_output_directory, SERVER_PORT, token)
    server = ThreadingHTTPServer(("127.0.0.1", SERVER_PORT), make_handler(token))
    print(f"Servidor del bot en http://127.0.0.1:{SERVER_PORT} (solo localhost).")
    print(f"Sesión para la UI: {session_path}")
    print("La UI dispara el bot con el botón 'Ejecutar bot'. Ctrl+C para salir.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if current_process is not None and current_process.poll() is None:
            print("Deteniendo el bot en curso...")
            current_process.terminate()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
