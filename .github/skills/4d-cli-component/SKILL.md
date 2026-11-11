---
name: 4d-cli-component
description: Maintain the openid 4D component facade, async SystemWorker lifecycle, external signed oidc-cli asset adapter, real source/compiled host acceptance and fail-closed release packaging.
---

# openid component maintenance

Read `AGENTS.md`, `README.md`, `template.json`, component class docs and the
relevant scripts/tests before changes. This destination is already initialized:
repository/component/project/catalog/package `openid`, namespace `OpenID`,
external CLI `oidc-cli`. Do not reinitialize or add a native CLI starter.
Deployment is macOS ARM64 plus Windows x64; Intel macOS and Rosetta are
unsupported. Use `macOS-arm64`, never the former `macOS-universal` selector.

The separately maintained upstream owns OIDC discovery, browser, PKCE,
state/nonce, callback, token exchange and validation. This wrapper validates
trusted configuration, transports protocol1 JSON through stdin/stdout, and
owns cancellation/process lifetime. Never move OIDC logic into 4D or add
NetKit/plug-ins. See the upstream protocol/providers/releases documentation.

Use the reviewed external-asset adapter, not the template's native-source
builder. Exact release/version/archive hashes and notarization receipt are
mandatory; an unresolved production pin stops packaging. Explicitly approved
development CI artifacts do not become release pins. Preserve signed bytes
and executable mode; no re-sign/lipo/quarantine-removal/unsigned fallback.

Keep Client/Task UI calls nonblocking. Each attempt uses CALL WORKER with
isolated shared cancellation state and a bounded SystemWorker owned there.
Close stdin, drain streams independently, enforce limits and caller deadline,
validate protocol/normal exit/issuer/token opt-in, reap and KILL WORKER.
Form unload must dispose; process-owner unique-ID checks are supplemental.
Never persist/log raw outputs, authorization URLs or tokens.

Run Python tests and actual tool4d source-host, compile, pack/unpack and
compiled-host checks. All headless projects need dependencies.json before
first open. Use the approved fixed free tool4d download and SHA256 in package
metadata, worktree-local only; no activation, global install or secret access.
Retain compiler provenance, actual native Libraries/CompiledCode,
source-stripped .4DZ, explicit nested ZIP directories and executable modes.
Retest the exact final unpacked ZIP, not the working source folder.

Keep CI and manual main-only Publish workflows; component tags are
prefix-free SemVer while the upstream version remains independent. Outer
signed/notarized/stapled DMG packaging must preserve the CLI signature.
Missing required evidence fails, never downgrades. Do not dispatch publication,
merge, tag or access secret values without separate authorization.

Report actual passed/failed/not_run scope. The generic x86_64 compiler target
is retained for Windows, not Intel macOS support. macOS ARM64 fixtures do not establish Windows 4D,
interactive Auth0/MFA or Dependency Manager installation. Synthetic identity
protocol fixtures are not real-provider E2E or transaction-bound 4D Server login.
