# openid

Real 4D wrapper component for asynchronous desktop OpenID Connect, using the
separately maintained [miyako/oidc-cli](https://github.com/miyako/oidc-cli).
Namespace **OpenID**, public classes **Client** and **Task**. No NetKit, native
4D plug-in, embedded OIDC implementation, client secret, token cache, refresh
persistence or provider logout.

**Development candidate, not release-ready.** A reviewed signed/notarized
published CLI release pin is required before distribution. Existing unsigned
`v0.1.0` / `v0.1.0-rc.2` assets are not acceptable substitutes. No runtime
download, PATH lookup, quarantine removal or unsigned fallback is performed.
Upstream [redistribution licensing/notices](docs/redistribution.md) also require
review before release.

## Desktop API

Set application-controlled trust configuration, not an issuer supplied by an
untrusted caller. Preserve the issuer exactly, including its trailing slash.

```4d
// Form initialization
Form.oidc:=cs.OpenID.Client.new(New object(\
    "issuer"; "https://YOUR-TENANT.auth0.com/"; \
    "client_id"; "YOUR_PUBLIC_CLIENT_ID"; \
    "listen_address"; "127.0.0.1:42813"); "macOS-universal")

// Login button: returns immediately; no UI wait()
Form.login:=Form.oidc.authenticate()
SET TIMER(6)

// On Timer
If (Form.login#Null)
    If (Form.login.done)
        Form.loginResult:=Form.login.result()
        Form.login.dispose()
        Form.login:=Null
        SET TIMER(0)
        // Use loginResult.identity.issuer + identity.subject, not email.
        // Do not write loginResult to logs, especially with tokens enabled.
    End if
End if

// Cancel button / On Unload (do not KILL WORKER yourself)
If (Form.login#Null)
    Form.login.cancel()
    Form.login.dispose()
End if
```

Select `"Windows-x64"` explicitly on Windows. Windows ARM64 is unsupported.
macOS resources contain a signed universal executable; do not lipo or re-sign it.
See [Client](component/openid/Documentation/Classes/Client.md) and
[Task](component/openid/Documentation/Classes/Task.md).

`authenticate()` and `version()` return independent Tasks. Each attempt owns a
uniquely named cooperative 4D worker, SystemWorker and in-memory result.
Only that dedicated worker performs short bounded waits. It sends UTF-8 JSON
on stdin, closes input, independently handles stdout/stderr callbacks, bounds
both streams, checks normal termination/exit/protocol and kills its worker
after cleanup. Cancellation uses shared state, not a queued message behind a
blocking authentication call. Owner-process unique ID and caller deadline
checks supplement the CLI timeout. The UI polls completion; there is no
required host callback that can silently fail to arrive.

**Identity JSON is a local observation, not 4D Server authentication.** Neither
this result nor an arbitrary signed ID token implements transaction-bound
Client/Server login, replaces native 4D login, or authorizes another resource.
Server authentication needs a separate server-controlled challenge/nonce,
audience/issuer/replay/session-binding design.

## Build and validation

This repository deliberately adapts the
[component template](https://github.com/miyako/4d-component-template)'s native
starter pipeline for a **pinned external binary dependency**. It does not build
or version the CLI. Component SemVer tags are prefix-free (`0.1.0`); the
independently versioned upstream CLI retains its own tag convention.

Install the component in a host's `Components/openid.4dbase` or, once an
accepted release exists, through Dependency Manager. The source project is
`component/openid/Project/openid.4DProject`. Every headless project includes
`dependencies.json` before first open to avoid import dialogs.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/generate_icons.py --check
# Requires approved, checksum-pinned local tool4d and acquired CLI resources:
python3 scripts/test_4d.py --root . --tool4d .tools/tool4d.app/Contents/MacOS/tool4d
python3 scripts/compile_component.py --root . --tool4d .tools/tool4d.app/Contents/MacOS/tool4d
```

Packaging retains the template's actual compiler outputs, source stripping,
explicit ZIP directories, executable modes and exact unpacked compiled-host
gate. Distribution must preserve the CLI signature and use the supported
signed/notarized/stapled outer DMG path; a bare CLI cannot be stapled.
Missing pins, receipts, hashes, compiler output or host evidence must fail
closed. No tag, release or merge is authorized by implementation/CI.

See [acceptance](docs/acceptance.md), [provider setup](docs/providers.md) and the
upstream [protocol](https://github.com/miyako/oidc-cli/blob/main/docs/protocol.md).

Local macOS ARM64 tool4d 20.7/101905 executed the source and unpacked compiled
development component, including real async version, active cancellation,
CLI timeout, owner exit and zero leaked workers. Both compiler targets passed.
This uses the approved, independently verified signed/notarized **CI artifact**,
not a published release pin. It does not establish Intel/Windows 4D execution,
normal IDE UI responsiveness, Auth0/browser/MFA or downloaded-release acceptance.
