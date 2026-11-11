// Preflight without parser exceptions: 4D diagnostics must not echo malformed credentials.
property source : Text
property position : Integer
property size : Integer

Function valid($source : Text)->$valid : Boolean
	This.source:=$source
	This.position:=1
	This.size:=Length($source)
	$valid:=This.value(0)
	This.whitespace()
	$valid:=$valid & (This.position>This.size)
	This.source:=""

Function whitespace()
	While (This.position<=This.size)
		If (Position(Substring(This.source; This.position; 1); " \t\r\n"; *)=0)
			return
		End if
		This.position+=1
	End while

Function value($depth : Integer)->$valid : Boolean
	var $character; $literal; $number : Text
	var $start : Integer
	If ($depth>32)
		return False
	End if
	This.whitespace()
	If (This.position>This.size)
		return False
	End if
	$character:=Substring(This.source; This.position; 1)
	Case of
		: ($character="{")
			return This.object($depth+1)
		: ($character="[")
			return This.array($depth+1)
		: ($character="\"")
			return This.string()
		: (Position($character; "tfn"; *)>0)
			$literal:="null"
			If (Character code($character)=116)
				$literal:="true"
			End if
			If (Character code($character)=102)
				$literal:="false"
			End if
			If (Not(cs._Text.new().equal(Substring(This.source; This.position; Length($literal)); $literal)))
				return False
			End if
			This.position+=Length($literal)
			return True
		Else
			$start:=This.position
			While (This.position<=This.size)
				$character:=Substring(This.source; This.position; 1)
				If (Position($character; "0123456789eE+.-"; *)=0)
					break
				End if
				This.position+=1
			End while
			$number:=Substring(This.source; $start; This.position-$start)
			return Match regex("^-?(0|[1-9][0-9]{0,14})(\\.[0-9]{1,15})?([eE][+-]?[0-9]{1,2})?$"; $number)
	End case

Function object($depth : Integer)->$valid : Boolean
	var $keys : Collection
	var $start : Integer
	var $key; $character : Text
	$keys:=New collection
	This.position+=1
	This.whitespace()
	If (Substring(This.source; This.position; 1)="}")
		This.position+=1
		return True
	End if
	Repeat
		$start:=This.position
		If (Not(This.string()))
			return False
		End if
		$key:=JSON Parse(Substring(This.source; $start; This.position-$start); Is text)
		If (cs._Text.new().includes($keys; $key))
			return False
		End if
		$keys.push($key)
		This.whitespace()
		If (Substring(This.source; This.position; 1)#":")
			return False
		End if
		This.position+=1
		If (Not(This.value($depth)))
			return False
		End if
		This.whitespace()
		$character:=Substring(This.source; This.position; 1)
		This.position+=1
		If ($character="}")
			return True
		End if
		If ($character#",")
			return False
		End if
		This.whitespace()
	Until (This.position>This.size)
	$valid:=False

Function array($depth : Integer)->$valid : Boolean
	var $character : Text
	This.position+=1
	This.whitespace()
	If (Substring(This.source; This.position; 1)="]")
		This.position+=1
		return True
	End if
	Repeat
		If (Not(This.value($depth)))
			return False
		End if
		This.whitespace()
		$character:=Substring(This.source; This.position; 1)
		This.position+=1
		If ($character="]")
			return True
		End if
		If ($character#",")
			return False
		End if
	Until (This.position>This.size)
	$valid:=False

Function hexUnit()->$value : Integer
	var $text; $character : Text
	var $index; $digit : Integer
	$text:=Uppercase(Substring(This.source; This.position; 4))
	If (Length($text)#4)
		return -1
	End if
	$value:=0
	For ($index; 1; 4)
		$character:=Substring($text; $index; 1)
		$digit:=Position($character; "0123456789ABCDEF"; *)-1
		If ($digit<0)
			return -1
		End if
		$value:=($value*16)+$digit
	End for
	This.position+=4

Function string()->$valid : Boolean
	var $character : Text
	var $unit; $low : Integer
	If (Substring(This.source; This.position; 1)#"\"")
		return False
	End if
	This.position+=1
	While (This.position<=This.size)
		$character:=Substring(This.source; This.position; 1)
		This.position+=1
		Case of
			: ($character="\"")
				return True
			: (Character code($character)<32)
				return False
			: ($character="\\")
				$character:=Substring(This.source; This.position; 1)
				This.position+=1
				If (Character code($character)=117)
					$unit:=This.hexUnit()
					If ($unit<0)
						return False
					End if
					Case of
						: (($unit>=55296) & ($unit<=56319))
							If (Not(cs._Text.new().equal(Substring(This.source; This.position; 2); "\\u")))
								return False
							End if
							This.position+=2
							$low:=This.hexUnit()
							If (($low<56320) | ($low>57343))
								return False
							End if
						: (($unit>=56320) & ($unit<=57343))
							return False
					End case
				Else
					If (($character="") | (Position($character; "\"\\/bfnrt"; *)=0))
						return False
					End if
				End if
		End case
	End while
	$valid:=False
