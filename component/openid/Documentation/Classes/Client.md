# Client

`cs.OpenID.Client.new(configuration; target)` snapshots trusted application
configuration. `authenticate()` returns a Task immediately; `version()` also
returns a Task. Neither API waits for the child process on the calling/UI
process. `compiled` reports actual component execution mode for acceptance.

Use `macOS-universal` (or its macOS default) and explicit `Windows-x64`.
The temporary ARM64-only selector is no longer supported. The reviewed native
Intel build-verification exception does not change runtime OIDC configuration,
identity semantics or the nonblocking API.

The wrapper accepts exactly the upstream protocol v1 fields:

| Field | Default / policy |
| --- | --- |
| `issuer`, `client_id` | Required exact trusted issuer and public client |
| `protocol_version` | `1`, other versions rejected |
| `scopes` | `["openid"]`; must include `openid`, no `offline_access` |
| `listen_address` | `127.0.0.1:0`; numeric IPv4 `127/8` or `[::1]`, port 0–65535 |
| `callback_path` | `/callback`; simple absolute path, no `//` or `/.` segments |
| `timeout_seconds` | 180; 0 means default; integer 1–900 |
| `http_timeout_seconds` | 15; 0 means default; integer 1–60 |
| `open_browser` | true |
| `allow_insecure_loopback_http` | false; explicit numeric-loopback local test only |
| `include_tokens` | false; explicit sensitive in-memory output opt-in |
| `parent_pid` | Optional integer 0–2147483647; CLI OS-parent monitoring only |

Unknown fields (including `client_secret`) and null/wrongly typed settings
fail before launch. The wrapper intentionally restricts IPv6 spellings to
`[::1]`; the CLI further validates numeric IPs, issuer syntax, public-client
settings and all discovery endpoints. It never relaxes TLS verification.
Configuration is JSON on stdin, not argv. Caller deadline is CLI timeout +5
seconds (10 seconds for `version`), followed by at most 2 seconds of cleanup.
The deadline starts before launch, not after successful input.

Default success: `{"ok":true,"identity":{"issuer":"...","subject":"..."}}`.
Only `include_tokens:true` allows `tokens` with `id_token`, `access_token`,
`token_type`, `expires_at`. Tokens are never necessary for identity-only use.
Do not serialize/log/store a token-bearing Task/result. No refresh token,
secret or cache is accepted. `expires_at` is not a validity guarantee; the
upstream zero-time representation means missing access-token expiry.

`version` success is `{"ok":true,"version":"<upstream CLI version>"}`.
Acquisition checks the exact reviewed upstream version; component versions do
not rewrite the CLI's version.

Failures are `{"ok":false,"error":{"code":"...","message":"..."}}`, optionally
with a CLI failure exit code. Messages are wrapper-owned sanitized constants.
Raw stdout, stderr, provider messages, authorization URLs, tokens and local
4D exception details are never included in the result. Error codes distinguish
invalid configuration, launch/resource/platform failure, cancellation, owner
loss, caller timeout, process/cleanup errors, output limits, malformed protocol,
protocol version, exit mismatch and upstream operation failures. CLI error
codes must match exit status 2/3/4/5/10; success requires normal exit zero.
An execution context without a live, uniquely identified 4D owner returns
`unsupported_context`; ownership checks are never silently disabled.

Each stdout response must be one newline-terminated UTF-8 JSON object, at most
262144 bytes. Embedded newlines, replacement characters, malformed types,
unsupported protocol versions, issuer mismatch and unsolicited tokens are
rejected. Stderr is separately drained/bounded to 65536 bytes, not equated
with failure. In headless mode the sole supported authorization event is
available in memory through Task.takeAuthorizationURL(); no stderr is logged.
Exception-free JSON syntax preflight rejects duplicate keys, invalid escapes,
unpaired surrogate escapes and excessive nesting before invoking the 4D JSON
decoder: native parser diagnostics must not echo malformed credential-bearing
text. Optional numeric response values are conservatively bounded to 15 integer
digits, 15 fractional digits and a two-digit exponent; the defined CLI v1
response uses only the integer protocol version and text-valued token fields.
