# Provider setup and interactive acceptance

The application selects a trusted exact issuer and a public/native client.
Do not accept an issuer from an arbitrary login form or an untrusted server.
Keep the provider's trailing slash exactly; discovery must match it.

## Auth0 (planned first hosted interactive provider)

Create your own tenant and **Native** application, public authorization-code
client with S256 PKCE, token endpoint authentication **None**, and **RS256**
ID-token signing. Register exactly
`http://127.0.0.1:42813/callback` as an allowed callback URL, create/authorize a
test user, and supply the tenant issuer and public client ID in host code.
Use `listen_address:"127.0.0.1:42813"` and `callback_path:"/callback"`.
Do not fabricate a tenant, reuse unrelated credentials, or add a client secret.

On a native macOS ARM64 or Windows x64 4D desktop host, confirm UI responsiveness during browser login and
MFA, success identity issuer+subject, repeated login, cancellation before and
after browser opening, form unload, host-process exit, occupied callback port,
wrong state/path/issuer, timeout, provider denial and offline/JWKS errors.
Confirm no sensitive output is written to host logs, status reports or disk.
Tokens require a separate explicit opt-in test and protected handling.

**No real Auth0 tenant/user credentials were supplied. Auth0, interactive
browser/MFA and normal IDE/4D Server acceptance remain unverified.** This
component does not implement native 4D Client/Server authentication.

## Disposable local provider

The standalone CLI's hosted Keycloak E2E passed in
[run 43034430810](https://github.com/miyako/oidc-cli/actions/runs/43034430810),
covering real provider callback/JWKS/identity/token validation. That is upstream
CLI evidence, not this wrapper's 4D host evidence.

For deliberately local tests only, numeric-loopback HTTP issuers require
`allow_insecure_loopback_http:true`. It never enables arbitrary HTTP endpoints
or insecure TLS. The upstream disposable fixture uses an exact-origin
loopback Secure-cookie policy because a normal Python jar otherwise causes
`Cookie not found`; do not generalize that test-only relaxation to production.
