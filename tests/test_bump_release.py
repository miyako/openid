"""Wrapper release SemVer must never rewrite the external dependency pin."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bump_release


class BumpReleaseTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix=".external-bump-", dir=ROOT)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        for directory in ("component", "scripts"):
            shutil.copytree(ROOT / directory, self.root / directory,
                            ignore=shutil.ignore_patterns("DerivedData", "bin", "__pycache__", "Libraries"))
        for file in ("template.json", "package.json", "workflow-contract.json", "release-policy.json"):
            shutil.copy2(ROOT / file, self.root / file)
        for args in (("init", "-q"), ("remote", "add", "origin", "https://github.com/miyako/openid.git")):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        bump_release.apply(self.root, "0.1.0", "miyako/openid")

    def test_component_only_bump_and_retry(self):
        pin = (self.root / "scripts/oidc-cli-pin.json").read_bytes()
        policy = (self.root / "release-policy.json").read_bytes()
        result = bump_release.apply(self.root, "0.2.0", "miyako/openid")
        self.assertEqual(set(result["changed_paths"]), {"template.json", "package.json"})
        self.assertEqual((self.root / "scripts/oidc-cli-pin.json").read_bytes(), pin)
        self.assertEqual((self.root / "release-policy.json").read_bytes(), policy)
        self.assertEqual(bump_release.apply(self.root, "0.2.0", "miyako/openid")["changed_paths"], [])

    def test_highest_stable_history_and_modes(self):
        tags = ["v1.2.3", "2.0.0", "v2.1.0", "9.0.0-rc.1", "99R1.1", "unrelated"]
        for mode, expected in (("patch", "2.1.1"), ("minor", "2.2.0"), ("major", "3.0.0")):
            with self.subTest(mode=mode):
                result = bump_release.next_version(self.root, mode, "miyako/openid", tags=tags)
                self.assertEqual(result["version"], expected)

    def test_no_stable_tag_bumps_configured_version(self):
        for configured, expected in (("0.1.0", "0.1.1"), ("0.1.1", "0.1.2"),
                                     ("1.2.9", "1.2.10")):
            with self.subTest(configured=configured):
                bump_release.apply(self.root, configured, "miyako/openid")
                self.assertEqual(bump_release.next_version(self.root, "patch", "miyako/openid",
                                                         tags=[])["version"], expected)

    def test_invalid_component_versions_and_identity_fail_without_mutation(self):
        before = (self.root / "template.json").read_bytes()
        for version in ("v0.2.0", "0.2.0-rc.1", "20R3.2"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                bump_release.apply(self.root, version, "miyako/openid")
        with self.assertRaises(ValueError):
            bump_release.apply(self.root, "0.2.0", "other/openid")
        self.assertEqual((self.root / "template.json").read_bytes(), before)

    def test_dependency_cannot_be_bump_surface(self):
        path = self.root / "workflow-contract.json"
        value = json.loads(path.read_text())
        value["version_surfaces"] = [{"kind": "json-pointer",
                                     "path": "scripts/oidc-cli-pin.json", "pointer": "/version"}]
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "dependency/tooling"):
            bump_release.apply(self.root, "0.2.0", "miyako/openid")
