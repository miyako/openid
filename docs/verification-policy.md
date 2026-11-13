# Universal macOS verification policy

The owner explicitly prefers universal macOS support and approved the narrower
Intel acquisition policy below. This supersedes the temporary ARM64-only scope
decision. It does **not** establish that the previously failing Intel online
notarization check now passes.

## Required checks by native build host

| Native target | macOS ARM64 | macOS Intel x64 | Windows x64 |
| --- | --- | --- | --- |
| Exact reviewed archive and executable SHA256 | Required | Required | Required |
| Upstream macOS resource | Original signed universal executable | Same original signed universal executable | Not applicable |
| Strict cryptographic signature, all architectures | Required | Required | Not applicable |
| Developer ID, team `Y69CWUC25B`, hardened runtime, secure timestamps | Required for both slices | Required for both slices | No Authenticode signing configured |
| Pinned upstream receipt, status `Accepted`, exact universal binary binding | Required | Required | Not applicable |
| Online `--check-notarization` and explicit `=notarized` requirement | Required; failure stops acquisition | **Not performed under the explicit reviewed Intel policy** | Not applicable |
| Native protocol/version execution | Required | Required | Required |

The exact target-scoped policy is part of the reviewed pin and native
provenance. It is selected from the actual native build host, not a component
configuration value, command-line escape hatch or response to a failed check.
Translated execution cannot qualify as a native Intel build. An ARM64 online
failure cannot downgrade to the Intel policy. Signature, archive, receipt,
team, runtime, timestamp or version failures still stop the build.

Intel evidence must say that the online requirement was **not run by policy**,
never that it passed. Assembly and release acceptance must preserve and verify
that distinction. The CLI remains the separately maintained published
`miyako/oidc-cli` v0.2.0 universal asset; it is not rebuilt, re-signed, thinned
or reassembled. Windows remains explicitly unsigned.

## Recorded policy and evidence

The pin's `release.verification_policy` must match this fixed reviewed map:

```json
{
  "macos-x64": "native-intel-accepted-receipt-v1",
  "macos-arm64": "native-arm64-online-notarized-v1",
  "windows-x64": "native-windows-integrity-v1"
}
```

Each native manifest retains its existing target/source/commit/binary/execution
binding and adds `external.verification`. Intel records:

```json
{
  "policy": "native-intel-accepted-receipt-v1",
  "signature": "passed",
  "accepted_receipt": "passed",
  "online_notarization": "not_run"
}
```

ARM64 records its own policy with all three checks `passed`; Windows records
its integrity policy with all three Apple checks `not_applicable`. Acceptance
preserves the full manifest at `steps.cli_test_<target>.details`; a passed
native execution step does not turn Intel's online `not_run` into a pass.
Publication independently checks the exact target-specific evidence.

## Why this exception exists

Independent fresh Intel CI repeatedly reported `valid on disk` and
`satisfies its Designated Requirement`, followed by explicit notarized
requirement failure (exit3), including
[run 43109110167](https://github.com/miyako/openid/actions/runs/43109110167).
The identical universal binary passed the online check on ARM64. Upstream
Apple submission was `Accepted`; its Intel signing/publishing host had also
passed verification. Those observations do not establish why a fresh Intel
host rejects the online requirement, nor prove a CPU incompatibility.

The owner chose to retain Intel compatibility with that uncertainty explicitly
documented. This is weaker independent notarization verification on Intel,
not an unsigned fallback and not proof of fresh-host Gatekeeper acceptance.

## Limits and unchanged boundaries

No quarantine attribute is removed. Gatekeeper is not disabled or bypassed.
No promise is made that a quarantined download will launch without an Apple
policy rejection on Intel. Real downloaded/quarantined first-launch acceptance
remains unverified until separately exercised.

The outer component distribution still requires the existing Developer ID
signing, Apple notarization and stapled DMG process. This acquisition exception
does not disable those publication gates, alter signed CLI bytes, or authorize
a merge, tag or release.

Native CLI checks are distinct from native 4D host checks. Hosted tests may
establish Intel CLI version, bounded timeout and signal-cancellation behavior;
they do not establish native Intel 4D, normal IDE UI, Auth0/browser/MFA or
downloaded-release behavior. Available ARM64 source and exact compiled-host
evidence must be reported separately. Both 4D compiler targets remain necessary
for generic x86_64 code and the macOS ARM64 library; compilation is not native
execution on every platform.

The facade remains `macOS-universal` (or its macOS default) and explicit
`Windows-x64`. No OIDC trust, TLS, PKCE/state/nonce, protocol, token opt-in,
worker cancellation/deadline, license-notice or identity-is-not-server-login
boundary is relaxed by this platform policy.
