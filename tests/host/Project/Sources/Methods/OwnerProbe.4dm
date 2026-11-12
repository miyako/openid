//%attributes = {"invisible":true}
#DECLARE($probe : Object; $configuration : Object; $target : Text)
var $task : cs.OpenID.Task
$task:=cs.OpenID.Client.new($configuration; $target).authenticate()
Use ($probe)
	$probe.state:=$task._state
	$probe.workerName:=$task._workerName
End use
KILL WORKER
