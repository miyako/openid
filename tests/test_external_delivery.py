"""External two-platform delivery; synthetic fixtures never execute native tools."""
import copy
import base64
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import accept_hosted
import accept_local
import build_provenance
import ci_config
import doctor
import external_cli
import package_component
import release_assets
import sign_release
import test_delivery
import test_host_runner
import test_sign_release


def thin_arm64():
    return struct.pack("<IIIIIIII", 0xFEEDFACF, 0x0100000C, 0, 2, 0, 0, 0, 0)


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
        self.mac.write_bytes(thin_arm64())
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
        self.write_pin()
        for target in ci_config.targets(self.fixture.config):
            source = self.windows if target == "windows-x64" else self.mac
            binary = self.root / "build" / target / source.name
            binary.parent.mkdir()
            shutil.copy2(source, binary)
            self.manifest(target)
        self.notices = self.mac.parents[2] / "licenses"
        for notice in self.release["licenses"]:
            shutil.copy2(self.root / notice["path"], self.notices / Path(notice["path"]).name)
        self.fixture.write_status()

    def write_pin(self):
        (self.root / "scripts/oidc-cli-pin.json").write_text(json.dumps(self.pin))

    def binary(self, target):
        return self.root / "build" / target / ("oidc-cli.exe" if target == "windows-x64" else "oidc-cli")

    def manifest(self, target, tested=True):
        binary = self.binary(target)
        status = build_provenance.record(self.root, target, binary, tested, external_cli.PROFILE)
        asset = self.release["assets"]["windows-x64" if target == "windows-x64" else "macos"]
        status["external"] = {
            "repository": external_cli.REPOSITORY, "tag": self.release["tag"],
            "archive_sha256": asset["sha256"], "release_eligible": True}
        binary.with_name("build-manifest.json").write_text(json.dumps(status))
        return status

    def assemble(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(external_cli, "signature_check"):
            return ci_config.assemble(self.root)

    def package(self):
        with patch.object(external_cli, "signature_check"):
            return self.fixture.package()

    def test_external_matrix_is_two_native_targets_and_template_keeps_three(self):
        for config in (self.fixture.config, ci_config.load_config(ROOT)):
            entries = ci_config.matrix(config)["include"]
            self.assertEqual([entry["target"] for entry in entries], ["macos-arm64", "windows-x64"])
            self.assertEqual([entry["runner"] for entry in entries], ["macos-15", "windows-2022"])
            self.assertEqual({entry["language"] for entry in entries}, {"external"})
        self.assertEqual(ci_config.targets({"language": "go"}), ci_config.TARGETS)

    def test_two_target_assembly_ignores_stale_intel_and_never_creates_universal(self):
        intel = self.root / "build/macos-x64/oidc-cli"
        intel.parent.mkdir()
        intel.write_bytes(b"stale untrusted Intel input")
        intel.with_name("build-manifest.json").write_text('{"execution":"not_run"}')
        # Actions downloads strip modes, so assembly restores the exact reviewed mode.
        self.binary("macos-arm64").chmod(0o644)
        with patch.object(ci_config.subprocess, "run") as run:
            self.assemble()
            self.assertTrue(all(call.args[0][0] == "git" for call in run.call_args_list))
        self.assertEqual(self.mac.read_bytes(), thin_arm64())
        self.assertEqual(stat.S_IMODE(self.mac.stat().st_mode), 0o755)
        self.assertEqual(self.windows.read_bytes(), self.binary("windows-x64").read_bytes())
        for notice in self.release["licenses"]:
            self.assertEqual(external_cli.digest(self.notices / Path(notice["path"]).name), notice["sha256"])
        intel.unlink()
        intel.with_name("build-manifest.json").unlink()
        self.assemble()

    def test_assembly_rejects_missing_foreign_native_execution_and_mixed_provenance(self):
        for target in ci_config.targets(self.fixture.config):
            binary = self.binary(target)
            manifest = binary.with_name("build-manifest.json")
            original = json.loads(manifest.read_text())
            for field, value in (("execution", "not_run"), ("commit", "b" * 40),
                                 ("source_sha256", "0" * 64), ("binary_sha256", "0" * 64),
                                 ("toolchain", "go version synthetic")):
                manifest.write_text(json.dumps({**original, field: value}))
                with self.subTest(target=target, field=field), self.assertRaises(ValueError):
                    self.assemble()
            manifest.write_text(json.dumps(original))
            data = binary.read_bytes()
            binary.unlink()
            with self.assertRaisesRegex(ValueError, "all supported native"):
                self.assemble()
            binary.write_bytes(data)

    def test_unreviewed_bytes_notices_and_development_provenance_cannot_assemble(self):
        binary = self.binary("macos-arm64")
        original = binary.read_bytes()
        binary.write_bytes(b"replacement signed-looking bytes")
        self.manifest("macos-arm64")
        with self.assertRaisesRegex(ValueError, "reviewed signed upstream bytes"):
            self.assemble()
        binary.write_bytes(original)
        status = self.manifest("macos-arm64")
        status["external"]["release_eligible"] = False
        binary.with_name("build-manifest.json").write_text(json.dumps(status))
        with self.assertRaisesRegex(ValueError, "development artifacts"):
            self.assemble()
        self.manifest("macos-arm64")
        (self.root / self.release["licenses"][0]["path"]).write_text("modified upstream notice")
        with self.assertRaises(ValueError):
            self.assemble()

    def test_external_package_is_thin_arm64_with_both_compiler_targets(self):
        archive = self.package()
        with zipfile.ZipFile(archive) as packed:
            self.assertEqual(packed.read("example-component.4dbase/Resources/bin/macOS/oidc-cli"), thin_arm64())
        for data in (test_delivery.synthetic_universal(), thin_arm64()[:16],
                     thin_arm64().replace(b"\x0c\x00\x00\x01", b"\x07\x00\x00\x01"),
                     thin_arm64()[:8] + struct.pack("<I", 2) + thin_arm64()[12:]):
            self.mac.write_bytes(data)
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, "thin ARM64"):
                self.package()
        self.mac.write_bytes(thin_arm64())
        self.fixture.status["targets"] = ["arm64_macOS_lib"]
        self.fixture.write_status()
        with self.assertRaisesRegex(ValueError, "both required targets"):
            self.package()
        self.fixture.status["targets"] = ["x86_64_generic", "arm64_macOS_lib"]
        compiled = self.fixture.project.parent / "DerivedData/CompiledCode"
        next(compiled.glob("MX64 *")).unlink()
        self.fixture.write_status()
        with self.assertRaisesRegex(ValueError, "MX64"):
            self.package()

    def test_external_package_retains_windows_shape_bytes_and_all_notices(self):
        self.windows.write_bytes(b"not PE32+")
        with self.assertRaisesRegex(ValueError, "PE executable"):
            self.package()
        self.windows.write_bytes(test_delivery.synthetic_pe())
        for notice in self.release["licenses"]:
            path = self.notices / Path(notice["path"]).name
            data = path.read_bytes()
            path.write_bytes(b"changed")
            with self.subTest(notice=path.name), self.assertRaisesRegex(ValueError, "license missing or changed"):
                self.package()
            path.write_bytes(data)
        self.mac.write_bytes(thin_arm64() + b"resigned")
        with self.assertRaisesRegex(ValueError, "reviewed signed upstream bytes"):
            self.package()

    def test_hosted_evidence_only_requires_supported_native_manifests(self):
        tool = self.root / "tool4d"
        tool.write_bytes(b"synthetic tool identity, never executed")
        calls = []

        def host(root, tool, component=None, **options):
            calls.append((component is not None, options))
            return {"success": True, "finished": True, "compiled": component is not None,
                    "asyncDesktopStatus": "passed"}

        def run(arguments, **options):
            if "sign" in arguments:
                archive = self.root / "dist/example-component.zip"
                archive.with_suffix(".dmg").write_bytes(b"synthetic signed DMG")
                archive.with_name("example-component-signing.json").write_text("{}")
            return subprocess.CompletedProcess(arguments, 0, "synthetic tool4d identity\n", "")

        (self.root / "scripts/sign_release.py").write_text("# synthetic boundary")
        with patch.object(accept_hosted, "require_tool4d_host"), \
                patch.object(external_cli, "signature_check"), \
                patch.object(accept_hosted, "compile_component", return_value=self.fixture.status), \
                patch.object(accept_hosted, "test_4d", side_effect=host), \
                patch.object(accept_hosted, "verify_signing_proof", return_value={}), \
                patch.object(accept_hosted.subprocess, "run", side_effect=run), \
                patch.object(build_provenance, "commit", return_value=None):
            report = accept_hosted.accept(self.root, "owner/example-component", tool)
        self.assertTrue(report["finished"])
        self.assertNotIn("cli_test_macos-x64", report["steps"])
        self.assertEqual(report["steps"]["native_intel_4d"]["status"], "unsupported")
        self.assertIn("Intel macOS unsupported", report["reason"])
        for target in ("macos-arm64", "windows-x64"):
            self.assertEqual(report["steps"]["cli_test_" + target]["status"], "passed")
        self.assertEqual(report["steps"]["signing"]["status"], "passed")
        self.assertEqual(calls, [(False, {"require_desktop": True}),
                                 (True, {"require_desktop": True}), (True, {"require_desktop": True})])

    def test_local_external_cross_mode_rejected_before_native_build(self):
        with patch.object(accept_local, "build") as build:
            with self.assertRaisesRegex(ValueError, "native-only"):
                accept_local.accept(self.root, "owner/example-component", self.root / "tool4d", cross=True)
            build.assert_not_called()
        report = json.loads((self.root / "build/acceptance.json").read_text())
        self.assertEqual(report["steps"]["native_intel_4d"]["status"], "unsupported")
        self.assertNotIn("cli_build_macos-x64", report["steps"])
        self.assertNotIn("cli_rosetta", report["steps"])

    def test_doctor_does_not_claim_intel_is_a_supported_native_cli_host(self):
        with patch.object(doctor, "native_target", return_value="macos-x64"), \
                patch.object(doctor, "github_repository", return_value=None), \
                patch.object(doctor, "resolve_tool_pin", return_value=("https://example.test/tool", "a" * 64)):
            report = doctor.doctor(self.root)
        check = next(check for check in report["checks"] if check["name"] == "native_cli_host")
        self.assertEqual(check["status"], "not_run")
        self.assertIn("unsupported", check["reason"])
        self.assertFalse(report["ready_for_local_acceptance"])

    def test_release_evidence_passes_with_two_native_manifests_and_intel_unsupported(self):
        archive = self.package()
        revision = "a" * 40
        contract = self.root / "tests/host/contract.json"
        contract.parent.mkdir(parents=True)
        contract.write_text(json.dumps(test_host_runner.CONTRACT))
        dmg = archive.with_suffix(".dmg")
        dmg.write_bytes(b"synthetic notarized DMG")
        proof = {
            "schema": 1, "version": self.fixture.config["version"],
            "sourceSHA": revision, "releaseTag": self.fixture.config["version"],
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
        source = test_host_runner.valid_status(False)
        compiled = test_host_runner.valid_status(True)
        source["asyncDesktopStatus"] = compiled["asyncDesktopStatus"] = "passed"
        assets = [{"path": "dist/" + path.name, "sha256": external_cli.digest(path),
                   "bytes": path.stat().st_size} for path in (archive, dmg, signing)]
        steps = {
            "assembly": {"status": "passed"}, "package": {"status": "passed"},
            "compile": {"status": "passed", "details": self.fixture.status},
            "source_host": {"status": "passed", "details": source},
            "compiled_host": {"status": "passed", "details": compiled},
            "unsigned_compiled_host": {"status": "passed", "details": compiled},
            "signing": {"status": "passed"}, "signing_proof": {"status": "passed", "details": proof},
            "native_intel_4d": {"status": "unsupported", "reason": "Intel macOS unsupported"}}
        for target in ci_config.targets(self.fixture.config):
            status = self.manifest(target)
            status["commit"] = revision
            steps["cli_test_" + target] = {"status": "passed", "details": status}
        report = {"schema": 1, "scope": "hosted", "commit": revision, "finished": True,
                  "result": "partial", "configuration": self.fixture.config,
                  "steps": steps, "assets": assets, "artifact": assets[0],
                  "unsigned_artifact": {"path": assets[0]["path"], "sha256": "0" * 64}}
        evidence = archive.with_suffix(".acceptance.json")
        evidence.write_text(json.dumps(report))

        def verify():
            evidence.write_text(json.dumps(report))
            with patch.object(release_assets, "commit", return_value=revision):
                return release_assets.verify_assets(
                    self.root, "owner/example-component", "0.1.0", revision, apple_signing=True)

        self.assertEqual(len(verify()), 4)
        original = copy.deepcopy(report)
        for target in ("macos-arm64", "windows-x64"):
            del report["steps"]["cli_test_" + target]
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "required acceptance step"):
                verify()
            report = copy.deepcopy(original)
        for field, value in (("execution", "not_run"), ("commit", "b" * 40),
                             ("source_sha256", "0" * 64), ("binary_sha256", "0" * 64),
                             ("external", {"release_eligible": False})):
            report["steps"]["cli_test_windows-x64"]["details"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify()
            report = copy.deepcopy(original)
        report["steps"]["native_intel_4d"]["status"] = "not_run"
        with self.assertRaisesRegex(ValueError, "Intel macOS unsupported"):
            verify()
        report = copy.deepcopy(original)
        report["steps"]["cli_test_macos-x64"] = {"status": "passed"}
        with self.assertRaisesRegex(ValueError, "Intel macOS unsupported"):
            verify()

    def test_outer_signed_dmg_and_mounted_zip_preserve_thin_external_cli(self):
        shutil.copy2(ROOT / "workflow-contract.json", self.root / "workflow-contract.json")
        library = self.fixture.component / "Libraries/lib4d-arm64.dylib"
        library.write_bytes(thin_arm64())
        self.fixture.write_status()
        archive = self.package()
        env = {name: "synthetic-credential-" + name for name in sign_release.SECRET_NAMES}
        env.update(
            NOTARYTOOL_TEAM_ID=test_sign_release.TEAM,
            APPLE_DEVELOPER_ID_CERTIFICATE=base64.b64encode(b"synthetic not-a-real-p12").decode(),
            GITHUB_ACTIONS="true", GITHUB_REPOSITORY="owner/example-component",
            RELEASE_TAG="0.1.0", RELEASE_SHA="a" * 40)
        tools = test_sign_release.FakeTools(env, repository="example-component", cli="oidc-cli")
        with patch.object(sign_release.platform, "system", return_value="Darwin"), \
                patch.object(external_cli, "signature_check"), \
                patch.object(sign_release.subprocess, "run", side_effect=tools.run):
            proof = sign_release.sign_release(self.root, env)
        self.assertEqual(proof["preservedExternalCLI"], {
            "path": "Resources/bin/macOS/oidc-cli", "sha256": external_cli.digest(self.mac),
            "resigned": False, "verified": True})
        self.assertEqual(proof["signedFiles"], [{"path": "Libraries/lib4d-arm64.dylib", "verified": True}])
        self.assertEqual(proof["notarization"]["status"], "Accepted")
        self.assertTrue(proof["dmg"]["stapled"])
        self.assertTrue(proof["dmg"]["validated"])
        self.assertEqual(proof["zip"]["origin"], "final-mounted-accepted-DMG")
        with zipfile.ZipFile(archive) as packed:
            path = "example-component.4dbase/Resources/bin/macOS/oidc-cli"
            self.assertEqual(packed.read(path), thin_arm64())
            self.assertEqual(stat.S_IMODE(packed.getinfo(path).external_attr >> 16), 0o755)
        external_cli.verify_bundle(self.root, archive, "example-component")
        signed = [args[-1] for args in tools.calls if args[:2] == [sign_release.CODESIGN, "--force"]]
        self.assertFalse(any(Path(path).name == "oidc-cli" for path in signed))
        self.assertFalse(any("lipo" in args[0] for args in tools.calls))


if __name__ == "__main__":
    unittest.main()
