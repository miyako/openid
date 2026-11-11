property _configuration : Object
property _target : Text

Class constructor($configuration : Object; $target : Text)
	This._configuration:=OB Copy($configuration)
	This._target:=$target

Function authenticate()->$task : cs.Task
	$task:=cs.Task.new(This._configuration; This._target; "authenticate")

Function version()->$task : cs.Task
	$task:=cs.Task.new(New object; This._target; "version")

Function get compiled()->$compiled : Boolean
	$compiled:=Is compiled mode
