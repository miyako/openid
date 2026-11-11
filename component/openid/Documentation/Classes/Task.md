# Task

Created by `Client.authenticate()` / `Client.version()`; do not construct
internal task state yourself.

| Member | Contract |
| --- | --- |
| `done` | Nonblocking completion Boolean; no implicit process wait |
| `result()` | Copy of final sanitized result; `pending` until done |
| `cancel()` | Idempotent cancellation request via shared state |
| `dispose()` | Cancel, clear sensitive authorization event and discard result |
| `takeAuthorizationURL()` | Read-and-clear in-memory event only with `open_browser:false` |

The owner is the 4D process that created the Task, not a form. On form unload
call `dispose()` explicitly; process-exit monitoring cannot detect a closed
form in a surviving application process. Keep a Task reference until done if
completion matters. Dropping the reference does not itself cancel the worker;
the bounded CLI/caller deadline still applies. Do not KILL WORKER or abort its
process externally: that can skip process cleanup.

`cancel()` observed before final acceptance wins over ready output. Cancellation
after a committed result does not retract it. `dispose()` discards an already
completed result and ensures an active task will not later publish tokens.
Keep any copied token result under the caller's own protected lifecycle.
No promise of secure memory erasure is made for 4D garbage-collected strings.

There is no global task map, queue of cancellation callbacks or permanent
background service. The uniquely named dedicated worker clears its queue with
KILL WORKER after termination/reap. A failed cleanup is reported explicitly,
never as a successful login. Forced host/OS crashes cannot execute language
cleanup; the CLI's finite deadline and optional parent monitor supplement it.

Headless authorization URLs contain state/nonce/PKCE material: display only to
the same user and never persist/log them. Completion/disposal clears an untaken
URL. Automatic browser mode does not retain stderr or an authorization URL.
