"""Universal external delivery retains native per-target verification evidence."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import accept_hosted
import build_provenance
import ci_config
import external_cli
import release_assets
import test_delivery
import test_host_runner


class ExternalDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_delivery.DeliveryTests("test_matrix_only_selected_language")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.fixture.config.update(cli="oidc-cli", cli_source=external_cli.PROFILE)
        self.fixture.write_config()
        self.mac = self.fixture.mac.with_name("oidc-cli")
        self.fixture.mac.rename(self.mac)
        self.mac.chmod(0o755)
        self.windows = self.fixture.windows.with_name("oidc-cli.exe")
        self.fixture.windows.rename(self.windows)
        shutil.copytree(ROOT / "scripts/licenses", self.root / "scripts/licenses")
        for name in ("external_cli.py", "build_cli.py", "build_provenance.py"):
            shutil.copy2(ROOT / "scripts" / name, self.root / "scripts" / name)
        self.pin = json.loads((ROOT / "scripts/oidc-cli-pin.json").read_text())
        self.release = self.pin["release"]
        for key, binary in (("macos", self.mac), ("windows-x64", self.windows)):
            self.release["assets"][key]["binary_sha256"] = external_cli.digest(binary)
        (self.root / "scripts/oidc-cli-pin.json").write_text(json.dumps(self.pin))
        for notice in self.release["licenses"]:
            shutil.copy2(self.root / notice["path"],
                         self.fixture.component / "Resources/licenses" / Path(notice["path"]).name)
        for target in ci_config.TARGETS:
            source = self.windows if target == "windows-x64" else self.mac
            binary = self.root / "build" / target / source.name
            binary.parent.mkdir()
            shutil.copy2(source, binary)
            status = build_provenance.record(self.root, target, binary, True, external_cli.PROFILE)
            status["external"] = external_cli.release_provenance(self.release, target)
            binary.with_name("build-manifest.json").write_text(json.dumps(status))
        self.fixture.write_status()

    def manifest(self, target):
        return self.root / "build" / target / "build-manifest.json"

    def test_universal_matrix_and_assembly_require_three_policy_bound_native_manifests(self):
        self.assertEqual([entry["target"] for entry in ci_config.matrix(self.fixture.config)["include"]],
                         list(ci_config.TARGETS))
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/example-component"}), \
                patch.object(external_cli, "signature_check"), \
                patch.object(build_provenance, "commit", return_value=None), \
                patch.object(ci_config.subprocess, "run") as run:
            ci_config.assemble(self.root)
            run.assert_not_called()
            self.assertEqual(self.mac.read_bytes(), test_delivery.synthetic_universal())
            for target in ci_config.TARGETS:
                manifest = self.manifest(target)
                original = json.loads(manifest.read_text())
                for field, value in (("execution", "not_run"), ("commit", "b" * 40),
                                     ("source_sha256", "0" * 64), ("binary_sha256", "0" * 64)):
                    manifest.write_text(json.dumps({**original, field: value}))
                    with self.subTest(target=target, field=field), self.assertRaises(ValueError):
                        ci_config.assemble(self.root)
                manifest.write_text(json.dumps(original))
                for wrong in ("passed", "not_run", "not_applicable"):
                    bad = copy.deepcopy(original)
                    verification = bad["external"]["verification"]
                    if verification["online_notarization"] == wrong:
                        continue
                    verification["online_notarization"] = wrong
                    manifest.write_text(json.dumps(bad))
                    with self.subTest(target=target, wrong=wrong), self.assertRaises(ValueError):
                        ci_config.assemble(self.root)
                manifest.unlink()
                with self.assertRaisesRegex(ValueError, "missing build-manifest"):
                    ci_config.assemble(self.root)
                manifest.write_text(json.dumps(original))

    def test_hosted_evidence_retains_tiers_and_fixture_environment_is_isolated(self):
        tool = self.root / "tool4d"
        tool.write_bytes(b"synthetic tool identity, never executed")
        (self.root / "scripts/sign_release.py").write_text("# synthetic boundary")

        def host(root, tool, component=None, **options):
            return {"success": True, "finished": True, "compiled": component is not None,
                    "asyncDesktopStatus": "passed"}

        def run(arguments, **options):
            if "sign" in arguments:
                archive = self.root / "dist/example-component.zip"
                archive.with_suffix(".dmg").write_bytes(b"synthetic signed DMG")
                archive.with_name("example-component-signing.json").write_text("{}")
            return subprocess.CompletedProcess(arguments, 0, "synthetic tool4d identity\n", "")

        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "miyako/openid", "GITHUB_REF_NAME": "1/merge"}):
            with self.assertRaisesRegex(ValueError, "actual repository does not match"):
                ci_config.load_config(self.root, repository=os.environ["GITHUB_REPOSITORY"])
            with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/example-component"}), \
                    patch.object(accept_hosted, "require_tool4d_host"), \
                    patch.object(external_cli, "signature_check"), \
                    patch.object(accept_hosted, "compile_component", return_value=self.fixture.status), \
                    patch.object(accept_hosted, "test_4d", side_effect=host), \
                    patch.object(accept_hosted, "verify_signing_proof", return_value={}), \
                    patch.object(accept_hosted.subprocess, "run", side_effect=run), \
                    patch.object(build_provenance, "commit", return_value=None):
                report = accept_hosted.accept(self.root, "owner/example-component", tool)
            self.assertEqual(os.environ["GITHUB_REPOSITORY"], "miyako/openid")
            self.assertEqual(os.environ["GITHUB_REF_NAME"], "1/merge")
        self.assertTrue(report["finished"])
        self.assertEqual(report["steps"]["signing"]["status"], "passed")
        for target in ci_config.TARGETS:
            step = report["steps"]["cli_test_" + target]
            self.assertEqual(step["status"], "passed")
            self.assertEqual(step["details"]["external"]["verification"], external_cli.verification_evidence(target))

    def test_release_verifier_rejects_missing_or_misrepresented_native_tiers(self):
        with patch.object(external_cli, "signature_check"):
            archive = self.fixture.package()
        revision = "a" * 40
        contract = self.root / "tests/host/contract.json"
        contract.parent.mkdir(parents=True)
        contract.write_text(json.dumps(test_host_runner.CONTRACT))
        source, compiled = test_host_runner.valid_status(False), test_host_runner.valid_status(True)
        source["asyncDesktopStatus"] = compiled["asyncDesktopStatus"] = "passed"
        dmg = archive.with_suffix(".dmg")
        dmg.write_bytes(b"synthetic signed DMG")
        proof = {
            "schema": 1, "version": "0.1.0", "sourceSHA": revision, "releaseTag": "0.1.0",
            "unsignedCompileInputSHA256": self.fixture.status["input_sha256"],
            "unsignedZIPHashSHA256": "0" * 64, "hostValidation": "required-after-signing",
            "signedFiles": [{"path": "Libraries/lib4d-arm64.dylib", "verified": True}],
            "preservedExternalCLI": {"path": "Resources/bin/macOS/oidc-cli",
                                     "sha256": self.release["assets"]["macos"]["binary_sha256"],
                                     "resigned": False, "verified": True},
            "notarization": {"status": "Accepted", "submissionUUID": "12345678-1234-4321-8765-123456789abc"},
            "dmg": {"stapled": True, "validated": True, "sha256": external_cli.digest(dmg)},
            "zip": {"stapled": False, "notarizedViaDMG": True, "origin": "final-mounted-accepted-DMG",
                    "sha256": external_cli.digest(archive)}}
        signing = archive.with_name("example-component-signing.json")
        signing.write_text(json.dumps(proof))
        assets = [{"path": "dist/" + path.name, "sha256": external_cli.digest(path),
                   "bytes": path.stat().st_size} for path in (archive, dmg, signing)]
        steps = {
            "assembly": {"status": "passed"}, "package": {"status": "passed"},
            "compile": {"status": "passed", "details": self.fixture.status},
            "source_host": {"status": "passed", "details": source},
            "compiled_host": {"status": "passed", "details": compiled},
            "unsigned_compiled_host": {"status": "passed", "details": compiled},
            "signing": {"status": "passed"}, "signing_proof": {"status": "passed", "details": proof}}
        for target in ci_config.TARGETS:
            manifest = json.loads(self.manifest(target).read_text())
            manifest["commit"] = revision
            steps["cli_test_" + target] = {"status": "passed", "details": manifest}
        report = {"schema": 1, "scope": "hosted", "commit": revision, "finished": True,
                  "result": "partial", "configuration": self.fixture.config,
                  "steps": steps, "assets": assets, "artifact": assets[0],
                  "unsigned_artifact": {"path": assets[0]["path"], "sha256": "0" * 64}}
        evidence = archive.with_suffix(".acceptance.json")

        def verify():
            evidence.write_text(json.dumps(report))
            with patch.object(release_assets, "commit", return_value=revision):
                return release_assets.verify_assets(
                    self.root, "owner/example-component", "0.1.0", revision, apple_signing=True)

        self.assertEqual(len(verify()), 4)
        original = copy.deepcopy(report)
        for target in ci_config.TARGETS:
            del report["steps"]["cli_test_" + target]
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "required acceptance step"):
                verify()
            report = copy.deepcopy(original)
            verification = report["steps"]["cli_test_" + target]["details"]["external"]["verification"]
            verification["online_notarization"] = "passed" if target != "macos-arm64" else "not_run"
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "release provenance"):
                verify()
            report = copy.deepcopy(original)


if __name__ == "__main__":
    unittest.main()
