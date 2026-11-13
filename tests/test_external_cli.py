"""Fail-closed external release acquisition and immutable signed-byte boundaries."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import external_cli as cli
import build_provenance
import sign_release
import package_component
import release_assets


class ExternalTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix=".external-cli-test-", dir=ROOT)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        (self.root / "scripts/licenses").mkdir(parents=True)
        self.release = {
            "version": "9.0.0", "tag": "v9.0.0", "receipt_sha256": "a" * 64,
            "apple_team_id": "ABCDEFGHIJ",
            "verification_policy": dict(cli.VERIFICATION_POLICIES),
            "assets": {
                "macos": {"name": "oidc-cli_9.0.0_darwin_universal.tar.gz",
                          "sha256": "b" * 64, "binary_sha256": "c" * 64},
                "windows-x64": {"name": "oidc-cli_9.0.0_windows_amd64.zip",
                                "sha256": "d" * 64, "binary_sha256": "e" * 64}},
            "licenses": [],
        }
        for kind, name in (("upstream", "upstream"), ("dependencies", "dependencies"),
                           ("runtime", "runtime"), ("upstream", "release-grant")):
            path = self.root / ("scripts/licenses/" + name + ".txt")
            path.write_text("Synthetic license fixture, not redistribution evidence\n")
            self.release["licenses"].append({
                "kind": kind, "path": str(path.relative_to(self.root)), "sha256": cli.digest(path)})
        self.pin = {"schema": 1, "profile": cli.PROFILE, "repository": cli.REPOSITORY,
                    "status": "reviewed", "release": self.release}
        self.write_pin()
        self.binary = self.root / "binary"
        self.binary.write_bytes(b"synthetic signed binary")

    def write_pin(self):
        (self.root / "scripts/oidc-cli-pin.json").write_text(json.dumps(self.pin))

    def archive(self, names=("oidc-cli",), kind=tarfile.REGTYPE, mode=0o755):
        archive = self.root / "archive.tar.gz"
        with tarfile.open(archive, "w:gz", format=tarfile.USTAR_FORMAT) as packed:
            for name in names:
                entry = tarfile.TarInfo(name)
                entry.type, entry.mode = kind, mode
                entry.size = 3 if kind == tarfile.REGTYPE else 0
                packed.addfile(entry, io.BytesIO(b"abc") if entry.size else None)
        return archive

    def test_unresolved_production_pin_never_downloads_or_executes(self):
        self.pin["status"] = "unresolved"
        self.write_pin()
        with patch.object(cli, "fetch") as fetch, patch.object(cli.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "unresolved"):
                cli.acquire(self.root, "macos-arm64")
            fetch.assert_not_called()
            run.assert_not_called()

    def test_development_checksum_list_verifies_every_approved_file(self):
        expected = {}
        for index, name in enumerate(cli.DEV_DIGESTS):
            path = self.root / name
            path.write_bytes(("fixture-" + str(index)).encode())
            expected[name] = cli.digest(path)
        manifest = self.root / "SHA256SUMS"
        original = "".join(checksum + "  " + name + "\n" for name, checksum in expected.items())
        manifest.write_text(original)
        with patch.object(cli, "DEV_DIGESTS", expected):
            self.assertEqual(cli.dev_checksums(self.root), expected)
            for text in (
                    original + original.splitlines()[0] + "\n",
                    original.replace(next(iter(expected)), "../oidc-cli"),
                    "\n".join(original.splitlines()[:-1]) + "\n",
                    original + "0" * 64 + "  extra.zip\n",
                    original.replace(next(iter(expected.values())), "0" * 64, 1)):
                manifest.write_text(text)
                with self.subTest(text=text[:80]), self.assertRaises(ValueError):
                    cli.dev_checksums(self.root)
            manifest.write_text(original)
            # A nonexecuted foreign archive is still mandatory and verified.
            windows = next(name for name in expected if name.endswith(".zip"))
            (self.root / windows).write_bytes(b"tampered Windows archive")
            with self.assertRaisesRegex(ValueError, "artifact SHA256 mismatch"):
                cli.dev_checksums(self.root)

    def test_reviewed_exact_pin_and_license_hashes(self):
        self.assertEqual(cli.load_pin(self.root), self.release)
        (self.root / self.release["licenses"][0]["path"]).write_text("changed")
        with self.assertRaisesRegex(ValueError, "license digest"):
            cli.load_pin(self.root)

    def test_reviewed_policy_is_fixed_per_native_target_and_universal_pin_unchanged(self):
        release = cli.load_pin(ROOT)
        self.assertEqual(release["verification_policy"], cli.VERIFICATION_POLICIES)
        self.assertEqual(release["assets"]["macos"], {
            "name": "oidc-cli_0.2.0_darwin_universal.tar.gz",
            "sha256": "513c4f27378933700465ef38bd870a87833c8eb5ad2416cbc6345b25cdce362c",
            "binary_sha256": "3feaf489dcf377b0afd2968d326ade088a8578a82c1811acfa13ce082747b8fb"})
        self.assertEqual(release["receipt_sha256"],
                         "3b364cf4a4a1571b2d5b3fffa75259e72c68b8503c16a311fc1868e1a140f63f")
        self.assertEqual(release["licensing_commit"], "e687010b6ea3c51c6d3cf247d78f78826e188d17")
        self.assertEqual(len(release["licenses"]), 6)
        for policy in (None, {}, {"macos-arm64": cli.VERIFICATION_POLICIES["macos-x64"]},
                       {**cli.VERIFICATION_POLICIES, "macos-arm64": cli.VERIFICATION_POLICIES["macos-x64"]},
                       {**cli.VERIFICATION_POLICIES, "macos-x64": "fallback-if-online-fails"}):
            self.release["verification_policy"] = policy
            self.write_pin()
            with self.subTest(policy=policy), self.assertRaisesRegex(ValueError, "per-native-target"):
                cli.load_pin(self.root)

    def test_signed_asset_metadata_does_not_replace_redistribution_permission(self):
        self.release["licenses"] = []
        self.write_pin()
        with self.assertRaisesRegex(ValueError, "redistribution licenses required"):
            cli.load_pin(self.root)

    def test_every_notice_kind_and_separate_release_grant_are_checked(self):
        notices = self.release["licenses"]
        for kind in ("upstream", "dependencies", "runtime"):
            self.release["licenses"] = [notice for notice in notices if notice["kind"] != kind]
            self.write_pin()
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "redistribution licenses required"):
                cli.load_pin(self.root)
        self.release["licenses"] = notices
        self.write_pin()
        self.assertEqual(cli.load_pin(self.root), self.release)
        (self.root / notices[-1]["path"]).write_text("changed release grant")
        with self.assertRaisesRegex(ValueError, "license digest"):
            cli.load_pin(self.root)

    def test_bad_repo_latest_tag_unsigned_versions_and_development_pin_rejected(self):
        cases = [
            ("repository", "evil/oidc-cli"), ("status", "unresolved")]
        for key, value in cases:
            before = self.pin[key]
            self.pin[key] = value
            self.write_pin()
            with self.subTest(key=key), self.assertRaises(ValueError):
                cli.load_pin(self.root)
            self.pin[key] = before
        for version in ("0.1.0", "0.1.0-rc.2", cli.DEV_VERSION, "latest"):
            self.release.update(version=version, tag="v" + version)
            self.write_pin()
            with self.subTest(version=version), self.assertRaises(ValueError):
                cli.load_pin(self.root)

    def test_archive_and_receipt_pins_mandatory(self):
        for item, key in ((self.release, "receipt_sha256"), (self.release["assets"]["macos"], "sha256")):
            before = item[key]
            for value in (None, "", "A" * 64):
                item[key] = value
                self.write_pin()
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    cli.load_pin(self.root)
            item[key] = before

    def test_tar_preserves_exact_bytes_and_executable_mode(self):
        archive = self.archive()
        output = cli.extract(archive, self.root / "out/oidc-cli", cli.digest(archive))
        self.assertEqual(output.read_bytes(), b"abc")
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o755)

    def test_archive_hash_checked_before_extraction(self):
        archive = self.archive()
        output = self.root / "out/oidc-cli"
        with self.assertRaisesRegex(ValueError, "SHA256"):
            cli.extract(archive, output, "0" * 64)
        self.assertFalse(output.exists())

    def test_tar_traversal_extra_duplicate_link_directory_and_mode_rejected(self):
        for names, kind, mode in (
                (("../oidc-cli",), tarfile.REGTYPE, 0o755),
                (("/oidc-cli",), tarfile.REGTYPE, 0o755),
                (("oidc-cli", "extra"), tarfile.REGTYPE, 0o755),
                (("oidc-cli", "oidc-cli"), tarfile.REGTYPE, 0o755),
                (("oidc-cli",), tarfile.SYMTYPE, 0o755),
                (("oidc-cli",), tarfile.LNKTYPE, 0o755),
                (("oidc-cli",), tarfile.DIRTYPE, 0o755),
                (("oidc-cli",), tarfile.REGTYPE, 0o4755)):
            archive = self.archive(names, kind, mode)
            with self.subTest(names=names, kind=kind), self.assertRaises(ValueError):
                cli.extract(archive, self.root / "out/oidc-cli", cli.digest(archive))

    def test_windows_only_exact_regular_root_member(self):
        archive = self.root / "archive.zip"
        for name, mode in (("../oidc-cli.exe", stat.S_IFREG),
                           ("oidc-cli.exe", stat.S_IFLNK)):
            with zipfile.ZipFile(archive, "w") as packed:
                info = zipfile.ZipInfo(name)
                info.external_attr = (mode | 0o755) << 16
                packed.writestr(info, b"abc")
            with self.subTest(name=name), self.assertRaises(ValueError):
                cli.extract(archive, self.root / "out/oidc-cli.exe", cli.digest(archive))
        with zipfile.ZipFile(archive, "w") as packed:
            packed.writestr("oidc-cli.exe", b"abc")
        self.assertEqual(cli.extract(archive, self.root / "out/oidc-cli.exe",
                                     cli.digest(archive)).read_bytes(), b"abc")

    def test_symlink_output_rejected(self):
        archive = self.archive()
        (self.root / "link").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            cli.extract(archive, self.root / "link/out", cli.digest(archive))

    def test_receipt_requires_accepted_submission_and_exact_binary_hash(self):
        path = self.root / "receipt.json"
        value = {"schema": 1, "status": "Accepted",
                 "submission_id": "cc4ee0a2-d27c-4a54-8d76-563d12d97079",
                 "binaries": {"darwin_universal": cli.digest(self.binary)}}
        path.write_text(json.dumps(value))
        cli.receipt_check(path, self.binary, cli.digest(path))
        for key, changed in (("status", "Invalid"), ("submission_id", "not-a-uuid"),
                             ("binaries", {"darwin_universal": "f" * 64})):
            bad = dict(value, **{key: changed})
            path.write_text(json.dumps(bad))
            with self.subTest(key=key), self.assertRaises(ValueError):
                cli.receipt_check(path, self.binary, cli.digest(path))
        with self.assertRaises(ValueError):
            cli.receipt_check(path, self.binary, "0" * 64)

    def test_native_version_protocol_and_status_are_not_component_semver(self):
        good = {"protocol_version": 1, "ok": True, "version": "9.0.0"}
        for value, code, stderr in ((good, 0, b""), (dict(good, ok=False), 0, b""),
                                     (dict(good, protocol_version=True), 0, b""),
                                     (dict(good, version="0.1.0"), 0, b""),
                                     (good, 1, b""), (good, 0, b"unexpected")):
            with patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess(
                    [], code, json.dumps(value).encode(), stderr)):
                if value is good and code == 0 and not stderr:
                    cli.version_check(self.binary, "9.0.0")
                else:
                    with self.assertRaises(ValueError):
                        cli.version_check(self.binary, "9.0.0")
        with patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 0, b'{"ok":false,"ok":true,"protocol_version":1,"version":"9.0.0"}', b"")):
            with self.assertRaises(ValueError):
                cli.version_check(self.binary, "9.0.0")

    def test_signature_requires_online_notarization_and_both_hardened_slices(self):
        display = ("Authority=Developer ID Application: Example\nTeamIdentifier=ABCDEFGHIJ\n"
                   "Timestamp=Nov 11, 2026\nCodeDirectory v=20500 flags=0x10000(runtime)\n")
        def result(args, **kwargs):
            return subprocess.CompletedProcess(args, 0, "", display)
        with patch.object(cli.platform, "system", return_value="Darwin"), \
                patch.object(cli.subprocess, "run", side_effect=result) as run:
            cli.signature_check(self.binary, "ABCDEFGHIJ")
            self.assertIn("--check-notarization", run.call_args_list[0].args[0])
            self.assertIn("=notarized", run.call_args_list[0].args[0])
            self.assertFalse(run.call_args_list[0].kwargs["capture_output"])
            self.assertEqual(sum("--display" in call.args[0] for call in run.call_args_list), 2)
        for missing in ("Authority=Developer ID Application: Example\n", "Timestamp=Nov 11, 2026\n",
                        "CodeDirectory v=20500 flags=0x10000(runtime)\n"):
            with patch.object(cli.platform, "system", return_value="Darwin"), \
                    patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess(
                        [], 0, "", display.replace(missing, ""))):
                with self.assertRaises(ValueError):
                    cli.signature_check(self.binary, "ABCDEFGHIJ")
        with patch.object(cli.platform, "system", return_value="Darwin"), \
                patch.object(cli.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["codesign"])):
            with self.assertRaises(subprocess.CalledProcessError):
                cli.signature_check(self.binary)

    def test_binary_tampering_is_rejected_without_resigning(self):
        with self.assertRaisesRegex(ValueError, "signed upstream bytes"):
            cli.verify_binary(self.root, self.binary, "macos-arm64")

    def signature_result(self, args, **kwargs):
        if args[0] == "sysctl":
            return subprocess.CompletedProcess(args, 0, "0\n", "")
        display = ("Authority=Developer ID Application: Example\nTeamIdentifier=ABCDEFGHIJ\n"
                   "Timestamp=Nov 11, 2026\nCodeDirectory v=20500 flags=0x10000(runtime)\n")
        return subprocess.CompletedProcess(args, 0, "", display)

    def test_production_policy_uses_actual_native_architecture_not_cli_target_environment(self):
        for machine, target, opposite in (("x86_64", "macos-x64", "macos-arm64"),
                                          ("arm64", "macos-arm64", "macos-x64")):
            with self.subTest(machine=machine), \
                    patch.object(cli.platform, "system", return_value="Darwin"), \
                    patch.object(cli.platform, "machine", return_value=machine), \
                    patch.dict(os.environ, {"CLI_TARGET": opposite}), \
                    patch.object(cli.subprocess, "run", side_effect=self.signature_result) as run:
                evidence = cli.signature_check(self.binary, "ABCDEFGHIJ", production=True)
                expected = cli.verification_evidence(target)
                del expected["accepted_receipt"]
                self.assertEqual(evidence, expected)
                verification = next(call.args[0] for call in run.call_args_list if "--verify" in call.args[0])
                self.assertIn("--strict", verification)
                self.assertIn("--all-architectures", verification)
                online = target == "macos-arm64"
                for flag in ("--check-notarization", "--test-requirement", "=notarized"):
                    self.assertEqual(flag in verification, online)
                self.assertEqual(evidence["online_notarization"], "passed" if online else "not_run")
                displays = [call.args[0] for call in run.call_args_list if "--display" in call.args[0]]
                self.assertEqual([args[args.index("--arch") + 1] for args in displays], ["x86_64", "arm64"])

    def test_production_rejects_rosetta_unknown_hosts_and_never_uses_failure_fallback(self):
        for machine in ("arm64", "x86_64"):
            def failure(args, **kwargs):
                if "--verify" in args:
                    raise subprocess.CalledProcessError(3, args)
                return self.signature_result(args, **kwargs)
            with self.subTest(machine=machine), \
                    patch.object(cli.platform, "system", return_value="Darwin"), \
                    patch.object(cli.platform, "machine", return_value=machine), \
                    patch.object(cli.subprocess, "run", side_effect=failure) as run, \
                    patch.object(cli.time, "sleep") as sleep:
                with self.assertRaises(subprocess.CalledProcessError):
                    cli.signature_check(self.binary, "ABCDEFGHIJ", production=True)
                attempts = [call.args[0] for call in run.call_args_list if "--verify" in call.args[0]]
                self.assertEqual(len(attempts), 4 if machine == "arm64" else 1)
                self.assertEqual(sleep.call_count, 3 if machine == "arm64" else 0)
                for args in attempts:
                    self.assertEqual("--check-notarization" in args, machine == "arm64")
            with patch.object(cli.platform, "system", return_value="Darwin"), \
                    patch.object(cli.platform, "machine", return_value=machine), \
                    patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess(
                        [], 0, "1\n", "")) as run:
                with self.assertRaisesRegex(ValueError, "Rosetta"):
                    cli.signature_check(self.binary, "ABCDEFGHIJ", production=True)
                self.assertFalse(any("--verify" in call.args[0] for call in run.call_args_list))
        with patch.object(cli.platform, "system", return_value="Darwin"), \
                patch.object(cli.platform, "machine", return_value="unknown"), \
                patch.object(cli.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "unsupported native"):
                cli.signature_check(self.binary, "ABCDEFGHIJ", production=True)
            run.assert_not_called()

    def test_intel_policy_still_checks_every_slice_signing_property(self):
        for arch in ("x86_64", "arm64"):
            for missing in ("Authority=Developer ID Application: Example\n",
                            "TeamIdentifier=ABCDEFGHIJ\n", "Timestamp=Nov 11, 2026\n",
                            "CodeDirectory v=20500 flags=0x10000(runtime)\n"):
                def result(args, **kwargs):
                    value = self.signature_result(args, **kwargs)
                    if "--display" in args and args[args.index("--arch") + 1] == arch:
                        value.stderr = value.stderr.replace(missing, "")
                    return value
                with self.subTest(arch=arch, missing=missing), \
                        patch.object(cli.platform, "system", return_value="Darwin"), \
                        patch.object(cli.platform, "machine", return_value="x86_64"), \
                        patch.object(cli.subprocess, "run", side_effect=result):
                    with self.assertRaisesRegex(ValueError, "Developer ID"):
                        cli.signature_check(self.binary, "ABCDEFGHIJ", production=True)

    def test_acquisition_records_exact_policy_evidence_and_never_skips_receipt(self):
        import build_cli
        archive = self.archive()
        receipt = self.root / "APPLE_NOTARIZATION.json"
        receipt.write_text(json.dumps({
            "schema": 1, "status": "Accepted",
            "submission_id": "cc4ee0a2-d27c-4a54-8d76-563d12d97079",
            "binaries": {"darwin_universal": hashlib.sha256(b"abc").hexdigest()}}))
        self.release["receipt_sha256"] = cli.digest(receipt)
        for target in ("macos-x64", "macos-arm64", "windows-x64"):
            key = "windows-x64" if target == "windows-x64" else "macos"
            packed = archive
            if target == "windows-x64":
                packed = self.root / "archive.zip"
                with zipfile.ZipFile(packed, "w") as zipped:
                    zipped.writestr("oidc-cli.exe", b"abc")
            asset = self.release["assets"][key]
            asset.update(sha256=cli.digest(packed), binary_sha256=hashlib.sha256(b"abc").hexdigest())
            self.write_pin()
            def fetch(url, output):
                cli.destination(output)
                shutil.copy2(receipt if url.endswith("APPLE_NOTARIZATION.json") else packed, output)
            expected = cli.verification_evidence(target)
            with self.subTest(target=target), \
                    patch.object(build_cli, "native_target", return_value=target), \
                    patch.object(cli, "fetch", side_effect=fetch), \
                    patch.object(cli, "signature_check", return_value=expected) as signature, \
                    patch.object(cli, "receipt_check", wraps=cli.receipt_check) as check_receipt, \
                    patch.object(cli, "version_check"), \
                    patch.object(build_provenance, "record", return_value={}):
                binary = cli.acquire(self.root, target)
                manifest = json.loads(binary.with_name("build-manifest.json").read_text())
                self.assertEqual(manifest["external"], cli.release_provenance(self.release, target))
                self.assertEqual(binary.read_bytes(), b"abc")
                self.assertEqual(stat.S_IMODE(binary.stat().st_mode), 0o755)
                if target.startswith("macos-"):
                    signature.assert_called_once_with(binary, self.release["apple_team_id"], production=True)
                    check_receipt.assert_called_once()
                    receipt.write_text(receipt.read_text().replace("Accepted", "Rejected"))
                    self.release["receipt_sha256"] = cli.digest(receipt)
                    self.write_pin()
                    with self.assertRaisesRegex(ValueError, "accepted binary"):
                        cli.acquire(self.root, target)
                    self.assertFalse(binary.exists())
                    self.assertFalse(binary.with_name("build-manifest.json").exists())
                    receipt.write_text(receipt.read_text().replace("Rejected", "Accepted"))
                    self.release["receipt_sha256"] = cli.digest(receipt)
                else:
                    signature.assert_not_called()
                    check_receipt.assert_not_called()

    def test_notarization_requirement_retry_is_bounded_and_fail_closed(self):
        display = ("Authority=Developer ID Application: Example\nTeamIdentifier=ABCDEFGHIJ\n"
                   "Timestamp=Nov 11, 2026\nCodeDirectory v=20500 flags=0x10000(runtime)\n")
        requirement_failure = subprocess.CalledProcessError(3, ["codesign"])
        passed = subprocess.CompletedProcess([], 0, "", display)
        with patch.object(cli.platform, "system", return_value="Darwin"), \
                patch.object(cli.time, "sleep") as sleep, \
                patch.object(cli.subprocess, "run", side_effect=[requirement_failure, *([passed] * 4)]) as run:
            cli.signature_check(self.binary, "ABCDEFGHIJ")
            sleep.assert_called_once_with(15)
            self.assertEqual(sum("--check-notarization" in call.args[0]
                                 for call in run.call_args_list), 2)
        with patch.object(cli.platform, "system", return_value="Darwin"), \
                patch.object(cli.time, "sleep") as sleep, \
                patch.object(cli.subprocess, "run", side_effect=requirement_failure) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                cli.signature_check(self.binary, "ABCDEFGHIJ")
            self.assertEqual(run.call_count, 4)
            self.assertEqual(sleep.call_count, 3)
            self.assertTrue(all(call.args == (15,) for call in sleep.call_args_list))
        with patch.object(cli.platform, "system", return_value="Darwin"), \
                patch.object(cli.time, "sleep") as sleep, \
                patch.object(cli.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["codesign"])) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                cli.signature_check(self.binary, "ABCDEFGHIJ")
            self.assertEqual(run.call_count, 1)
            sleep.assert_not_called()

    def test_publication_checks_embedded_bytes_and_mode_not_only_evidence(self):
        prefix = "openid.4dbase/Resources/"
        entries = [(prefix + "bin/macOS/oidc-cli", b"mac", 0o755),
                   (prefix + "bin/Windows/oidc-cli.exe", b"win", 0o755)]
        for key, data in (("macos", b"mac"), ("windows-x64", b"win")):
            self.release["assets"][key]["binary_sha256"] = hashlib.sha256(data).hexdigest()
        for notice in self.release["licenses"]:
            entries.append((prefix + "licenses/" + Path(notice["path"]).name,
                            (self.root / notice["path"]).read_bytes(), 0o644))
        self.write_pin()
        archive = self.root / "openid.zip"
        def pack(items):
            with zipfile.ZipFile(archive, "w") as packed:
                for name, data, mode in items:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = (stat.S_IFREG | mode) << 16
                    packed.writestr(info, data)
        pack(entries)
        cli.verify_bundle(self.root, archive, "openid")
        for data, mode in ((b"resigned", 0o755), (b"mac", 0o644)):
            pack([(entries[0][0], data, mode), *entries[1:]])
            with self.subTest(data=data, mode=mode), self.assertRaises(ValueError):
                cli.verify_bundle(self.root, archive, "openid")
        for notice in entries[2:]:
            pack([entry for entry in entries if entry[0] != notice[0]])
            with self.subTest(missing=notice[0]), self.assertRaisesRegex(ValueError, "license missing"):
                cli.verify_bundle(self.root, archive, "openid")
            pack([(name, b"changed" if name == notice[0] else data, mode)
                  for name, data, mode in entries])
            with self.subTest(changed=notice[0]), self.assertRaises(ValueError):
                cli.verify_bundle(self.root, archive, "openid")

    def test_outer_signer_never_includes_external_cli(self):
        config = {"cli": "oidc-cli", "cli_source": cli.PROFILE}
        libraries = self.root / "Libraries"
        libraries.mkdir()
        library = libraries / "lib4d-arm64.dylib"
        library.write_bytes(b"synthetic library")
        with patch.object(cli, "verify_binary") as verify, \
                patch.object(sign_release, "macho_architectures", return_value=["arm64"]):
            signed = sign_release.signing_inputs(self.root, self.root, config)
            self.assertEqual(signed, [library])
            verify.assert_called_once_with(self.root, self.root / "Resources/bin/macOS/oidc-cli", "macos-arm64")
        with patch.object(cli, "verify_binary", side_effect=ValueError("signature rejected")):
            with self.assertRaisesRegex(ValueError, "signature rejected"):
                sign_release.signing_inputs(self.root, self.root, config)

    def test_external_signing_policy_cannot_be_disabled_by_empty_or_missing_policy(self):
        config = {"cli_source": cli.PROFILE, "version": "9.0.0"}
        policy = self.root / "release-policy.json"
        with patch.object(sign_release, "load_config", return_value=config):
            self.assertTrue(sign_release.release_policy(self.root))
            for versions in ([], ["8.0.0"]):
                policy.write_text(json.dumps({"schema": 1, "apple_notarized_versions": versions}))
                self.assertTrue(sign_release.release_policy(self.root))
            policy.write_text('{"schema":true,"apple_notarized_versions":[]}')
            with self.assertRaises(ValueError):
                sign_release.release_policy(self.root)

    def test_desktop_release_evidence_requires_literal_passed(self):
        self.assertEqual(release_assets.require_desktop_evidence({"asyncDesktopStatus": "passed"}),
                         {"asyncDesktopStatus": "passed"})
        for value in (None, {}, {"asyncDesktopStatus": "not_run"},
                      {"asyncDesktopStatus": True}, {"asyncDesktopStatus": "failed"}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "headless acceptance is partial"):
                release_assets.require_desktop_evidence(value)

    def test_explicit_development_package_is_source_stripped_nonrelease_and_macos_only(self):
        import test_delivery
        fixture = test_delivery.DeliveryTests("test_matrix_only_selected_language")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.config.update(cli="oidc-cli", cli_source=cli.PROFILE)
        mac = fixture.mac.with_name("oidc-cli")
        fixture.mac.rename(mac)
        fixture.windows.rename(fixture.windows.with_name("oidc-cli.exe"))
        mac.chmod(0o755)
        fixture.write_config()
        fixture.write_status()
        archive = None
        for ref in ("feature/oidc-wrapper", "1/merge", "9.9.9"):
            with self.subTest(ref=ref), patch.dict(os.environ, {"GITHUB_REF_NAME": ref}), \
                    patch.object(cli, "dev_verify", return_value=mac), \
                    patch.object(cli, "signature_check") as signature:
                archive = package_component.package(
                    fixture.root, repository="owner/example-component", development=True)
                signature.assert_called_once_with(mac)
        with patch.dict(os.environ, {"GITHUB_REF_NAME": "feature/oidc-wrapper"}), \
                patch.object(cli, "dev_verify", return_value=mac), \
                patch.object(cli, "signature_check"):
            with self.assertRaisesRegex(ValueError, "development component tag"):
                package_component.package(
                    fixture.root, repository="owner/example-component", tag="9.9.9", development=True)
            package_component.package(
                fixture.root, repository="owner/example-component",
                tag=fixture.config["version"], development=True)
        self.assertIsNotNone(archive)
        self.assertEqual(archive.parent, fixture.root / "build/development")
        self.assertFalse((fixture.root / "dist/example-component.zip").exists())
        with zipfile.ZipFile(archive) as packed:
            prefix = "example-component.4dbase/"
            marker = json.loads(packed.read(prefix + "DEVELOPMENT_ONLY.json"))
            self.assertIs(marker["release_eligible"], False)
            self.assertEqual(marker["upstream_version"], cli.DEV_VERSION)
            self.assertFalse(any("/Windows/" in name for name in packed.namelist()))
            binary = packed.getinfo(prefix + "Resources/bin/macOS/oidc-cli")
            self.assertEqual(packed.read(binary), mac.read_bytes())
            self.assertEqual(stat.S_IMODE(binary.external_attr >> 16), 0o755)
            self.assertIn(prefix + "Resources/bin/macOS/", packed.namelist())
            with zipfile.ZipFile(io.BytesIO(packed.read(prefix + "example-component.4DZ"))) as project:
                self.assertFalse(any(name.endswith(".4dm") for name in project.namelist()))
                self.assertTrue(any("CompiledCode/" in name for name in project.namelist()))
        unpacked = package_component.unpack_for_test(fixture.root, archive)
        self.assertEqual((unpacked / "Resources/bin/macOS/oidc-cli").read_bytes(), mac.read_bytes())
        # Development does not relax the production path or compiler provenance.
        with self.assertRaises((ValueError, OSError)):
            package_component.package(fixture.root, repository="owner/example-component", tag="0.1.0")
        fixture.marker.unlink()
        with patch.object(cli, "dev_verify", return_value=mac), patch.object(cli, "signature_check"):
            with self.assertRaisesRegex(ValueError, "compile-status"):
                package_component.package(fixture.root, repository="owner/example-component", development=True)

    def test_development_manifest_cannot_pass_production_provenance(self):
        for name in ("external_cli.py", "build_cli.py", "build_provenance.py"):
            shutil.copy2(ROOT / "scripts" / name, self.root / "scripts" / name)
        (self.root / "template.json").write_text(json.dumps({"cli_source": cli.PROFILE}))
        (self.root / "package.json").write_text("{}")
        status = build_provenance.record(self.root, "macos-arm64", self.binary, True, cli.PROFILE)
        status["external"] = {"release_eligible": False}
        self.binary.with_name("build-manifest.json").write_text(json.dumps(status))
        with self.assertRaisesRegex(ValueError, "development artifacts"):
            build_provenance.verify(self.root, "macos-arm64", self.binary)

    def test_pin_changes_invalidate_provenance_source_digest(self):
        for name in ("external_cli.py", "build_cli.py", "build_provenance.py"):
            shutil.copy2(ROOT / "scripts" / name, self.root / "scripts" / name)
        (self.root / "template.json").write_text(json.dumps({"cli_source": cli.PROFILE}))
        (self.root / "package.json").write_text("{}")
        before = build_provenance.source_digest(self.root)
        self.release["assets"]["macos"]["sha256"] = "0" * 64
        self.write_pin()
        self.assertNotEqual(before, build_provenance.source_digest(self.root))
