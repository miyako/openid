# Acceptance scope

## Current universal policy

The owner explicitly superseded the temporary ARM64-only decision and prefers
universal macOS support. The original signed v0.1.1 universal asset, facade
selector, three native CLI targets and same-source assembly requirements are
restored. No binary was rebuilt, re-signed, thinned or reassembled.

Native ARM64 retains independent online notarization verification. Actual
native Intel retains strict all-slice cryptographic signature, Developer ID/
team, hardened runtime, secure timestamps, pinned archive/binary/receipt
hashes and the Accepted upstream universal receipt, but **omits the online
notarized requirement by an explicit reviewed policy**. This is not a successful
Intel online observation. The target-scoped tier is bound to provenance and
acceptance; it cannot be selected by OIDC configuration or a failed-check
fallback. See [verification policy and limits](verification-policy.md).

Hosted native CLI fixtures exercise version, a one-second global timeout, and
POSIX SIGTERM cancellation against a disposable loopback discovery server.
The fixture intentionally never completes discovery, so no browser,
authorization URL or token is involved; processes and server threads are
bounded and torn down. Windows runs native version/timeout; its POSIX signal
test is explicitly skipped. These are CLI lifecycle checks, not provider login
or native Intel/Windows 4D acceptance.

## Executed current universal-policy acceptance

At component commit `131b56ce8a4df7e387062288a4dd36b13981ec15`,
[CI run 43117236685](https://github.com/miyako/openid/actions/runs/43117236685)
passed configuration, all three native CLI jobs and universal resource
assembly. Actual downloaded same-commit manifests contain:

| Target | Signature | Accepted receipt | Online notarization | Native lifecycle |
| --- | --- | --- | --- | --- |
| macOS Intel x64 | passed | passed | **not_run**, declared Intel policy | Version, timeout and SIGTERM cancellation passed |
| macOS ARM64 | passed | passed | passed | Version, timeout and SIGTERM cancellation passed |
| Windows x64 | not_applicable | not_applicable | not_applicable | Version and timeout passed; POSIX SIGTERM explicitly skipped |

Assembly on ARM64 independently rechecked the identical universal bytes with
the ARM64 online requirement. That does not relabel Intel's `not_run` tier.
The local Python suite ran **232 tests: 229 passed, 3 native-only skips** under
GitHub-style repository/ref variables. Workflow and generated-icon checks pass.

Using approved tool4d **20.7 build 20.101905** on native ARM64, both actual
compiler targets passed after assembling the three native artifacts and all
six pinned notice files. Both the real source host and the **exact unpacked
full universal ZIP** passed the complete contract with native CLI `0.1.1`,
`asyncDesktopStatus:"passed"` and zero leaked workers; compiled mode was
respectively false and true. Embedded executable modes, binary/notice digests,
source stripping and the unpacked CLI's actual ARM64 signature/online check
were also verified.

The local inspection ZIP SHA256 is
`364acdb8b6632365a9de1204dd904f802b818ee01d3e0e7eaaff88ca31746ee6`
(9,356,650 bytes), bound to the commit above. It is not a published release
or outer-notarized distribution. Adjacent retained inspection evidence marks
`release_ready:false`; it does not manufacture hosted signing acceptance.
The native manifests, source/compiler/compiled-host reports and exact archive
are preserved separately.

Native Intel/Windows **4D** execution, normal desktop UI/Auth0/MFA,
quarantined/downloaded first launch and the outer Developer ID signed,
notarized/stapled DMG remain **not run**. No merge, tag, release, quarantine
removal, Gatekeeper setting change or local signing-secret operation occurred.

Published **v0.1.1** now satisfies the signed/notarized asset checks, and exact
tag/archive/binary/receipt metadata is recorded. The owner explicitly authorized
MIT licensing covering the existing release. The immutable grant and complete
dependency/runtime notices are now pinned; production dependency acquisition
is enabled. Published `v0.1.0` and `v0.1.0-rc.2` precede signing support and remain
unacceptable. This resolves the dependency/permission gates, not the remaining
outer distribution signing or unexecuted platform/provider acceptance.

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

## Published v0.1.1 asset review

The user-requested release
[`v0.1.1`](https://github.com/miyako/oidc-cli/releases/tag/v0.1.1) points to
source commit `1c909c00e6aa4924c4755e325f8ba8bb25927b31`. All four archives and
the receipt passed `SHA256SUMS`; the selected universal/Windows archive and
receipt SHA256 values also match the release API digests. Extraction rejected
anything except each exact root regular executable.

The universal executable independently passed Developer ID verification for
team `Y69CWUC25B`, hardened runtime, timestamp, both Mach-O architecture
signatures and online notarization. The receipt is `Accepted`, submission
`7a9552e3-aa5d-419d-bb9f-b2c579d1f0f6`, and binds that exact executable hash.
Only after verification, native ARM64 `version` returned protocol1, `ok:true`,
version `0.1.1`. The executable was not re-signed, reassembled or dequarantined.
This initial asset-only review inspected Windows archive/hash/shape without
executing it. Current CI results above separately establish native Windows
CLI version/timeout, not Authenticode signing or native Windows 4D.

Exact selected archive/binary/receipt hashes are recorded in
[`scripts/oidc-cli-pin.json`](../scripts/oidc-cli-pin.json).
Its status is now `reviewed`, with MIT license/grant and all required notices
from licensing commit `847a235a3cc02d82b4f3b432e5eb42c7cab5d3fc` pinned
separately from the older binary/source release. See
[redistribution provenance](redistribution.md).
The component's earlier full source/compiled development-host acceptance used
the separately approved CI artifact, not this new release; those scopes must
not be conflated.

## Historical full-online Intel gate

The MIT grant/notices and reviewed production pin are enabled by component
commit `f7fe775ef9f56f246043283203f69a892e320044`. Local ARM64 production
acquisition passed the complete archive/receipt/Developer ID/both-slice/online
notarization/native-version checks. The real source host executed **v0.1.1**
with `compiled:false`, `asyncDesktopStatus:"passed"` and zero leaked workers,
including cancellation, timeout, owner exit and protocol/sanitization cases.
Both actual 4D compile targets subsequently passed with the staged macOS
v0.1.1 executable and six notice files. At that point no native Windows/Intel
4D execution or final packed v0.1.1 component acceptance had been performed.

At commit `480eb99a4ffa603d07f46d296da2b3022893d545`, the full Python suite
passed 221 tests with one native-only skip. In
[CI run 43109110167](https://github.com/miyako/openid/actions/runs/43109110167),
configuration, ARM64 native acquisition and Windows x64 native acquisition/
version passed. The independent **fresh Intel macOS** job exhausted four strict
online notarized-requirement checks with 15-second pauses. Every attempt
reported `valid on disk` and `satisfies its Designated Requirement`, followed by
`test-requirement: code failed to satisfy specified code requirement(s)` and
exit3. Assembly was skipped. Signature integrity and the MIT permission are
not the failing gates; the cause of the fresh Intel notarized-requirement
rejection is not established.

Upstream
[v0.1.1 publishing run 43102918063](https://github.com/miyako/oidc-cli/actions/runs/43102918063)
previously passed exact extracted universal checks and native Intel `version`
on its signing/publishing host. That host had just submitted the same binaries
to Apple; it is not independent cold-Intel acceptance and does not override
the current failure. Neither retries nor a receipt/plain signature can replace
a passing online requirement. No unsigned fallback, requirement bypass,
re-signing, tag replacement, release or merge was performed.

The current native Intel receipt-only tier is the owner's explicit compatibility
choice after that investigation, not a diagnosis or claim that the failed
requirement now passes. ARM64 online verification, all signature/byte checks
and mandatory outer signing/notarization/stapling remain unchanged.
