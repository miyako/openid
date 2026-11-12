Function info($number : Integer)->$owner : Object
	var $name : Text
	var $state; $ticks; $mode; $id : Integer
	If ($number<1)
		return Null
	End if
	$state:=Does not exist
	$id:=0
	PROCESS PROPERTIES($number; $name; $state; $ticks; $mode; $id)
	If (($state<0) | ($id<1))
		return Null
	End if
	$owner:=New object("number"; $number; "ID"; $id; "state"; $state)

Function alive($original : Object)->$alive : Boolean
	var $current : Object
	If ($original=Null)
		return False
	End if
	$current:=This.info($original.number)
	If ($current=Null)
		return False
	End if
	$alive:=($current.ID=$original.ID) & ($current.state>=0)
