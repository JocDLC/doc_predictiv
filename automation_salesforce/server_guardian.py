"""Guardián del servidor local: mantiene vivo ``ui_server.py``.

Lanza el servidor como proceso hijo y lo supervisa: si el proceso muere o deja
de responder a ``GET /status``, copia el final de su salida a
``logs/server_crash_<timestamp>.log`` y lo reinicia con una espera creciente.
Tras ``MAX_CRASHES`` caídas en ``CRASH_WINDOW_SECONDS`` se detiene y deja un
marcador fatal para no reiniciar en bucle un servidor roto.

Uso: ``python server_guardian.py`` (``INICIAR.bat`` lo lanza minimizado).
"""

from __future__ import annotations

import collections
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER_SCRIPT = "ui_server.py"
STATUS_URL = "http://127.0.0.1:8765/status"
LOG_DIRECTORY = ROOT / "logs"
UI_SERVER_LOG = LOG_DIRECTORY / "ui_server.log"
FATAL_MARKER = LOG_DIRECTORY / "server_fatal.log"

PROBE_INTERVAL_SECONDS = 30
PROBE_TIMEOUT_SECONDS = 10
MAX_FAILED_PROBES = 3
POLL_SECONDS = 1.0
STARTUP_GRACE_SECONDS = 15
CRASH_WINDOW_SECONDS = 600
MAX_CRASHES = 5
BACKOFF_SECONDS = [0, 5, 15, 30, 60, 120, 300]
CRASH_LOG_TAIL_BYTES = 64 * 1024


def log(message: str) -> None:
    print(f"[guardian {datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def probe_status() -> bool:
    """True si el servidor responde /status; no requiere token."""
    try:
        with urllib.request.urlopen(STATUS_URL, timeout=PROBE_TIMEOUT_SECONDS) as response:
            return response.status == 200
    except Exception:  # noqa: BLE001 — cualquier falla cuenta como "no responde"
        return False


def write_crash_log(reason: str, log_dir: Path = LOG_DIRECTORY) -> Path:
    """Guarda el final de ui_server.log junto al motivo de la caída."""
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    crash_path = log_dir / f"server_crash_{stamp}.log"
    tail = ""
    try:
        with open(UI_SERVER_LOG, "rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - CRASH_LOG_TAIL_BYTES))
            tail = handle.read().decode("utf-8", errors="replace")
    except OSError:
        tail = "(sin salida registrada)"
    crash_path.write_text(
        f"motivo: {reason}\nhora: {datetime.now().isoformat(timespec='seconds')}\n\n{tail}",
        encoding="utf-8",
    )
    return crash_path


def wait_child(proc, probe, sleep, now, stop: threading.Event) -> str | None:
    """Espera al hijo; devuelve None si hay que cerrar, o el motivo de la caída."""
    failed_probes = 0
    next_probe = now() + STARTUP_GRACE_SECONDS
    while not stop.is_set():
        exit_code = proc.poll()
        if exit_code is not None:
            return f"exit:{exit_code}"
        current = now()
        if current >= next_probe:
            if probe():
                failed_probes = 0
            else:
                failed_probes += 1
                log(f"sondeo /status falló ({failed_probes}/{MAX_FAILED_PROBES})")
            if failed_probes >= MAX_FAILED_PROBES:
                return "colgado: /status sin respuesta"
            next_probe = current + PROBE_INTERVAL_SECONDS
        sleep(POLL_SECONDS)
    return None


def terminate_child(proc) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:  # noqa: BLE001 — si no muere, va el kill
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


def supervise(
    *,
    spawn,
    probe=probe_status,
    sleep=time.sleep,
    now=time.monotonic,
    log_dir: Path = LOG_DIRECTORY,
    fatal_marker: Path = FATAL_MARKER,
    stop: threading.Event | None = None,
) -> int:
    """Bucle principal: devuelve 0 en apagado limpio, 2 en caídas repetidas."""
    stop = stop or threading.Event()
    crashes: collections.deque[float] = collections.deque()
    backoff_index = 0
    while not stop.is_set():
        if probe():
            # Otro proceso ya sirve el puerto (instancia manual, un server
            # que sobrevivió a un relanzado del guardián): en Windows dos
            # procesos pueden bindear el mismo puerto, así que spawnear
            # crearía una segunda instancia conviviendo con tokens
            # distintos. Se vigila desde afuera y se spawneara recién
            # cuando deje de responder.
            log("el puerto ya responde /status; supervisando sin spawnear")
            while probe() and not stop.is_set():
                sleep(PROBE_INTERVAL_SECONDS)
            continue
        proc = spawn()
        spawned_at = now()
        reason = wait_child(proc, probe, sleep, now, stop)
        if reason is None:
            terminate_child(proc)
            log("apagado limpio del servidor")
            return 0
        terminate_child(proc)
        if probe():
            # El hijo murió pero el puerto sigue servido por otro proceso:
            # no hay vacante, se adopta al ocupante en vez de spawnear.
            log("el puerto sigue servido por otro proceso; se adopta")
            continue
        if reason == "exit:0":
            # Convención con ui_server: exit 0 = reinicio intencional
            # (/api/reload, lock de instancia, puerto ocupado). No es una
            # caída: relanzar al instante, sin crash log ni backoff.
            log("reinicio intencional (exit 0); relanzando sin penalizar")
            continue
        crash_log = write_crash_log(reason, log_dir)
        log(f"servidor caído ({reason}); salida en {crash_log.name}; reiniciando")
        crashes.append(now())
        while crashes and now() - crashes[0] > CRASH_WINDOW_SECONDS:
            crashes.popleft()
        if len(crashes) >= MAX_CRASHES:
            log_dir.mkdir(parents=True, exist_ok=True)
            fatal_marker.write_text(
                f"{datetime.now().isoformat(timespec='seconds')} el servidor cayó "
                f"{MAX_CRASHES} veces en {CRASH_WINDOW_SECONDS // 60} minutos; "
                "revisar los server_crash_*.log\n",
                encoding="utf-8",
            )
            log(f"demasiadas caídas seguidas; marcador fatal en {fatal_marker.name}")
            return 2
        if now() - spawned_at > CRASH_WINDOW_SECONDS:
            backoff_index = 0  # una corrida larga y sana reinicia la espera
        delay = BACKOFF_SECONDS[min(backoff_index, len(BACKOFF_SECONDS) - 1)]
        backoff_index += 1
        if delay:
            stop.wait(delay)
    return 0


def spawn_server() -> subprocess.Popen:
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    log_handle = open(UI_SERVER_LOG, "ab", buffering=0)
    return subprocess.Popen(
        [sys.executable, SERVER_SCRIPT],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )


def main() -> int:
    log(f"guardián iniciado; supervisando {SERVER_SCRIPT}")
    try:
        return supervise(spawn=spawn_server)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
