# _CLI (internal convention)

Internal resource resolver. `resolve()` returns `{ok:true,file:4D.File}` or a
prelaunch error. Client/Task use the asynchronous `_Run` lifecycle; the generic
`execute()` helper is synchronous and is used only for bounded version/argument
acceptance probes, never interactive authentication.

`cs._CLI.new(executableName : Text; target : Text)` is the reusable bundled
executable resolver. The host can technically access `cs.OpenID._CLI`;
underscore naming is not true private access in 4D.

This resolves a standalone CLI for separate-process execution, not a native
4D plug-in. A plug-in must be installed in the host; this resolver and component
packaging cannot privately load/deploy it or satisfy that installation requirement.

`execute(arguments : Collection) : Object` selects `/RESOURCES/bin/macOS/<name>`
or `/RESOURCES/bin/Windows/<name>.exe`, checks existence, expands the virtual
File to a physical path using `File(file.platformPath; fk platform path)`, then
delegates to `_Process`. There is deliberately no PATH search, permission repair,
shell, download, copied PDF algorithm or queue.

macOS default/`macOS-arm64` uses the pinned ARM64-only executable. Intel macOS,
Rosetta and the former `macOS-universal` selector are explicitly unsupported.
The resolver checks `/usr/bin/uname -m` using a one-second-bounded SystemWorker;
only successful exact `arm64` output with no stderr is accepted. Intel/Rosetta,
failed probes and malformed output fail closed. It does not infer architecture
from CPU marketing names or missing `System info` fields. If the documented
`System info.macRosetta` flag is present and true, it also rejects that context.
Client/Task resolve inside their dedicated worker, never on the calling/UI
process. Internal synchronous `resolve()`/`execute()` are not UI APIs.
`supportsMacOS()` is a pure compatibility predicate used by fixtures;
`resolve()` always runs the actual host probe, never caller-supplied metadata.
Windows requires explicit `Windows-x64`. Unknown selection or OS returns an explicit error;
Windows ARM64 native execution is not implemented. See [Client](Client.md)
for the common result/error shape.

The read-only `compiled` Boolean evaluates `Is compiled mode` inside the
component. The release host fixture uses it to reject an interpreted fallback.
