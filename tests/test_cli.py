"""External native protocol checks; no upstream compiler or source checkout."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import external_cli


class ExternalNativeTests(unittest.TestCase):
    def test_external_only_no_source_build(self):
        config = json.loads((ROOT / "template.json").read_text())
        self.assertEqual(config["cli_source"], external_cli.PROFILE)
        self.assertFalse(any((ROOT / "cli").rglob("*.*")))

    def test_native_version_if_explicitly_requested(self):
        target = os.environ.get("CLI_TARGET")
        if not target:
            self.skipTest("native acquisition is performed by CI after static tests")
        # This checks eligibility before downloading or executing anything.
        release = external_cli.load_pin(ROOT)
        self.assertNotEqual(release["version"], external_cli.DEV_VERSION)


if __name__ == "__main__":
    unittest.main()
