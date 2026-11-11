#!/usr/bin/env python3
"""Build-time-only acquisition adapter; never builds or re-signs upstream code."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tarfile
import time
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "external-oidc-cli-v1"
REPOSITORY = "miyako/oidc-cli"
VERIFICATION_POLICIES = {
    "macos-x64": "native-intel-accepted-receipt-v1",
    "macos-arm64": "native-arm64-online-notarized-v1",
    "windows-x64": "native-windows-integrity-v1",
}
DEV_VERSION = "0.0.0-signing-check"
DEV_SHA = "27dd05ce90c0ecf0487a99d0e030e9d3a89ef37d"
DEV_DIGESTS = {
    "oidc-cli_0.0.0-signing-check_darwin_universal.tar.gz":
        "072e723af266273c89e237f64dde4bce6560e83bfce488e8bfbf6099a418220a",
    "oidc-cli_0.0.0-signing-check_darwin_amd64.tar.gz":
        "ddf69a79d9088d700e5c220df70598d9e7139ab2fe00d69bceafe82f65bf16aa",
    "oidc-cli_0.0.0-signing-check_darwin_arm64.tar.gz":
        "120518e1c622bb4d0316d1b9e30d4458f183c4630e5ac9645473111262faa3d2",
    "oidc-cli_0.0.0-signing-check_windows_amd64.zip":
        "6bb4a0b3df85204b3887123f5e90dfd1ae28fd732fe70c2a1e41457f1c69e40c",
    "APPLE_NOTARIZATION.json":
        "cd6fbd1e078344da3b72a2fb5fc4cd5ecaec0e6a1b10bfd958f18bb265365007",
}


def dev_checksums(folder):
    """Validate all four approved archives and the receipt before any execution."""
    folder = Path(folder)
    entries = {}
    for line in regular(folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match[2] not in DEV_DIGESTS or match[2] in entries:
            raise ValueError("invalid, duplicate or unapproved development checksum entry")
        entries[match[2]] = match[1]
    if entries != DEV_DIGESTS:
        raise ValueError("development SHA256SUMS must match all exact approved archive/receipt pins")
    for name, checksum in entries.items():
        if digest(regular(folder / name)) != checksum:
            raise ValueError("development artifact SHA256 mismatch: " + name)
    return entries


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def regular(path):
    path = Path(path)
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("expected regular non-symlink file: " + str(path))
    return path


def destination(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("destination must not traverse symlinks")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def checked_hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("a reviewed lowercase SHA256 is required")
    return value


def json_object(text):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value
    value = json.loads(text, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def load_pin(root=ROOT):
    pin = json_object(regular(Path(root) / "scripts/oidc-cli-pin.json").read_text())
    if (type(pin.get("schema")) is not int or pin.get("schema") != 1 or pin.get("profile") != PROFILE
            or pin.get("repository") != REPOSITORY):
        raise ValueError("unsupported external CLI pin")
    release = pin.get("release")
    if pin.get("status") != "reviewed" or not isinstance(release, dict):
        raise ValueError("production oidc-cli pin unresolved; release and acquisition prohibited")
    version = release.get("version")
    if (not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version)
            or version in {"0.1.0", "0.1.0-rc.2", DEV_VERSION}
            or release.get("tag") != "v" + version):
        raise ValueError("exact reviewed future release tag/version required")
    checked_hash(release.get("receipt_sha256"))
    if not re.fullmatch(r"[A-Z0-9]{10}", release.get("apple_team_id", "")):
        raise ValueError("reviewed Developer ID team required")
    if release.get("verification_policy") != VERIFICATION_POLICIES:
        raise ValueError("exact reviewed per-native-target verification policy required")
    assets = release.get("assets", {})
    if not isinstance(assets, dict):
        raise ValueError("reviewed platform assets must be an object")
    for target, suffix in (("macos", "darwin_universal.tar.gz"), ("windows-x64", "windows_amd64.zip")):
        asset = assets.get(target, {})
        if not isinstance(asset, dict):
            raise ValueError("reviewed archive must be an object")
        if asset.get("name") != "oidc-cli_" + version + "_" + suffix:
            raise ValueError("exact universal macOS / Windows x64 archive required")
        checked_hash(asset.get("sha256"))
        checked_hash(asset.get("binary_sha256"))
    licenses = release.get("licenses")
    if (not isinstance(licenses, list) or not licenses
            or {notice.get("kind") for notice in licenses if isinstance(notice, dict)}
            != {"upstream", "dependencies", "runtime"}):
        raise ValueError("reviewed upstream and dependency redistribution licenses required")
    names = set()
    for notice in licenses:
        if not isinstance(notice, dict):
            raise ValueError("license record must be an object")
        path = notice.get("path", "")
        if not re.fullmatch(r"scripts/licenses/[A-Za-z0-9_.-]+", path):
            raise ValueError("unsafe license path")
        if Path(path).name in names:
            raise ValueError("duplicate license basename")
        names.add(Path(path).name)
        if digest(regular(Path(root) / path)) != checked_hash(notice.get("sha256")):
            raise ValueError("license digest mismatch")
    return release


def extract(archive, output, expected_hash):
    """Only one exact root regular executable is admissible, including metadata."""
    archive = regular(archive)
    if digest(archive) != checked_hash(expected_hash):
        raise ValueError("archive SHA256 mismatch")
    windows = archive.name.endswith(".zip")
    name = "oidc-cli.exe" if windows else "oidc-cli"
    if windows:
        with zipfile.ZipFile(archive) as packed:
            entries = packed.infolist()
            if len(entries) != 1 or entries[0].filename != name:
                raise ValueError("archive must contain only the root executable")
            entry = entries[0]
            mode = entry.external_attr >> 16
            if entry.flag_bits & 1 or stat.S_ISLNK(mode) or entry.is_dir():
                raise ValueError("nonregular or encrypted archive member")
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG) or entry.file_size > 128 * 1024 * 1024:
                raise ValueError("invalid archive member mode/size")
            data = packed.read(entry)
            mode = 0o755
    else:
        with tarfile.open(archive, "r:gz") as packed:
            entries = packed.getmembers()
            if (len(entries) != 1 or entries[0].name != name or not entries[0].isfile()
                    or entries[0].pax_headers or entries[0].mode != 0o755
                    or entries[0].size > 128 * 1024 * 1024):
                raise ValueError("archive must contain only a mode-0755 root executable")
            data = packed.extractfile(entries[0]).read()
            mode = entries[0].mode
    output = destination(output)
    output.write_bytes(data)
    output.chmod(mode)
    return output


def receipt_check(path, binary, expected_hash, key="darwin_universal"):
    if digest(regular(path)) != checked_hash(expected_hash):
        raise ValueError("notarization receipt SHA256 mismatch")
    receipt = json_object(path.read_text())
    try:
        uuid.UUID(receipt["submission_id"])
    except (ValueError, KeyError, TypeError):
        raise ValueError("invalid notarization submission ID") from None
    if (type(receipt.get("schema")) is not int or receipt.get("schema") != 1 or receipt.get("status") != "Accepted"
            or receipt.get("binaries", {}).get(key) != digest(binary)):
        raise ValueError("notarization receipt does not bind accepted binary")


def verification_evidence(target):
    """Expected acquisition evidence, never a substitute for performing the checks."""
    if target not in VERIFICATION_POLICIES:
        raise ValueError("unsupported external CLI verification target")
    windows = target == "windows-x64"
    return {
        "policy": VERIFICATION_POLICIES[target],
        "signature": "not_applicable" if windows else "passed",
        "accepted_receipt": "not_applicable" if windows else "passed",
        "online_notarization": ("not_applicable" if windows else
                                "passed" if target == "macos-arm64" else "not_run"),
    }


def release_provenance(release, target):
    verification = verification_evidence(target)
    key = "windows-x64" if target == "windows-x64" else "macos"
    return {"repository": REPOSITORY, "tag": release["tag"],
            "archive_sha256": release["assets"][key]["sha256"], "release_eligible": True,
            "verification": verification}


def signature_check(binary, team=None, *, production=False):
    if platform.system() != "Darwin":
        raise ValueError("Apple signature verification requires macOS")
    if type(production) is not bool:
        raise ValueError("explicit production signature profile required")
    native = None
    if production:
        from build_cli import native_target
        native = native_target()
        if native not in ("macos-x64", "macos-arm64"):
            raise ValueError("native macOS signature verification required")
    online = not production or native == "macos-arm64"
    arguments = ["codesign", "--verify", "--strict", "--all-architectures", "--verbose=4"]
    if online:
        arguments += ["--check-notarization", "--test-requirement", "=notarized"]
    for attempt in range(4):
        try:
            subprocess.run([*arguments, str(binary)],
                           check=True, capture_output=False, timeout=120)
            break
        except subprocess.CalledProcessError as error:
            if not online or error.returncode != 3 or attempt == 3:
                raise
            print("Apple notarization requirement not satisfied; retrying in 15 seconds "
                  f"(attempt {attempt + 2}/4)", file=sys.stderr)
            time.sleep(15)
    subprocess.run(["lipo", str(binary), "-verify_arch", "x86_64", "arm64"],
                   check=True, capture_output=True, timeout=20)
    teams = set()
    for arch in ("x86_64", "arm64"):
        result = subprocess.run(["codesign", "--display", "--verbose=4", "--arch", arch, str(binary)],
                                check=True, capture_output=True, text=True, timeout=20)
        display = result.stdout + result.stderr
        match = re.search(r"^TeamIdentifier=([A-Z0-9]{10})$", display, re.M)
        if (not match or (team and match[1] != team)
                or "Authority=Developer ID Application:" not in display
                or not re.search(r"^Timestamp=.+$", display, re.M)
                or not re.search(r"^CodeDirectory .*flags=.*\([^)]*\bruntime\b", display, re.M)
                or "Signature=adhoc" in display):
            raise ValueError("Developer ID hardened runtime/timestamp/team required")
        teams.add(match[1])
    if len(teams) != 1:
        raise ValueError("universal slices must share Developer ID team")
    if production:
        evidence = verification_evidence(native)
        del evidence["accepted_receipt"]
        return evidence


def version_check(binary, version):
    result = subprocess.run([str(binary.resolve()), "version"], input=b"", capture_output=True, timeout=20)
    try:
        value = json_object(result.stdout)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("invalid native version JSON") from None
    if (result.returncode or result.stderr or not isinstance(value, dict)
            or type(value.get("protocol_version")) is not int or value["protocol_version"] != 1
            or value.get("ok") is not True or value.get("version") != version):
        raise ValueError("native CLI version/protocol mismatch")


def fetch(url, path):
    class HTTPSOnlyRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, response, code, message, headers, new_url):
            if not new_url.startswith("https://"):
                raise ValueError("HTTPS download redirect required")
            return super().redirect_request(request, response, code, message, headers, new_url)
    if not url.startswith("https://"):
        raise ValueError("HTTPS download required")
    opener = urllib.request.build_opener(HTTPSOnlyRedirect)
    with opener.open(url, timeout=60) as response:
        if not response.url.startswith("https://"):
            raise ValueError("HTTPS download required")
        destination(path).write_bytes(response.read(128 * 1024 * 1024 + 1))


def acquire(root, target):
    from build_provenance import record
    from build_cli import native_target
    root = Path(root)
    verification = verification_evidence(target)
    release = load_pin(root)
    if target != native_target():
        raise ValueError("acquisition/version evidence requires the native target")
    key = "windows-x64" if target == "windows-x64" else "macos"
    asset = release["assets"][key]
    cache = root / "build/external-cli"
    base = f"https://github.com/{REPOSITORY}/releases/download/{release['tag']}/"
    archive = cache / asset["name"]
    fetch(base + asset["name"], archive)
    binary = root / "build" / target / ("oidc-cli.exe" if key == "windows-x64" else "oidc-cli")
    try:
        extract(archive, binary, asset["sha256"])
        if digest(binary) != asset["binary_sha256"]:
            raise ValueError("reviewed binary digest mismatch")
        if key == "macos":
            receipt = cache / "APPLE_NOTARIZATION.json"
            fetch(base + receipt.name, receipt)
            receipt_check(receipt, binary, release["receipt_sha256"])
            verification = {
                **signature_check(binary, release["apple_team_id"], production=True),
                "accepted_receipt": "passed",
            }
            if verification != verification_evidence(target):
                raise ValueError("signature verification host differs from acquisition target")
        version_check(binary, release["version"])
        status = record(root, target, binary, True, PROFILE)
        status["external"] = release_provenance(release, target)
        binary.with_name("build-manifest.json").write_text(json.dumps(status, indent=2) + "\n")
        return binary
    except Exception:
        binary.unlink(missing_ok=True)
        binary.with_name("build-manifest.json").unlink(missing_ok=True)
        raise


def verify_binary(root, binary, target):
    verification_evidence(target)
    release = load_pin(root)
    key = "windows-x64" if target == "windows-x64" else "macos"
    if digest(regular(binary)) != release["assets"][key]["binary_sha256"]:
        raise ValueError("bundled CLI differs from reviewed signed upstream bytes")
    if key == "macos":
        signature_check(binary, release["apple_team_id"], production=True)


def verify_bundle(root, archive, repository):
    """Publication runs on Linux: bind embedded bytes, not a local replacement."""
    release = load_pin(root)
    prefix = repository + ".4dbase/Resources/"
    expected = {
        prefix + "bin/macOS/oidc-cli": release["assets"]["macos"]["binary_sha256"],
        prefix + "bin/Windows/oidc-cli.exe": release["assets"]["windows-x64"]["binary_sha256"],
        **{prefix + "licenses/" + Path(notice["path"]).name: notice["sha256"]
           for notice in release["licenses"]},
    }
    with zipfile.ZipFile(regular(archive)) as packed:
        names = packed.namelist()
        for name, checksum in expected.items():
            if names.count(name) != 1:
                raise ValueError("bundled upstream executable/license missing or duplicated")
            entry = packed.getinfo(name)
            mode = entry.external_attr >> 16
            if (not stat.S_ISREG(mode) or entry.file_size > 128 * 1024 * 1024
                    or ("/bin/" in name and stat.S_IMODE(mode) != 0o755)
                    or hashlib.sha256(packed.read(entry)).hexdigest() != checksum):
                raise ValueError("bundled upstream bytes/mode differ from reviewed release")


def dev_verify(root):
    """Explicit local source-fixture aid, never emits a production build manifest."""
    folder = Path(root) / "build/dev-cli"
    binary = folder / "verified/oidc-cli"
    try:
        dev_checksums(folder)
        archive_name = f"oidc-cli_{DEV_VERSION}_darwin_universal.tar.gz"
        extract(folder / archive_name, binary, DEV_DIGESTS[archive_name])
        receipt_check(folder / "APPLE_NOTARIZATION.json", binary, DEV_DIGESTS["APPLE_NOTARIZATION.json"])
        signature_check(binary)
        version_check(binary, DEV_VERSION)
        destination(folder / "verified/development-only.json").write_text(json.dumps({
            "release_eligible": False, "repository": REPOSITORY, "run_id": 43041282015,
            "commit": DEV_SHA, "version": DEV_VERSION, "binary_sha256": digest(binary)}, indent=2) + "\n")
        return binary
    except Exception:
        binary.unlink(missing_ok=True)
        binary.with_name("development-only.json").unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check-pin", "acquire", "verify-dev"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--target", choices=("macos-x64", "macos-arm64", "windows-x64"))
    args = parser.parse_args()
    try:
        if args.command == "check-pin":
            load_pin(args.root)
        elif args.command == "verify-dev":
            print(dev_verify(args.root))
        else:
            if not args.target:
                raise ValueError("--target required")
            print(acquire(args.root, args.target))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(2, f"external CLI rejected: {error}\n")


if __name__ == "__main__":
    main()
