//%attributes = {"invisible":true}
var OpenID_ActiveRun : cs._Run
If (OpenID_ActiveRun#Null)
	OpenID_ActiveRun.emergency()
End if
KILL WORKER
ABORT
