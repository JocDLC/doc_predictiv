"""Tests del guardián del servidor: reinicio, backoff, marcador fatal."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import server_guardian as guardian


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


class FakeStop:
    def __init__(self):
        self._set = False
        self.waits = []

    def is_set(self):
        return self._set

    def set(self):
        self._set = True

    def wait(self, seconds):
        self.waits.append(seconds)
        return self._set


class FakeProc:
    """Proceso falso: muere tras ``polls_until_death`` consultas, o nunca."""

    def __init__(self, polls_until_death=None, exit_code=1):
        self.polls = 0
        self.death_at = polls_until_death
        self.exit_code = exit_code
        self.terminated = False
        self.killed = False

    def poll(self):
        self.polls += 1
        if self.death_at is not None and self.polls >= self.death_at:
            return self.exit_code
        return None

    def is_alive(self):
        """True si el proceso seguiría sirviendo el puerto (no muta estado)."""
        return self.death_at is None or self.polls < self.death_at

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return self.exit_code

    def kill(self):
        self.killed = True


class GuardianTests(unittest.TestCase):
    def _run(self, procs, probe=None, probe_factory=None, stop_after_sleeps=None):
        """Corre supervise con hijos falsos; el reloj/sleep son instantáneos.

        El probe por defecto refleja la realidad del puerto: responde solo
        mientras el último hijo spawneado sigue vivo. ``probe_factory``
        recibe la lista ``spawned`` y devuelve el probe a usar (un server
        ajeno se modela así).
        """
        clock = FakeClock()
        stop = FakeStop()
        spawned = []
        sleeps = [0]
        queue = iter(procs)
        if probe is None:
            if probe_factory is not None:
                probe = probe_factory(spawned)
            else:

                def probe():
                    return bool(spawned) and spawned[-1].is_alive()

        def spawn():
            proc = next(queue)
            spawned.append(proc)
            return proc

        def sleep(seconds):
            clock.sleep(seconds)
            sleeps[0] += 1
            if stop_after_sleeps is not None and sleeps[0] >= stop_after_sleeps:
                stop.set()

        tmp = TemporaryDirectory()
        log_dir = Path(tmp.name) / "logs"
        code = guardian.supervise(
            spawn=spawn,
            probe=probe,
            sleep=sleep,
            now=clock.now,
            log_dir=log_dir,
            fatal_marker=log_dir / "server_fatal.log",
            stop=stop,
        )
        return code, spawned, log_dir, tmp, stop

    def test_dead_child_restarts_and_logs_crash(self):
        code, spawned, log_dir, tmp, _ = self._run(
            [FakeProc(polls_until_death=2, exit_code=1), FakeProc()],
            stop_after_sleeps=3,
        )
        try:
            self.assertEqual(code, 0)
            self.assertEqual(len(spawned), 2)
            crashes = list(log_dir.glob("server_crash_*.log"))
            self.assertEqual(len(crashes), 1)
            self.assertIn("exit:1", crashes[0].read_text(encoding="utf-8"))
        finally:
            tmp.cleanup()

    def test_hung_child_is_restarted(self):
        code, spawned, log_dir, tmp, _ = self._run(
            [FakeProc(), FakeProc()],
            probe=lambda: False,  # /status nunca responde
            stop_after_sleeps=100,  # para tras re lanzar al hijo colgado
        )
        try:
            self.assertEqual(code, 0)
            self.assertEqual(len(spawned), 2)
            self.assertTrue(spawned[0].terminated)
            crash = next(log_dir.glob("server_crash_*.log")).read_text(encoding="utf-8")
            self.assertIn("colgado", crash)
        finally:
            tmp.cleanup()

    def test_crash_burst_writes_fatal_marker(self):
        procs = [FakeProc(polls_until_death=1, exit_code=1) for _ in range(guardian.MAX_CRASHES)]
        code, spawned, log_dir, tmp, stop = self._run(procs)
        try:
            self.assertEqual(code, 2)
            self.assertEqual(len(spawned), guardian.MAX_CRASHES)
            self.assertTrue((log_dir / "server_fatal.log").exists())
            self.assertEqual(len(list(log_dir.glob("server_crash_*.log"))), guardian.MAX_CRASHES)
            # backoff creciente entre reinicios (el primer reintento es inmediato)
            self.assertEqual(stop.waits[:3], [5, 15, 30])
        finally:
            tmp.cleanup()

    def test_clean_stop_terminates_child_and_exits_zero(self):
        code, spawned, _, tmp, _ = self._run([FakeProc()], stop_after_sleeps=1)
        try:
            self.assertEqual(code, 0)
            self.assertTrue(spawned[0].terminated)
        finally:
            tmp.cleanup()

    def test_supervise_adopts_an_already_serving_port(self):
        """Si /status ya responde no se spawnea: en Windows dos procesos
        pueden bindear el mismo puerto y cada uno tendría su token."""
        code, spawned, _, tmp, _ = self._run([], probe=lambda: True, stop_after_sleeps=3)
        try:
            self.assertEqual(code, 0)
            self.assertEqual(spawned, [])
        finally:
            tmp.cleanup()

    def test_exit_zero_is_an_intentional_reload_not_a_crash(self):
        """exit:0 (/api/reload, lock de instancia) se relanza sin crash log."""
        code, spawned, log_dir, tmp, _ = self._run(
            [FakeProc(polls_until_death=1, exit_code=0), FakeProc()],
            stop_after_sleeps=3,
        )
        try:
            self.assertEqual(code, 0)
            self.assertEqual(len(spawned), 2)
            self.assertEqual(list(log_dir.glob("server_crash_*.log")), [])
        finally:
            tmp.cleanup()

    def test_supervise_adopts_when_the_port_survives_the_child(self):
        """El hijo murió pero otro proceso quedó sirviendo: se adopta, no se
        spawnea encima."""

        # True solo cuando el último hijo murió = el puerto lo ocupa otro.
        def foreign(spawned):
            return lambda: bool(spawned) and not spawned[-1].is_alive()

        code, spawned, log_dir, tmp, _ = self._run(
            [FakeProc(polls_until_death=1, exit_code=1), FakeProc()],
            probe_factory=foreign,
            stop_after_sleeps=3,
        )
        try:
            self.assertEqual(code, 0)
            self.assertEqual(len(spawned), 1)  # solo el que murió; no respawnea
            self.assertEqual(list(log_dir.glob("server_crash_*.log")), [])
        finally:
            tmp.cleanup()

    def test_write_crash_log_keeps_tail_and_reason(self):
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "logs"
            log_dir.mkdir()
            guardian_log = log_dir / "ui_server.log"
            import server_guardian

            original = server_guardian.UI_SERVER_LOG
            server_guardian.UI_SERVER_LOG = guardian_log
            try:
                guardian_log.write_bytes(b"x" * 2000)
                crash_path = guardian.write_crash_log("exit:3", log_dir)
            finally:
                server_guardian.UI_SERVER_LOG = original
            content = crash_path.read_text(encoding="utf-8")
            self.assertIn("motivo: exit:3", content)
            self.assertIn("x" * 100, content)


if __name__ == "__main__":
    unittest.main()
