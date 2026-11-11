# Acceptance scope

Production packaging is blocked until a reviewed published **signed/notarized**
CLI release can be pinned with exact tag, platform archive hashes and receipt.
Published `v0.1.0` and `v0.1.0-rc.2` precede that support.
The public upstream currently lacks a root redistribution license; permission
and complete dependency/runtime notices are a separate required release review.

For explicitly approved development checks only, upstream nonpublishing
[run 43041282015](https://github.com/miyako/oidc-cli/actions/runs/43041282015)
at `27dd05ce90c0ecf0487a99d0e030e9d3a89ef37d` has `release-assets` for
`0.0.0-signing-check`. CI artifacts are not production release pins. Verify
all archives/checksums, receipt binding and actual Developer ID hardened-runtime
timestamp/notarized signatures independently before execution. Preserve bytes
and executable mode; do not re-sign, lipo or remove quarantine.

The template's free tool4d pin is 20.7 build 101905, macOS ARM64, archive SHA256
`40a5d177a4f73165f52abf6ec8000249d81411c41353ccf258cece8e74639261`.
The user explicitly approved a worktree-local checksum-verified `.tools`
download; no global installation, license activation or signing-secret
operation is needed.

Real source/compiled fixtures distinguish:

| Check | What it establishes |
| --- | --- |
| Python tests | Acquisition/protocol/source contracts and packaging invariants |
| Real 4D source host | Actual namespace/API, native async version, invalid settings/protocol, active cancellation, CLI timeout, owner exit, zero leaked workers, resource/argument failures |
| Real compiler | Fresh compiled code for x86_64 generic + macOS ARM64 |
| Unpacked compiled host | Actual source-stripped package loading and compiled mode |
| Synthetic identity fixture | Wrapper schema/issuer/token policy only, **not** provider login |
| Upstream Keycloak E2E | Separately maintained CLI real-provider behavior only |

Native Windows/Intel 4D, Auth0/browser/MFA, Dependency Manager downloaded
release installation, outer signed/stapled DMG and 4D Client/Server login are
separate checks. Do not infer them from Apple Silicon tool4d or native CLI
execution. Windows CLI has no configured Authenticode signing.

Save actual run reports under ignored `build/`, keeping source-host,
compile and compiled-host evidence distinct. A green test suite or compiler
exit without a fresh status file cannot approve a package. No release, tag or
merge is authorized here.

## Executed local acceptance

On macOS ARM64, free tool4d **20.7 build 20.101905** passed the source fixture,
actual `Compile project` for `x86_64_generic` + `arm64_macOS_lib`, and the same
fixture against the **exact unpacked development ZIP** with compiled mode true.
The approved CLI reports `0.0.0-signing-check`, binary SHA256
`fe77be341661bfa05c36e26fada3abfb418ad7d666aecdace503129da28fd768`.
Actual native execution was ARM64; compiling the Intel target and verifying
both Mach-O signatures is not Intel runtime execution.

The source investigation corrected real compatibility issues:
use documented `PROCESS PROPERTIES` unique IDs rather than unavailable
process-activity metadata; group shared result copies with their destination
state; and use `Split string` rather than a nonexistent Text `.split()`.
Strict Text helpers also avoid 4D's linguistic/case-insensitive defaults when
checking issuer equality, configuration fields, scopes and duplicate JSON keys.
Negative task numbers in tool4d diagnostic output are not the API's process
numbers. **The earlier provisional claim that tool4d cannot exercise owner
lifetime is superseded:** full async worker lifecycle checks pass without an
ownership bypass. Contexts that genuinely lack owner metadata still fail closed.

Malformed JSON is preflighted without parser exceptions to prevent 4D diagnostic
logging from echoing credential-bearing input. The fixture checks escaped
strings, Unicode, duplicate keys, invalid escapes/surrogates, malformed framing,
stream thresholds, token opt-in/disposal and sanitized failures. Synthetic
identity decoding remains distinct from an actual provider login.

```sh
python3 scripts/test_4d.py --root . --tool4d .tools/tool4d.app/Contents/MacOS/tool4d --require-desktop
python3 scripts/compile_component.py --root . --tool4d .tools/tool4d.app/Contents/MacOS/tool4d
python3 scripts/package_component.py --root . --repository miyako/openid --development --unpack-test
python3 scripts/test_4d.py --root . --tool4d .tools/tool4d.app/Contents/MacOS/tool4d \
  --component build/release-test/openid.4dbase --require-desktop
```

`--require-desktop` requires desktop-style owner/cancel/timeout semantics in the
4D engine, which this tool4d supports. It does **not** certify GUI behavior.
Production acquisition/publication cannot consume the development-only package.
See [external adapter](../scripts/EXTERNAL_CLI.md) for precise pin/provenance gates.

## Normal desktop/manual acceptance still required

With an already installed, licensed normal 4D desktop host, run the same source
and compiled fixture with `--tool4d /path/to/4D --require-desktop` (the option
names the executable; no license activation is performed). Then use the README
form sample with the user's own provider configuration and complete the
[interactive provider checklist](providers.md). Check UI responsiveness while
browser/MFA is pending, cancellation, form unload/disposal and host shutdown.
Repeat on native Intel macOS and Windows x64; do not infer those results from
the ARM64 headless run. No normal desktop installation/activation is authorized
or performed by these instructions.
