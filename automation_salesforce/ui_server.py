"""Servidor local mínimo para que la UI dispare el bot sin usar la terminal.

Escucha solo en ``127.0.0.1`` y exige un token aleatorio por sesión que la UI
lee de ``ui_output/bot_session.json`` con el permiso de carpeta que ya tiene.
Solo permite lanzar el runner de la cola activa: no ejecuta comandos
arbitrarios. Todo queda en la máquina local.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from browser_factory import (
    debugger_is_listening,
    detect_browser,
    launch_persistent_browser,
)

ROOT = Path(__file__).parent


def load_config() -> dict:
    with (ROOT / "config.json").open(encoding="utf-8") as file:
        return json.load(file)


def local_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


SERVER_PORT = 8765
ACTIVE_QUEUE = "cola_activa.json"
SESSION_FILE = "bot_session.json"
UI_PAGE = ROOT.parent / "documentador_predictivo.html"
TOKEN_PLACEHOLDER = "__BOT_SERVER_TOKEN__"

# Archivos JSON que la UI lee/escribe a través del servidor. Solo estos nombres,
# siempre dentro de las carpetas operativas: nada de rutas arbitrarias.
API_FILES = {
    "/api/queue": ROOT / "queues" / "cola_activa.json",
    "/api/results": ROOT / "queues" / "cola_activa.resultado.json",
    "/api/metrics": ROOT / "queues" / "cola_activa.metricas.json",
    "/api/snapshots": ROOT / "ui_output" / "cola_activa.snapshots.json",
}
WRITABLE_API = {"/api/queue"}

current_process: subprocess.Popen | None = None
# Serializa el congelado de la cola y el arranque del runner: un PUT o una
# segunda ejecución no pueden mezclarse con la tanda activa.
run_lock = threading.Lock()


def app_version() -> str:
    """Versión de la app: única fuente ``APP_VERSION`` en la página principal."""
    try:
        match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', UI_PAGE.read_text(encoding="utf-8"))
    except OSError:
        match = None
    return match.group(1) if match else "desconocida"


def freeze_active_queue(queue_directory: Path, run_id: str) -> Path:
    """Copia la cola activa a un archivo inmutable identificado por ``run_id``.

    El runner trabaja sobre esa copia: un ``PUT /api/queue`` posterior solo
    prepara el borrador de la próxima tanda sin alterar la ejecución en curso.
    """
    active_path = queue_directory / ACTIVE_QUEUE
    try:
        payload = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    frozen = {
        **payload,
        "run_id": run_id,
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    frozen_path = queue_directory / f"{run_id}.json"
    frozen_path.write_text(json.dumps(frozen, indent=2, ensure_ascii=False), encoding="utf-8")
    return frozen_path


def find_listening_pid(port: str) -> str | None:
    """Devuelve el PID que escucha en el puerto local indicado, si existe."""
    try:
        output = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3].upper() == "LISTENING" and parts[1].endswith(f":{port}"):
            return parts[4]
    return None


def restart_browser(config: dict) -> None:
    """Reinicia el navegador del perfil dedicado: cierra el que escucha en el
    puerto de depuración y lo vuelve a abrir con Salesforce y la app."""
    debugger_address = config.get("debugger_address", "127.0.0.1:9222")
    port = debugger_address.rpartition(":")[2]
    pid = find_listening_pid(port)
    if pid:
        subprocess.run(
            ["taskkill", "/PID", pid, "/T", "/F"],
            capture_output=True,
            timeout=30,
        )
        deadline = time.monotonic() + 15
        while debugger_is_listening(debugger_address) and time.monotonic() < deadline:
            time.sleep(0.5)
    subprocess.run(["taskkill", "/IM", "msedgedriver.exe", "/F"], capture_output=True)
    _, executable = detect_browser(config["browser"])
    urls = [config["salesforce_url"], f"http://127.0.0.1:{SERVER_PORT}/"]
    launch_persistent_browser(executable, local_path(config["profile_directory"]), debugger_address, urls)


def write_session_file(ui_output_directory: Path, port: int, token: str) -> Path:
    """Publica puerto y token donde la UI puede leerlos (carpeta ya vinculada)."""
    ui_output_directory.mkdir(parents=True, exist_ok=True)
    session_path = ui_output_directory / SESSION_FILE
    session_path.write_text(
        json.dumps({"port": port, "token": token}, indent=2),
        encoding="utf-8",
    )
    return session_path


def make_handler(token: str, config: dict | None = None):
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
            self.send_header("Access-Control-Allow-Headers", "X-Bot-Token, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, PUT")
            self.end_headers()

        def _serve_ui_page(self) -> None:
            if not UI_PAGE.is_file():
                self._send(404, {"error": "no se encontró documentador_predictivo.html"})
                return
            html = UI_PAGE.read_text(encoding="utf-8").replace(TOKEN_PLACEHOLDER, token)
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_api_file(self) -> None:
            target = API_FILES[self.path]
            try:
                payload = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = []
            self._send(200, payload if isinstance(payload, (list, dict)) else [])

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                self._serve_ui_page()
                return
            if self.path == "/status":
                running = current_process is not None and current_process.poll() is None
                self._send(
                    200,
                    {
                        "running": running,
                        "exit_code": None if running or current_process is None else current_process.returncode,
                        "version": app_version(),
                    },
                )
                return
            if self.path in API_FILES:
                if not self._authorized():
                    self._send(403, {"error": "token inválido o ausente"})
                    return
                self._read_api_file()
                return
            if self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            self._send(404, {"error": "ruta desconocida"})

        def do_PUT(self) -> None:
            if self.path not in WRITABLE_API:
                self._send(404, {"error": "ruta desconocida"})
                return
            if not self._authorized():
                self._send(403, {"error": "token inválido o ausente"})
                return
            try:
                body_length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(body_length).decode("utf-8"))
            except (ValueError, json.JSONDecodeError):
                self._send(400, {"error": "JSON inválido"})
                return
            if not isinstance(payload, dict) or not isinstance(payload.get("leads"), list):
                self._send(400, {"error": "se esperaba un objeto con la lista 'leads'"})
                return
            target = API_FILES[self.path]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            self._send(200, {"status": "guardada", "leads": len(payload["leads"])})

        def do_POST(self) -> None:
            global current_process
            if not self._authorized():
                self._send(403, {"error": "token inválido o ausente"})
                return
            if self.path == "/api/restart-browser":
                if current_process is not None and current_process.poll() is None:
                    self._send(409, {"error": "el bot está corriendo; esperá a que termine"})
                    return
                self._send(202, {"status": "reiniciando el navegador del bot"})
                threading.Thread(target=restart_browser, args=(config or load_config(),), daemon=True).start()
                return
            if self.path != "/run":
                self._send(404, {"error": "ruta desconocida"})
                return
            with run_lock:
                if current_process is not None and current_process.poll() is None:
                    self._send(409, {"status": "ya esta corriendo"})
                    return
                queue_directory = ROOT / "queues"
                queue_directory.mkdir(parents=True, exist_ok=True)
                run_id = "run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + secrets.token_hex(3)
                try:
                    frozen_path = freeze_active_queue(queue_directory, run_id)
                except OSError:
                    self._send(500, {"error": "no se pudo congelar la cola activa"})
                    return
                cfg = config or load_config()
                current_process = subprocess.Popen(
                    [
                        sys.executable,
                        str(ROOT / "run_document_queue.py"),
                        "--auto",
                        "--run-id", run_id,
                        "--results", str(ROOT / "queues" / "cola_activa.resultado.json"),
                        "--snapshots", str(ROOT / cfg.get("ui_output_directory", "ui_output") / "cola_activa.snapshots.json"),
                        "--metrics", str(ROOT / "queues" / "cola_activa.metricas.json"),
                        str(frozen_path),
                    ],
                    cwd=str(ROOT),
                )
            self._send(202, {"status": "iniciado", "queue": ACTIVE_QUEUE, "run_id": run_id})

        def log_message(self, *_args) -> None:
            pass

    return BotRequestHandler


def main() -> int:
    config = load_config()
    ui_output_directory = ROOT / config.get("ui_output_directory", "ui_output")
    token = secrets.token_hex(16)
    session_path = write_session_file(ui_output_directory, SERVER_PORT, token)
    server = ThreadingHTTPServer(("127.0.0.1", SERVER_PORT), make_handler(token, config))
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
