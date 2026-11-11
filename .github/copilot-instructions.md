Read AGENTS.md, README.md, the component skill and relevant class docs/tests.
This initialized public repository is a 4D component facade over external
miyako/oidc-cli, not a native plug-in or a CLI source project. Never reinitialize,
restore a greeting starter, rebuild the dependency or move OIDC logic into 4D.

Use the reviewed external-asset profile, exact tags/digests/receipt/license
notices and build-time bundling. Preserve Developer ID/notarized CLI bytes and
mode. No runtime latest downloader, PATH fallback, re-sign/lipo, quarantine
removal or unsigned fallback. Development CI artifacts cannot authorize release.

Keep UI APIs nonblocking; each attempt owns a worker, shared state and bounded
SystemWorker cleanup. Close stdin; drain/bound streams separately; validate
normal exit, strict UTF-8/protocol, exact case-sensitive issuer and token opt-in.
Use documented PROCESS PROPERTIES unique IDs for owner checks; fail explicitly
when owner metadata is unavailable. Shared copies must join the destination
state's group. Never log tokens, authorization URLs or raw protocol/4D errors.
Preflight malformed JSON without exception diagnostics.

Retain real tool4d source/compiled host fixtures, compiler input/output
provenance, source stripping, explicit ZIP directories and executable modes.
Every headless project needs dependencies.json before first open. Compilation
is not host execution; test the exact unpacked package. Keep CI and manual
Publish, prefix-free component SemVer and independently versioned CLI pins.
Publication must fail closed on unresolved pins/licenses, missing native/full
async host evidence or required outer Apple signing/notarization/stapling.

Report actual architecture and passed/failed/not_run checks. Headless ARM64
async-worker checks do not prove normal IDE UI, Auth0/browser/MFA, native Intel/
Windows 4D, Dependency Manager installation or transaction-bound 4D Server login.
No secret access, activation, merge, tag or release without explicit approval.
