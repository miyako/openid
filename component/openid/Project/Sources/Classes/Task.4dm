property _state : Object
property _owner : Integer
property _workerName : Text

Class constructor($configuration : Object; $target : Text; $command : Text)
	var $checked; $owner : Object
	var $previous : Text
	var CLI_LastErrors : Collection
	This._owner:=Current process
	This._workerName:="OpenID-"+Generate UUID
	This._state:=New shared object("done"; False; "cancelled"; False; "disposed"; False; "authorizationURL"; "")
	$checked:=cs._Config.new().validate($configuration; $command)
	If (Not($checked.ok))
		Use (This._state)
			This._state.result:=OB Copy($checked; ck shared; This._state)
			This._state.done:=True
		End use
		return
	End if
	$owner:=cs._Owner.new().info(This._owner)
	If ($owner=Null)
		Use (This._state)
			This._state.result:=OB Copy(New object("ok"; False; "error"; New object("code"; "unsupported_context"; "message"; "A live 4D process with unique owner metadata is required")); ck shared; This._state)
			This._state.done:=True
		End use
		return
	End if
	$previous:=Method called on error(ek local)
	CLI_LastErrors:=Null
	ON ERR CALL("_CaptureError"; ek local)
	CALL WORKER(This._workerName; Formula(cs._Run.new().run($1; $2; $3; $4; $5)); This._state; $checked.value; $target; $command; $owner)
	ON ERR CALL($previous; ek local)
	If (CLI_LastErrors#Null)
		Use (This._state)
			This._state.result:=OB Copy(New object("ok"; False; "error"; New object("code"; "worker_error"; "message"; "Could not schedule authentication worker")); ck shared; This._state)
			This._state.done:=True
		End use
	End if
	CLI_LastErrors:=Null

Function get done()->$done : Boolean
	$done:=This._state.done

Function cancel()
	Use (This._state)
		If (Not(This._state.done))
			This._state.cancelled:=True
		End if
	End use

Function result()->$result : Object
	If (This._state.done)
		$result:=OB Copy(This._state.result)
	Else
		$result:=New object("ok"; False; "error"; New object("code"; "pending"; "message"; "Authentication has not completed"))
	End if

Function takeAuthorizationURL()->$url : Text
	Use (This._state)
		$url:=This._state.authorizationURL
		This._state.authorizationURL:=""
	End use

Function dispose()
	This.cancel()
	Use (This._state)
		This._state.disposed:=True
		This._state.authorizationURL:=""
		If (This._state.done)
			This._state.result:=OB Copy(New object("ok"; False; "error"; New object("code"; "disposed"; "message"; "Task result was discarded")); ck shared; This._state)
		End if
	End use
