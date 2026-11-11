# openid component

This is the public `miyako/openid` **4D wrapper component**, namespace `OpenID`,
classes `Client` / `Task`, external executable basename `oidc-cli`. Do not move
OIDC logic here, add NetKit/native plug-ins, rebuild the CLI or restore a
template greeting starter.

The source scaffold was initialized using
`miyako/4d-component-template` at
`d2e161b61c9f8d37f30c1410fb5c11f9f08a826d`. Read its
[canonical playbook](https://github.com/miyako/4d-component-template/blob/d2e161b61c9f8d37f30c1410fb5c11f9f08a826d/AGENTS.md)
and the local component skill for real 4D/compiler/package conventions.
**Its native CLI starter/build instructions are superseded here by the
deliberate external pinned-asset adapter.** Do not run initialize/rename again.

## Required boundaries

- Only use reviewed exact upstream release tags, platform archive SHA256 and
  receipt hashes. Acquire at build time, never runtime/latest. Verify archives
  before extraction; reject symlinks, traversal, extra entries and mixed inputs.
- Preserve notarized Developer ID CLI bytes and mode. Never lipo, re-sign or
  remove quarantine from the external macOS executable. No unsigned fallback.
  Windows x64 has no configured Authenticode signing; do not claim otherwise.
- Published v0.1.1 signing/integrity and the owner's explicit MIT grant are
  reviewed. Its exact pin includes separate immutable licensing provenance
  and complete dependency/runtime notices; preserve all of them when bundling.
  Approved CI-artifact development acceptance is separate, never release eligible.
- No local secret access, Keychain operations or uploads. The user owns setup.
  No tag, release, merge, activation or global installation without authorization.
- UI APIs must remain nonblocking. Each attempt owns its cooperative worker,
  shared cancellation state, bounded SystemWorker lifecycle and cleanup.
  Do not queue cancellation behind authentication or kill its 4D worker directly.
- Send one UTF-8 protocol1 config on stdin and close input; separately drain/bound
  stdout/stderr. Validate status, version, shape, issuer and token opt-in.
  Never log/persist raw output, authorization URLs or tokens.
- `(issuer, subject)` is the default identity key. This is not a transaction-bound
  4D Server login assertion. No client secrets/cache/refresh/provider logout.

## Validation and release conventions

Use the Python suite and real source/compiled host fixtures, not static checks
as substitutes for runtime evidence. Every headless project must already have
`Project/Sources/dependencies.json`. Use the approved free checksum-pinned
worktree-local tool4d; never activate a license or install globally.

Keep actual compiler input/output digest provenance, source-stripped packed
`.4DZ`, external native Libraries, explicit ZIP directory records and executable
modes. Test the exact final unpacked `.4dbase` in compiled mode. Recompile after
input changes. Preserve source/compile/final-host reports separately.

Keep exactly CI and manual Publish workflows, prefix-free component SemVer
tags, bounded bump semantics and fail-closed acceptance/signing. An independently
versioned upstream CLI must not be rewritten by component version bumps.
The signed/notarized/stapled outer DMG path must preserve the CLI signature.

Report actual architecture/tool/artifact/revision evidence. Dual-target
compilation is not native execution on both architectures. Apple Silicon host
checks do not establish native Intel/Windows 4D, Auth0/browser/MFA, Dependency
Manager installation or 4D Client/Server authentication.
