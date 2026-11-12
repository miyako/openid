Function equal($left : Text; $right : Text)->$equal : Boolean
	If (Length($left)#Length($right))
		return False
	End if
	If (Length($left)=0)
		return True
	End if
	$equal:=(Position($left; $right; *)=1)

Function includes($values : Collection; $text : Text)->$found : Boolean
	var $value : Text
	For each ($value; $values)
		If (This.equal($value; $text))
			return True
		End if
	End for each
	$found:=False
