# External oidc-cli adapter

This initialized wrapper deliberately uses `external-oidc-cli-v1`, **not** the
template's stock `cli-universal-v1` source-builder contract. The retained Go
language metadata records initializer/upstream provenance; no Go toolchain,
upstream checkout, source build, lipo assembly, runtime downloader or `latest`
resolution is used. CI and Publish are the only workflows. Existing real 4D
compiler, packer, source/compiled host acceptance and release asset gates remain.

## Acceptance ownership and authorization

Local tool4d download was initially withheld, then explicitly authorized through
the parent coordinator. The parent owns the existing checksum-pinned downloader,
compiler and real source/compiled fixtures. This adapter does not invoke those
steps or dispatch any hosted workflow/publication. The existing checksum pin in
`package.json.tool` and downloader/compiler hooks remain intact.
CI's optional tool4d/host stages require **manual workflow_dispatch** plus
`FOURD_ENABLED=true`; ordinary push/PR runs cannot download tool4d. Publish
remains manual and requires the reviewed external pin, real host evidence and
the mandatory outer signing/notarization gates.
This scaffold does not manufacture source/compiled-host evidence.

Host acceptance uses the same registry in source and compiled mode. Its version
observation is a sanitized successful process envelope; synthetic identity
decoding is wrapper/protocol evidence, **not** provider or server-login proof.
The supported facade is `Client.new(config;target).authenticate()` / `version()`
returning a Task with `done`, `result()`, `cancel()`, `dispose()` and
`takeAuthorizationURL()`. No UI-thread wait is allowed: bounded `.wait(0.05)`
belongs only to the per-attempt `CALL WORKER`. Generic `_Process` argument
round-trip checks remain independent of OIDC identity decoding.

## Reviewed production dependency

`scripts/oidc-cli-pin.json` enables exact **v0.1.1** asset acquisition with
`status:reviewed`. Its archives, Developer ID, hardened runtime, timestamp,
both slices, online notarization and native `version` have passed independent
verification. The owner authorized MIT licensing, explicitly covering the
existing release source and binaries, at separate licensing commit
`847a235a3cc02d82b4f3b432e5eb42c7cab5d3fc`. All five upstream licensing
documents plus the Go baseline notice are vendored byte-for-byte, hash-pinned
and required in the assembled/packaged component. The combined notice bundle
covers both dependencies and the Go runtime, including PATENTS and embedded
third-party licenses. See [redistribution provenance](../docs/redistribution.md)
and [v0.1.1 evidence](../docs/acceptance.md#published-v011-asset-review).
Neither unsigned `v0.1.0` nor `v0.1.0-rc.2` is approved. A release must have a reviewed exact
`miyako/oidc-cli` tag/version, universal macOS and unsigned Windows x64 archive
names, archive and executable SHA256 values, `APPLE_NOTARIZATION.json` SHA256,
expected Developer ID team and redistribution licenses. Permission comes from
the explicitly published owner grant, not public repository visibility.

The `release` object includes reviewed license records of all three kinds
(placeholders in this schema example are deliberately invalid). Multiple
`upstream` records preserve both the standard MIT text and existing-release
grant; the actual pin also retains the notice manifest and scope documentation.

```json
{
  "version": "X.Y.Z",
  "tag": "vX.Y.Z",
  "apple_team_id": "REVIEWED_TEAM",
  "receipt_sha256": "REVIEWED_SHA256",
  "assets": {
    "macos": {
      "name": "oidc-cli_X.Y.Z_darwin_universal.tar.gz",
      "sha256": "REVIEWED_ARCHIVE_SHA256",
      "binary_sha256": "REVIEWED_EXECUTABLE_SHA256"
    },
    "windows-x64": {
      "name": "oidc-cli_X.Y.Z_windows_amd64.zip",
      "sha256": "REVIEWED_ARCHIVE_SHA256",
      "binary_sha256": "REVIEWED_EXECUTABLE_SHA256"
    }
  },
  "licenses": [
    {"kind": "upstream", "path": "scripts/licenses/UPSTREAM.txt", "sha256": "REVIEWED_SHA256"},
    {"kind": "dependencies", "path": "scripts/licenses/DEPENDENCIES.txt", "sha256": "REVIEWED_SHA256"},
    {"kind": "runtime", "path": "scripts/licenses/Go-LICENSE.txt", "sha256": "REVIEWED_SHA256"}
  ]
}
```

Changing the manifest to `status:reviewed` is a code-review decision, not an
automatic discovery step. Preserve immutable release bytes; inspect upstream
provenance and licenses before recording reviewed digests.

```sh
python3 scripts/external_cli.py check-pin
python3 scripts/external_cli.py acquire --target macos-arm64
python3 scripts/ci_config.py assemble
```

Acquisition verifies the pinned archive before extracting its only allowed root
regular executable. Traversal, links, duplicate/extra entries and unexpected
macOS modes are rejected. The accepted receipt must bind the exact signed
universal binary, which must pass Developer ID, hardened runtime, timestamp,
both architectures and online notarization checks **before execution**. Native
`version` must return `protocol_version:1`, `ok:true` and the upstream version;
component and CLI versions are independent. Windows x64 is explicitly unsigned
and tested natively, not presented as publisher-authenticated.

The Apple notarized-requirement check retries only requirement-failure exit3,
at most four identical strict checks with 15-second pauses. This follows the
upstream signing workflow's bounded retry approach; it does not classify the
failure as transient or accept a receipt/plain signature in place of a passing
online requirement. Other exit codes and timeouts fail immediately. OS
signature diagnostics are visible; credential-bearing CLI output is not.

Each same-commit manifest binds adapter inputs, pin, licenses, archive digest and
binary bytes. Assembly copies the universal binary unchanged; it never
reassembles/re-signs its slices. Actions strips modes, so assembly restores the
reviewed archive's executable mode. Packaging rechecks hashes/signatures and
bundles notices. Optional outer signing touches 4D libraries/container only:
the notarized upstream CLI is immutable. Receipt JSON is informational evidence,
not a substitute for OS signature and online notarization verification.

Publish checks the pin **before** bumping or committing. Wrapper patch/minor/
major and legacy stable-tag baseline behavior is preserved; only wrapper
metadata and explicitly declared wrapper surfaces change. Dependency pins,
upstream native version and release signing policy are never bumped implicitly.
Unresolved pins, missing native evidence, missing real source/compiled 4D host
evidence or signing failures prohibit publication. No release was published.
For this external profile the outer DMG is always Developer ID signed,
notarized and stapled: an absent/empty `apple_notarized_versions` list cannot
disable that requirement. The version list remains relevant to native-source
template consumers only; unsigned inspection is never external publication.

Loading/protocol-only fixture checks remain partial. Production hosted
acceptance requests the full asynchronous lifecycle fixture and requires the literal
`asyncDesktopStatus:"passed"` in source and exact final compiled-host reports;
publication independently rechecks both reports. `not_run`, missing, failed or
truthy non-Text statuses cannot approve a release. Desktop ownership validation
must not be bypassed when process metadata is unavailable. Actual tool4d worker
lifecycle execution can qualify when the stable legacy process-properties API
supplies real ownership metadata; there is no tool4d-specific exclusion. This
status does not assert normal IDE UI, interactive browser/provider, or MFA
acceptance.

## Authorized local development artifact (not release eligible)

The explicitly approved artifact is `release-assets` from `miyako/oidc-cli`
run `43041282015`, exact commit
`27dd05ce90c0ecf0487a99d0e030e9d3a89ef37d`, version
`0.0.0-signing-check`. Download only into ignored `build/dev-cli/`:

```sh
gh run download 43041282015 --repo miyako/oidc-cli --name release-assets --dir build/dev-cli
python3 scripts/external_cli.py verify-dev
```

The adapter independently pins all four approved platform archive digests and
the receipt digest. It parses `SHA256SUMS`, requires exactly those five approved
basenames/digests, rejects duplicate/traversal/extra entries, and hashes every
downloaded archive plus the receipt. Only the universal binary is extracted
and executed; receipt, binary, signature, both slices, online notarization and
native version checks precede any execution. The verified source-fixture executable is
`build/dev-cli/verified/oidc-cli`. Its adjacent `development-only.json` explicitly
records `release_eligible:false`. It emits **no** production build manifest, is
never placed in component resources automatically, and cannot pass production
packaging/publication gates. This helper neither reads secrets nor changes any
keychain. Bare executables rely on online Apple ticket lookup; offline
first-launch and actual quarantined/downloaded-host acceptance are not implied.

The parent explicitly authorized copying this verified development binary to
`component/openid/Resources/bin/macOS/oidc-cli` for real host fixtures. That
ignored local resource preserves the exact signed hash and mode and was
reverified after copying. Staging it does not resolve the production pin, emit
production provenance or authorize distribution.

For explicitly approved compiled development-host checks only:

```sh
# First compile current inputs with the parent-owned approved tool4d.
python3 scripts/package_component.py --root . --repository miyako/openid --development --unpack-test
```

This emits `build/development/openid.development.zip` and restores
`build/release-test/openid.4dbase`. Development packaging ignores
`GITHUB_REF_NAME`; an explicitly supplied `--tag` must still equal the configured
component version. Production packaging retains its release-tag environment
fallback and version validation. It requires the exact approved development
archive, receipt, signed executable/hash/mode and online signature verification.
It retains the original compiler input/output provenance gate, source-stripped
`.4DZ`, native libraries, explicit ZIP directories and executable modes.
Changed/staged resources require recompilation; no marker is rewritten.
The package is macOS-only, excludes Windows executables, contains a conspicuous
`DEVELOPMENT_ONLY.json` with `release_eligible:false`, and does not enter `dist/`
or emit release acceptance/provenance. This historical CI artifact remains
nonrelease; approval of the separately published v0.1.1 pin does not promote it.
This exception is not available in CI/Publish entry points and does not alter
production pin, packaging or publication gates.
