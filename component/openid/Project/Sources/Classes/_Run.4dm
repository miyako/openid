property dataType : Text
property encoding : Text
property hideWindow : Boolean
property timeout : Integer
property currentDirectory : 4D.Folder
property state : Object
property configuration : Object
property worker : 4D.SystemWorker
property output : Text
property diagnostic : Text
property outputBytes : Real
property diagnosticBytes : Real
property failure : Text
property command : Text
property owner : Object
property started : Real

Class constructor
	This.dataType:="text"
	This.encoding:="UTF-8"
	This.hideWindow:=True
	This.output:=""
	This.diagnostic:=""
	This.outputBytes:=0
	This.diagnosticBytes:=0
	This.failure:=""

Function run($state : Object; $configuration : Object; $target : Text; $command : Text; $owner : Object)
	var $resolved; $result : Object
	var $previous : Text
	var $start; $elapsed : Real
	var CLI_LastErrors : Collection
	var OpenID_ActiveRun : cs._Run
	This.state:=$state
	This.configuration:=$configuration
	This.command:=$command
	This.owner:=$owner
	OpenID_ActiveRun:=This
	ON ERR CALL("_RunError"; ek local)
	This.timeout:=10
	If ($command="authenticate")
		This.timeout:=$configuration.timeout_seconds+5
	End if
	$start:=Milliseconds
	This.started:=$start
	If ($state.cancelled)
		This.finish(cs._Protocol.new().failure("cancelled"))
		KILL WORKER
		return
	End if
	If (Not(cs._Owner.new().alive($owner)))
		This.finish(cs._Protocol.new().failure("owner_gone"))
		KILL WORKER
		return
	End if
	$resolved:=cs._CLI.new("oidc-cli"; $target).resolve()
	If (Not($resolved.ok))
		This.finish(cs._Protocol.new().failure($resolved.error.code))
		KILL WORKER
		return
	End if
	This.currentDirectory:=$resolved.file.parent
	$previous:=Method called on error(ek local)
	CLI_LastErrors:=Null
	ON ERR CALL("_CaptureError"; ek local)
	This.worker:=4D.SystemWorker.new(cs._Process.new().quote($resolved.file.path)+" "+$command; This)
	If (This.worker#Null)
		If ($command="authenticate")
			This.worker.postMessage(JSON Stringify($configuration))
		End if
		This.worker.closeInput()
		Use (This.state)
			This.state.pid:=This.worker.pid
		End use
	End if
	ON ERR CALL($previous; ek local)
	If ((CLI_LastErrors#Null) | (This.worker=Null))
		CLI_LastErrors:=Null
		This.failure:="launch_failed"
	Else
		Repeat
			$previous:=Method called on error(ek local)
			CLI_LastErrors:=Null
			ON ERR CALL("_CaptureError"; ek local)
			This.worker.wait(0.05)
			ON ERR CALL($previous; ek local)
			If (CLI_LastErrors#Null)
				CLI_LastErrors:=Null
				This.failure:="worker_error"
			End if
			$elapsed:=Milliseconds-$start
			If ($elapsed<0)
				$elapsed+=4294967296
			End if
			Case of
				: ($state.cancelled)
					This.failure:="cancelled"
				: (Not(cs._Owner.new().alive($owner)))
					This.failure:="owner_gone"
				: ($elapsed>=(This.timeout*1000))
					This.failure:="caller_timeout"
			End case
		Until ((This.failure#"") | This.worker.terminated)
	End if
	If (This.failure#"")
		If (This.worker#Null)
			$previous:=Method called on error(ek local)
			CLI_LastErrors:=Null
			ON ERR CALL("_CaptureError"; ek local)
			This.worker.terminate()
			This.worker.wait(2)
			ON ERR CALL($previous; ek local)
			If ((CLI_LastErrors#Null) | (Not(This.worker.terminated)))
				This.failure:="cleanup_failed"
			End if
			CLI_LastErrors:=Null
		End if
		$result:=cs._Protocol.new().failure(This.failure)
	Else
		$result:=cs._Protocol.new().decode(This.output; This.worker.exitCode; $command; $configuration)
	End if
	This.finish($result)
	This.worker:=Null
	This.configuration:=Null
	This.output:=""
	This.diagnostic:=""
	OpenID_ActiveRun:=Null
	ON ERR CALL(""; ek local)
	KILL WORKER

Function onData($worker : Object; $event : Object)
	var $bytes : Blob
	CONVERT FROM TEXT($event.data; "UTF-8"; $bytes)
	This.outputBytes+=BLOB size($bytes)
	If (This.outputBytes>262144)
		This.failure:="output_limit"
		$worker.terminate()
	Else
		This.output+=$event.data
	End if

Function onDataError($worker : Object; $event : Object)
	var $bytes : Blob
	var $line : Text
	var $payload : Variant
	var $previous : Text
	var $end : Integer
	var CLI_LastErrors : Collection
	CONVERT FROM TEXT($event.data; "UTF-8"; $bytes)
	This.diagnosticBytes+=BLOB size($bytes)
	If (This.diagnosticBytes>65536)
		This.failure:="diagnostic_limit"
		$worker.terminate()
		return
	End if
	If (This.command="authenticate")
		If (Not(This.configuration.open_browser))
			This.diagnostic+=$event.data
			$end:=Position(Char(10); This.diagnostic; *)
			While ($end>0)
				$line:=Substring(This.diagnostic; 1; $end-1)
				This.diagnostic:=Substring(This.diagnostic; $end+1)
				$previous:=Method called on error(ek local)
				CLI_LastErrors:=Null
				ON ERR CALL("_CaptureError"; ek local)
				$payload:=Null
				If (cs._JSON.new().valid($line))
					$payload:=JSON Parse($line)
				End if
				ON ERR CALL($previous; ek local)
				If (CLI_LastErrors=Null)
					If (Value type($payload)=Is object)
						If ($payload#Null)
							If ((Value type($payload.protocol_version)=Is real) | (Value type($payload.protocol_version)=Is longint))
								If ($payload.protocol_version=1)
									If ($payload.event="authorization_required")
										If (Value type($payload.authorization_url)=Is text)
											Use (This.state)
												If (Not(This.state.cancelled | This.state.disposed))
													This.state.authorizationURL:=$payload.authorization_url
												End if
											End use
										End if
									End if
								End if
							End if
						End if
					End if
				End if
				CLI_LastErrors:=Null
				$end:=Position(Char(10); This.diagnostic; *)
			End while
		End if
	End if

Function onError($worker : Object; $event : Object)
	This.failure:="process_error"

Function finish($result : Object)
	var $elapsed : Real
	$elapsed:=Milliseconds-This.started
	If ($elapsed<0)
		$elapsed+=4294967296
	End if
	Use (This.state)
		If (Not(This.state.done))
			This.state.authorizationURL:=""
			If (This.failure="cleanup_failed")
				This.state.result:=OB Copy(cs._Protocol.new().failure("cleanup_failed"); ck shared; This.state)
			Else
				If (This.state.disposed)
					This.state.result:=OB Copy(cs._Protocol.new().failure("disposed"); ck shared; This.state)
				Else
					Case of
						: (This.state.cancelled)
							$result:=cs._Protocol.new().failure("cancelled")
						: ($elapsed>=(This.timeout*1000))
							$result:=cs._Protocol.new().failure("caller_timeout")
						: (Not(cs._Owner.new().alive(This.owner)))
							$result:=cs._Protocol.new().failure("owner_gone")
					End case
					This.state.result:=OB Copy($result; ck shared; This.state)
				End if
			End if
			This.state.done:=True
		End if
	End use

Function emergency()
	var $previous : Text
	var CLI_LastErrors : Collection
	$previous:=Method called on error(ek local)
	CLI_LastErrors:=Null
	ON ERR CALL("_CaptureError"; ek local)
	This.failure:="worker_error"
	If (This.worker#Null)
		This.worker.terminate()
		This.worker.wait(2)
		If (Not(This.worker.terminated))
			This.failure:="cleanup_failed"
		End if
	End if
	If (CLI_LastErrors#Null)
		This.failure:="cleanup_failed"
	End if
	CLI_LastErrors:=Null
	This.finish(cs._Protocol.new().failure("worker_error"))
	This.output:=""
	This.diagnostic:=""
	This.configuration:=Null
	ON ERR CALL($previous; ek local)
