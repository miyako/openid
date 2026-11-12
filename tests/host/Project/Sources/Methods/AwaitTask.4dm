//%attributes = {"invisible":true}
#DECLARE($task : cs.OpenID.Task; $seconds : Integer)->$result : Object
var $start; $elapsed : Real
$start:=Milliseconds
Repeat
	DELAY PROCESS(Current process; 1)
	$elapsed:=Milliseconds-$start
	If ($elapsed<0)
		$elapsed+=4294967296
	End if
Until ($task.done | ($elapsed>($seconds*1000)))
If (Not($task.done))
	$task.cancel()
	return New object("ok"; False; "error"; New object("code"; "host_fixture_timeout"; "message"; "4D task did not complete in the fixture deadline"))
End if
$result:=$task.result()
