import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from lifecycle import install_stop_signals, parent_stream, restore_signals, watch_parent_stream


class LifecycleTests(unittest.TestCase):
    def test_pipe_is_live_until_parent_writer_closes(self):
        reader, writer = os.pipe()
        stop = threading.Event()
        with os.fdopen(reader, "rb", buffering=0) as stream:
            watcher = watch_parent_stream(stream, stop)
            self.assertFalse(stop.wait(0.03))
            os.write(writer, b"ignored")
            self.assertFalse(stop.wait(0.03))
            os.close(writer)
            self.assertTrue(stop.wait(2))
            watcher.join(2)

    def test_missing_stream_and_read_error_fail_closed(self):
        stop = threading.Event()
        self.assertIsNone(watch_parent_stream(None, stop))
        self.assertTrue(stop.is_set())
        stop.clear()
        stream = io.BytesIO()
        stream.close()
        thread = watch_parent_stream(stream, stop)
        self.assertTrue(stop.wait(2))
        thread.join(2)

    def test_regular_stdin_uses_binary_stream(self):
        stream = io.TextIOWrapper(io.BytesIO())
        with patch("sys.stdin", stream):
            self.assertIs(parent_stream(), stream.buffer)

    def test_early_child_exit_does_not_hold_buffered_stdin_finalization_lock(self):
        code = (
            "import threading,time; from lifecycle import parent_stream,watch_parent_stream; "
            "watch_parent_stream(parent_stream(),threading.Event()); time.sleep(.08)"
        )
        child = subprocess.Popen([sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parent, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            # Keep the launcher's write handle open while the child exits for an
            # unrelated reason (e.g. invalid config or an explicit stop file).
            self.assertEqual(child.wait(timeout=4), 0)
            child.stdin.close()
            child.stdin = None
            self.assertEqual(child.communicate(timeout=2), (b"", b""))
        finally:
            if child.poll() is None:
                child.kill()
            if child.stdin is not None:
                child.stdin.close()
                child.stdin = None
            child.communicate(timeout=3)

    def test_sigterm_requests_cleanup_and_handlers_restore(self):
        stop = threading.Event()
        old = signal.getsignal(signal.SIGTERM)
        previous = install_stop_signals(stop)
        try:
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            self.assertTrue(stop.is_set())
        finally:
            restore_signals(previous)
        self.assertEqual(signal.getsignal(signal.SIGTERM), old)

    def test_runtime_publication_failure_does_not_prevent_network_close(self):
        from ingame_client import GameBridge
        bridge = GameBridge.__new__(GameBridge)
        bridge.stop_path = Path("/unlikely-szero-stop-file")
        bridge.native_disconnect = Mock(side_effect=OSError("runtime unavailable"))
        bridge.native_rpc = SimpleNamespace(close=Mock(side_effect=OSError("IPC unavailable")))
        closed = Mock()
        bridge.client = SimpleNamespace(close=closed)
        bridge.publish = Mock(side_effect=OSError("status unavailable"))
        stop = threading.Event()
        stop.set()
        with self.assertLogs("szero_lan", level="WARNING"):
            bridge.run(stop)
        closed.assert_called_once_with()
        self.assertIsNone(bridge.client)

    def test_os_closes_liveness_pipe_when_launcher_is_killed(self):
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / "child-cleanup.txt"
            child = (
                "import pathlib,sys,threading; from lifecycle import watch_parent_stream; "
                "stop=threading.Event(); watch_parent_stream(sys.stdin.buffer,stop); "
                "stop.wait(10); pathlib.Path(sys.argv[1]).write_text(str(stop.is_set()))"
            )
            parent = (
                "import subprocess,sys,time; "
                "p=subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]],"
                "stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                "print('ready',flush=True); time.sleep(15)"
            )
            process = subprocess.Popen([sys.executable, "-c", parent, child, str(marker)],
                                       cwd=Path(__file__).resolve().parent, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(), "ready")
                process.kill()
                process.wait(3)
                deadline = time.monotonic() + 4
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(0.03)
                self.assertEqual(marker.read_text(), "True")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(3)
                process.stdout.close()
                process.stderr.close()


class BridgeLoggingTests(unittest.TestCase):
    def test_bridge_logging_requires_explicit_one_without_affecting_run(self):
        import ingame_client
        original_disabled = ingame_client.LOG.disabled
        try:
            for value in (None, "0", "true", "1"):
                with self.subTest(value=value), tempfile.TemporaryDirectory() as temporary, \
                     patch.dict(os.environ, {}, clear=False), \
                     patch.object(sys, "argv", ["bridge", "--game-root", temporary,
                                               "--runtime", str(Path(temporary) / "runtime.lua")]), \
                     patch.object(ingame_client, "configure_logging") as configure, \
                     patch.object(ingame_client, "GameBridge") as bridge, \
                     patch.object(ingame_client, "install_stop_signals", return_value={}), \
                     patch.object(ingame_client, "restore_signals"):
                    if value is None:
                        os.environ.pop("SZERO_LAN_MOD_LOGGING", None)
                    else:
                        os.environ["SZERO_LAN_MOD_LOGGING"] = value
                    self.assertEqual(ingame_client.main(), 0)
                    bridge.return_value.run.assert_called_once()
                    if value == "1":
                        configure.assert_called_once_with(Path(temporary) / "runtime.client.log")
                        self.assertFalse(ingame_client.LOG.disabled)
                    else:
                        configure.assert_not_called()
                        self.assertTrue(ingame_client.LOG.disabled)
                        self.assertFalse((Path(temporary) / "runtime.client.log").exists())
        finally:
            ingame_client.LOG.disabled = original_disabled


class BridgeParentPipeTests(unittest.TestCase):
    def setUp(self):
        import test_native_session_bridge as fixture
        fixture.NativeSessionBridgeTests.setUp(self)

    def tearDown(self):
        import test_native_session_bridge as fixture
        fixture.NativeSessionBridgeTests.tearDown(self)

    def test_actual_bridge_eof_disconnects_server_and_removes_native_endpoint(self):
        import json
        import test_native_session_bridge as fixture
        folder = Path(self.folder.name)
        (folder / "SzeroLAN.json").write_text(json.dumps({
            "server_host": "127.0.0.1", "server_port": self.server.port,
            "name": "liveness fixture", "native_search": True, "native_session": True}))
        runtime = folder / ("lan_runtime_" + "d" * 32 + ".lua")
        process = subprocess.Popen([sys.executable, str(Path(__file__).with_name("ingame_client.py")),
            "--game-root", str(folder), "--runtime", str(runtime), "--watch-parent-stdin"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=dict(os.environ, SZERO_LAN_MOD_LOGGING="0"))
        try:
            self.assertTrue(fixture.until(lambda: len(self.server.peers) == 1))
            self.assertIsNone(process.poll())
            process.stdin.close()
            process.stdin = None
            stdout, stderr = process.communicate(timeout=8)
            self.assertEqual(process.returncode, 0, (stdout, stderr))
            self.assertEqual((stdout, stderr), (b"", b""))
            self.assertFalse(runtime.with_suffix(".client.log").exists())
            self.assertTrue(fixture.until(lambda: not self.server.peers))
            self.assertFalse(runtime.with_suffix(".native.endpoint").exists())
            self.assertFalse(runtime.with_suffix(".service.endpoint").exists())
            from ingame_client import lua_value
            self.assertIn(lua_value("LAN bridge stopped"), runtime.with_suffix(".ui.lua").read_text())
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=3)


if __name__ == "__main__":
    unittest.main()
