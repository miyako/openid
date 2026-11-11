"""Source/fixture contract guards; real execution lives in the 4D host suite."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "component/openid/Project/Sources/Classes"


class WrapperContractTests(unittest.TestCase):
    def test_public_api_does_not_wait_or_execute_synchronously(self):
        for name in ("Client", "Task"):
            source = (CLASSES / (name + ".4dm")).read_text()
            self.assertNotIn(".wait(", source)
            self.assertNotIn(".execute(", source)
        task = (CLASSES / "Task.4dm").read_text()
        self.assertIn("CALL WORKER(", task)
        self.assertIn('New shared object("done"', task)
        self.assertIn("This._state.cancelled:=True", task)

    def test_no_sensitive_process_envelope_is_returned(self):
        protocol = (CLASSES / "_Protocol.4dm").read_text()
        self.assertNotIn('"stdout";', protocol)
        self.assertNotIn('"stderr";', protocol)
        self.assertNotIn('"message"; $payload.error.message', protocol)
        self.assertIn("unexpected_tokens", protocol)
        self.assertIn('equal($payload.identity.issuer; $configuration.issuer)', protocol)

    def test_config_allowlist_is_exact_upstream_protocol(self):
        source = (CLASSES / "_Config.4dm").read_text()
        allowlist = next(line for line in source.splitlines()
                         if 'New collection("issuer"; "client_id";' in line)
        import re
        fields = set(re.findall(r'"([^"]+)"', allowlist))
        self.assertEqual(fields, {
            "protocol_version", "issuer", "client_id", "scopes",
            "listen_address", "callback_path", "timeout_seconds",
            "http_timeout_seconds", "open_browser",
            "allow_insecure_loopback_http", "include_tokens", "parent_pid",
        })

    def test_owner_identity_and_shared_results_use_runtime_validated_apis(self):
        source = (CLASSES / "_Owner.4dm").read_text()
        self.assertIn("PROCESS PROPERTIES(", source)
        self.assertIn("$current.ID=$original.ID", source)
        self.assertNotIn("Get process activity", source)
        self.assertNotIn(".split(", (CLASSES / "_Config.4dm").read_text())
        run = (CLASSES / "_Run.4dm").read_text()
        self.assertIn("ck shared; This.state)", run)
        self.assertIn("unsupported_context", (CLASSES / "Task.4dm").read_text())

    def test_all_headless_projects_declare_dependencies_before_open(self):
        for project in ROOT.glob("**/*.4DProject"):
            if any(part in {"build", ".tools", ".git"} for part in project.parts):
                continue
            manifest = project.parent / "Sources/dependencies.json"
            self.assertTrue(manifest.is_file(), str(project))
            self.assertIsInstance(json.loads(manifest.read_text())["dependencies"], dict)

    def test_host_registry_requires_sensitive_and_lifecycle_checks(self):
        contract = json.loads((ROOT / "tests/host/contract.json").read_text())
        paths = {entry["path"] for entry in contract["feature"]["assertions"]}
        paths.update(entry["path"] for entry in contract["desktop"]["assertions"])
        for path in ("/activeCancellation/error/code", "/cliTimeout/error/code",
                     "/ownerGone/error/code", "/leakedWorkers", "/tokenOptInVerified",
                     "/tokenOptIn", "/stdoutAtLimit", "/stdoutOverflow",
                     "/stderrAtLimit", "/stderrOverflow"):
            self.assertIn(path, paths)
        fixture = (ROOT / "tests/host/Project/Sources/Methods/Smoke.4dm").read_text()
        self.assertLess(fixture.index('OB REMOVE($report; "tokenOptIn")'),
                        fixture.rindex("$statusFile.setText("))


if __name__ == "__main__":
    unittest.main()
