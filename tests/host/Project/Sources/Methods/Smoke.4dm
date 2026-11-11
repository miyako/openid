//%attributes = {"invisible":true}
var $ignored : Integer
var $parameter; $target; $text : Text
var $request; $report; $result; $configuration; $checked; $decoded : Object
var $tool : cs.OpenID.Client
var $task : cs.OpenID.Task
var $requestFile; $statusFile; $executable : 4D.File
var $invalid : Variant
var $probe; $activity; $process : Object
var $start; $elapsed : Real
var $index : Integer
var $run : cs.OpenID._Run
var $sink : cs.Probe
var $workers : Collection
var $ownerWorker : Text
var HOST_StatusFile : 4D.File
var HOST_Phase; HOST_PreviousHandler : Text
$ignored:=Get database parameter(User param value; $parameter)
If (Is Windows)
	$requestFile:=File($parameter; fk platform path)
Else
	$requestFile:=File($parameter; fk posix path)
End if
$request:=JSON Parse($requestFile.getText())
If (Is Windows)
	$statusFile:=File($request.status; fk platform path)
	$executable:=File($request.executable; fk platform path)
Else
	$statusFile:=File($request.status; fk posix path)
	$executable:=File($request.executable; fk posix path)
End if
HOST_StatusFile:=$statusFile
HOST_Phase:="starting"
HOST_PreviousHandler:=Method called on error(ek local)
ON ERR CALL("Host_error"; ek local)
$target:="macOS-arm64"
If (Is Windows)
	$target:="Windows-x64"
End if
$configuration:=New object("issuer"; "https://issuer.example"; "client_id"; "public-client")
$statusFile.setText("{\"phase\":\"client-constructor\",\"success\":false,\"finished\":false}")
$tool:=cs.OpenID.Client.new($configuration; $target)
$report:=New object("success"; True; "finished"; False; "compiled"; $tool.compiled; "cases"; New collection)
$report.macOSArchitectureGuard:=New collection(\
	cs.OpenID._CLI.new("oidc-cli"; $target).supportsMacOS(New object("ok"; True; "exitCode"; 0; "stdout"; "arm64\n"; "stderr"; "")); \
	Not(cs.OpenID._CLI.new("oidc-cli"; $target).supportsMacOS(New object("ok"; True; "exitCode"; 0; "stdout"; "x86_64\n"; "stderr"; ""))); \
	Not(cs.OpenID._CLI.new("oidc-cli"; $target).supportsMacOS(New object("ok"; False; "exitCode"; 1; "stdout"; "arm64\n"; "stderr"; ""))); \
	Not(cs.OpenID._CLI.new("oidc-cli"; $target).supportsMacOS(New object)); \
	Not(cs.OpenID._CLI.new("oidc-cli"; $target).supportsMacOS(New object("ok"; True; "exitCode"; 0; "stdout"; "arm64\n"; "stderr"; "unexpected"))))
$report.legacyMacOSTarget:=cs.OpenID._CLI.new("oidc-cli"; "macOS-universal").resolve()
HOST_Phase:="native renamed executable"
$report.renamedExecutable:=cs.OpenID._Process.new().execute($executable; New collection("version"))
HOST_Phase:="asynchronous version"
$workers:=New collection
$statusFile.setText("{\"phase\":\"version-start\",\"success\":false,\"finished\":false}")
$task:=$tool.version()
$workers.push($task._workerName)
$report.version:=AwaitTask($task; 15)
$report.nativeVersion:=cs.OpenID._Protocol.new().decode($report.renamedExecutable.stdout; $report.renamedExecutable.exitCode; "version"; New object)
$report.asyncDesktopStatus:="not_run"
$report.asyncDesktopReason:="host has no stable process-owner metadata"
$report.ownerSnapshot:=cs.OpenID._Owner.new().info(Current process)
If ($report.ownerSnapshot#Null)
	$report.asyncDesktopStatus:="passed"
	$report.asyncDesktopReason:=""
	$report.ownerSnapshotVerified:=($report.ownerSnapshot.number>0) & ($report.ownerSnapshot.ID>0)
End if
HOST_Phase:="identity decoding (synthetic, not provider authentication)"
$text:="{\"protocol_version\":1,\"ok\":true,\"identity\":{\"issuer\":\"https://issuer.example\",\"subject\":\"opaque-subject\"}}\n"
$decoded:=cs.OpenID._Protocol.new().decode($text; 0; "authenticate"; New object("issuer"; "https://issuer.example"; "include_tokens"; False))
$report.cases.push(New object("ok"; $decoded.ok; "stdout"; $text; "stderr"; ""; "exitCode"; 0; "value"; $decoded))
$report.unicodeIdentity:=cs.OpenID._Protocol.new().decode("{\"protocol_version\":1,\"ok\":true,\"identity\":{\"issuer\":\"https://issuer.example\",\"subject\":\"日本語\"}}\n"; 0; "authenticate"; New object("issuer"; "https://issuer.example"; "include_tokens"; False))
$report.invalidOwnerRejected:=(cs.OpenID._Owner.new().info(-1)=Null)
HOST_Phase:="configuration"
$checked:=cs.OpenID._Config.new().validate($configuration; "authenticate")
$report.configuration:=$checked
$report.invalidConfigurations:=New collection
For each ($invalid; New collection(New object; New object("issuer"; "http://example.com"; "client_id"; "public"); New object("issuer"; "https://issuer.example"; "client_id"; "public"; "client_secret"; "not-allowed"); New object("issuer"; "https://issuer.example"; "client_id"; "public"; "include_tokens"; "true"); New object("issuer"; "https://issuer.example"; "client_id"; "public"; "timeout_seconds"; True); New object("issuer"; "https://issuer.example"; "client_id"; "public"; "scopes"; New collection("offline_access"))))
	$report.invalidConfigurations.push(cs.OpenID._Config.new().validate($invalid; "authenticate"))
End for each
HOST_Phase:="invalid protocol"
$report.invalidProtocols:=New collection
For each ($text; New collection("not json\n"; "null\n"; "true\n"; "[]\n"; "{\"protocol_version\":true,\"ok\":true}\n"; "{\"protocol_version\":2,\"ok\":true}\n"; "{\"protocol_version\":1,\"ok\":true}\n"; "{\"protocol_version\":1,\"ok\":true}\n{}\n"))
	$report.invalidProtocols.push(cs.OpenID._Protocol.new().decode($text; 0; "authenticate"; $configuration))
End for each
$report.jsonValid:=New collection
For each ($text; New collection("{\"a\":[true,false,null,-0,1.25,1e2,{}]}"; "{\"a\":1,\"A\":2}"; "{\"a\":\"\\uD83D\\uDE00\"}"; "{\"escaped\":\"quote\\\"slash\\\\line\\n\"}"))
	$report.jsonValid.push(cs.OpenID._JSON.new().valid($text))
End for each
$report.jsonInvalid:=New collection
For each ($text; New collection("{\"a\":1,\"\\u0061\":2}"; "{\"a\":\"\\uD800\"}"; "{\"a\":\"\\uDC00\"}"; "{\"a\":\"\\x00\"}"; "{\"a\":01}"; "{\"a\":1,}"; "[1,]"; "{}{}"; "{\"a\":\"fixture-sensitive}"))
	$report.jsonInvalid.push(cs.OpenID._JSON.new().valid($text))
End for each
$report.malformedSensitive:=cs.OpenID._Protocol.new().decode("{\"protocol_version\":1,\"ok\":true,\"identity\":{\"subject\":\"fixture-sensitive}\n"; 0; "authenticate"; $configuration)
$report.issuerCaseMismatch:=cs.OpenID._Protocol.new().decode("{\"protocol_version\":1,\"ok\":true,\"identity\":{\"issuer\":\"https://ISSUER.example\",\"subject\":\"opaque\"}}\n"; 0; "authenticate"; New object("issuer"; "https://issuer.example"; "include_tokens"; False))
$report.configurationCaseMismatch:=cs.OpenID._Config.new().validate(New object("issuer"; "https://issuer.example"; "client_id"; "public"; "Open_browser"; False); "authenticate")
$report.exitMismatch:=cs.OpenID._Protocol.new().decode("{\"protocol_version\":1,\"ok\":true,\"version\":\"0.1.0\"}\n"; 3; "version"; New object)
$report.nonzero:=cs.OpenID._Protocol.new().decode("{\"protocol_version\":1,\"ok\":false,\"error\":{\"code\":\"invalid_input\",\"message\":\"constant\"}}\n"; 2; "authenticate"; $configuration)
$report.tokenRejection:=cs.OpenID._Protocol.new().decode("{\"protocol_version\":1,\"ok\":true,\"identity\":{\"issuer\":\"https://issuer.example\",\"subject\":\"opaque\"},\"tokens\":{}}\n"; 0; "authenticate"; New object("issuer"; "https://issuer.example"; "include_tokens"; False))
HOST_Phase:="token opt-in and sanitized errors"
$report.tokenOptIn:=cs.OpenID._Protocol.new().decode("{\"protocol_version\":1,\"ok\":true,\"identity\":{\"issuer\":\"https://issuer.example\",\"subject\":\"opaque\"},\"tokens\":{\"id_token\":\"fixture-id\",\"access_token\":\"fixture-access\",\"token_type\":\"Bearer\",\"expires_at\":\"0001-01-01T00:00:00Z\"}}\n"; 0; "authenticate"; New object("issuer"; "https://issuer.example"; "include_tokens"; True))
// Verify sensitive values in memory, then discard before writing any report.
$report.tokenOptInVerified:=($report.tokenOptIn.tokens.id_token="fixture-id") & ($report.tokenOptIn.tokens.access_token="fixture-access")
OB REMOVE($report; "tokenOptIn")
$report.sanitizedFailure:=cs.OpenID._Protocol.new().decode("{\"protocol_version\":1,\"ok\":false,\"error\":{\"code\":\"oauth_error\",\"message\":\"credential-bearing-provider-message\"}}\n"; 3; "authenticate"; $configuration)
HOST_Phase:="stream boundaries"
$text:="x"
For ($index; 1; 18)
	$text+=$text
End for
$run:=cs.OpenID._Run.new()
$sink:=cs.Probe.new()
$run.onData($sink; New object("data"; $text))
$report.stdoutAtLimit:=($run.outputBytes=262144) & (Not($sink.terminated))
$run.onData($sink; New object("data"; "x"))
$report.stdoutOverflow:=($run.failure="output_limit") & $sink.terminated
$report.oversizeProtocol:=cs.OpenID._Protocol.new().decode($text+"x"; 0; "version"; New object)
$run:=cs.OpenID._Run.new()
$run.command:="version"
$sink:=cs.Probe.new()
$run.onDataError($sink; New object("data"; Substring($text; 1; 65536)))
$report.stderrAtLimit:=($run.diagnosticBytes=65536) & (Not($sink.terminated)) & ($run.diagnostic="")
$run.onDataError($sink; New object("data"; "x"))
$report.stderrOverflow:=($run.failure="diagnostic_limit") & $sink.terminated
$run:=cs.OpenID._Run.new()
$run.state:=New shared object("done"; False; "cancelled"; False; "disposed"; False; "authorizationURL"; "")
$run.owner:=cs.OpenID._Owner.new().info(Current process)
$run.started:=Milliseconds-6000
$run.timeout:=6
$run.finish(New object("ok"; True; "version"; "0.1.0"))
$report.callerDeadline:=OB Copy($run.state.result)
$run:=cs.OpenID._Run.new()
$run.state:=New shared object("done"; False; "cancelled"; True; "disposed"; False; "authorizationURL"; "")
$run.owner:=cs.OpenID._Owner.new().info(Current process)
$run.started:=Milliseconds
$run.timeout:=6
$run.finish(New object("ok"; True; "version"; "0.1.0"))
$report.finalGateCancellation:=OB Copy($run.state.result)
$report.abnormalExit:=cs.OpenID._Protocol.new().decode("{\"protocol_version\":1,\"ok\":true,\"version\":\"0.1.0\"}\n"; Null; "version"; New object)
$run:=Null
$text:=""
HOST_Phase:="cancel before launch"
If ($report.ownerSnapshot#Null)
$task:=$tool.authenticate()
$workers.push($task._workerName)
$task.cancel()
$report.cancelled:=AwaitTask($task; 15)
$task.dispose()
$report.disposed:=$task.result()
HOST_Phase:="active cancellation"
$configuration:=New object("issuer"; $request.slowIssuer; "client_id"; "fixture"; "allow_insecure_loopback_http"; True; "timeout_seconds"; 10)
$task:=cs.OpenID.Client.new($configuration; $target).authenticate()
$workers.push($task._workerName)
$start:=Milliseconds
Repeat
	DELAY PROCESS(Current process; 1)
	$elapsed:=Milliseconds-$start
	If ($elapsed<0)
		$elapsed+=4294967296
	End if
Until ((OB Is defined($task._state; "pid")) | ($elapsed>5000))
$report.activeProcessObserved:=False
If (OB Is defined($task._state; "pid"))
	$report.activeProcessObserved:=($task._state.pid>0)
End if
DELAY PROCESS(Current process; 6)
$task.cancel()
$report.activeCancellation:=AwaitTask($task; 5)
HOST_Phase:="CLI deadline"
$configuration.timeout_seconds:=1
$task:=cs.OpenID.Client.new($configuration; $target).authenticate()
$workers.push($task._workerName)
$report.cliTimeout:=AwaitTask($task; 10)
HOST_Phase:="owner process cleanup"
$configuration.timeout_seconds:=10
$probe:=New shared object
$ownerWorker:="OpenID-owner-probe-"+Generate UUID
$workers.push($ownerWorker)
CALL WORKER($ownerWorker; Formula(OwnerProbe($1; $2; $3)); $probe; $configuration; $target)
$start:=Milliseconds
Repeat
	DELAY PROCESS(Current process; 1)
	$elapsed:=Milliseconds-$start
	If ($elapsed<0)
		$elapsed+=4294967296
	End if
Until ((OB Is defined($probe; "state")) | ($elapsed>15000))
If (OB Is defined($probe; "state"))
	$workers.push($probe.workerName)
	Repeat
		DELAY PROCESS(Current process; 1)
		$elapsed:=Milliseconds-$start
		If ($elapsed<0)
			$elapsed+=4294967296
		End if
	Until ($probe.state.done | ($elapsed>15000))
	If ($probe.state.done)
		$report.ownerGone:=OB Copy($probe.state.result)
	End if
End if
DELAY PROCESS(Current process; 6)
$report.leakedWorkers:=0
For each ($text; $workers)
	If (Process number($text)>0)
		$report.leakedWorkers+=1
	End if
End for each
Else
	$report.contextRejection:=$report.version
End if
HOST_Phase:="missing resource"
$report.unsupported:=cs.OpenID._CLI.new("oidc-cli"; "invalid-platform").resolve()
$report.missing:=cs.OpenID._CLI.new("missing-cli"; $target).resolve()
$report.rejectedTimeouts:=New collection
For each ($invalid; New collection(-1; 0; 31))
	$report.rejectedTimeouts.push(cs.OpenID._Process.new().execute($executable; New collection("version"); $invalid))
End for each
HOST_Phase:="generic argument rejection"
$report.rejectedArguments:=New collection
For each ($invalid; New collection(123; 1.25; True; False; Null; Current date; Current time; New collection; New object))
	$report.rejectedArguments.push(cs.OpenID._Process.new().execute($requestFile; New collection($invalid)))
End for each
$report.rejectedNul:=New collection
For each ($text; New collection(Char(0)+"prefix"; "middle"+Char(0)+"suffix"; "trailing"+Char(0)))
	$report.rejectedNul.push(cs.OpenID._Process.new().execute($requestFile; New collection($text)))
End for each
$report.missingFile:=cs.OpenID._Process.new().execute(Null; New collection)
$report.missingArguments:=cs.OpenID._Process.new().execute($requestFile; Null)
$report.launch:=cs.OpenID._Process.new().execute($requestFile; New collection)
$report.finished:=True
ON ERR CALL(HOST_PreviousHandler; ek local)
$statusFile.setText(JSON Stringify($report))
QUIT 4D
