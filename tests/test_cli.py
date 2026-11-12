"""External native protocol checks; no upstream compiler or source checkout."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import external_cli
from build_cli import native_target


@contextmanager
def slow_discovery():
    stop = threading.Event()
    entered = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            entered.set()
            stop.wait(10)
            self.close_connection = True

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port), entered
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if thread.is_alive():
            raise RuntimeError("native CLI fixture server did not stop")


class ExternalNativeTests(unittest.TestCase):
    def test_external_only_no_source_build(self):
        config = json.loads((ROOT / "template.json").read_text())
        self.assertEqual(config["cli_source"], external_cli.PROFILE)
        self.assertFalse(any((ROOT / "cli").rglob("*.*")))

    def native_binary(self):
        target = os.environ.get("CLI_TARGET")
        if not target:
            self.skipTest("native acquisition is performed by CI after static tests")
        self.assertEqual(target, native_target(), "native CLI tests must not use emulation")
        release = external_cli.load_pin(ROOT)
        binary = ROOT / "build" / target / ("oidc-cli.exe" if target == "windows-x64" else "oidc-cli")
        external_cli.verify_binary(ROOT, binary, target)
        return binary, release

    def test_native_version_if_explicitly_requested(self):
        binary, release = self.native_binary()
        external_cli.version_check(binary, release["version"])

    def native_failure(self, *, cancel):
        binary, _ = self.native_binary()
        with slow_discovery() as (issuer, entered):
            configuration = {
                "protocol_version": 1, "issuer": issuer, "client_id": "wrapper-native-probe",
                "allow_insecure_loopback_http": True, "open_browser": False, "include_tokens": False,
                "timeout_seconds": 10 if cancel else 1, "http_timeout_seconds": 10,
            }
            data = (json.dumps(configuration) + "\n").encode("utf-8")
            process = subprocess.Popen([str(binary), "authenticate"], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                if cancel:
                    process.stdin.write(data)
                    process.stdin.close()
                    process.stdin = None
                    self.assertTrue(entered.wait(4), "native CLI did not enter the disposable discovery fixture")
                    process.send_signal(signal.SIGTERM)
                    output, diagnostics = process.communicate(timeout=6)
                else:
                    output, diagnostics = process.communicate(data, timeout=8)
                self.assertLessEqual(len(output), 262144)
                self.assertLessEqual(len(diagnostics), 65536)
                value = json.loads(output.decode("utf-8"))
                expected_exit, expected_code = (5, "cancelled") if cancel else (4, "timeout")
                self.assertEqual(process.returncode, expected_exit, "native CLI lifecycle exit mismatch")
                self.assertTrue(
                    isinstance(value, dict) and type(value.get("protocol_version")) is int
                    and value["protocol_version"] == 1 and value.get("ok") is False
                    and isinstance(value.get("error"), dict) and value["error"].get("code") == expected_code,
                    "native CLI lifecycle protocol mismatch")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)

    def test_native_timeout_if_explicitly_requested(self):
        self.native_failure(cancel=False)

    @unittest.skipIf(os.name == "nt", "POSIX SIGTERM cancellation; Windows 4D cancellation remains separate")
    def test_native_cancellation_if_explicitly_requested(self):
        self.native_failure(cancel=True)


if __name__ == "__main__":
    unittest.main()
