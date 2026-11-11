property executableName : Text
property target : Text

Class constructor($executableName : Text; $target : Text)
	This.executableName:=$executableName
	This.target:=$target

Function get compiled()->$compiled : Boolean
	$compiled:=Is compiled mode

Function supportsMacOS($probe : Object)->$supported : Boolean
	If ($probe=Null)
		return False
	End if
	If ((Value type($probe.ok)#Is boolean) | (Value type($probe.stdout)#Is text) | (Value type($probe.stderr)#Is text))
		return False
	End if
	If ((Value type($probe.exitCode)#Is real) & (Value type($probe.exitCode)#Is longint))
		return False
	End if
	$supported:=$probe.ok & ($probe.exitCode=0) & cs._Text.new().equal($probe.stdout; "arm64\n") & ($probe.stderr="")

Function resolve()->$result : Object
	var $platform; $name : Text
	var $file : 4D.File
	var $architecture; $system : Object
	If (Not(Match regex("^[a-z][a-z0-9-]{0,62}$"; This.executableName)))
		return New object("ok"; False; "error"; New object("code"; "invalid_argument"; "message"; "Executable name must be a CLI basename, not a path"))
	End if
	$name:=This.executableName
	Case of
		: (Is macOS)
			If ((This.target#"") & (Not(cs._Text.new().equal(This.target; "macOS-arm64"))))
				return New object("ok"; False; "error"; New object("code"; "unsupported_architecture"; "message"; "macOS requires macOS-arm64; Intel and universal targets are unsupported"))
			End if
			$system:=System info
			If (Value type($system.macRosetta)=Is boolean)
				If ($system.macRosetta)
					return New object("ok"; False; "error"; New object("code"; "unsupported_architecture"; "message"; "Rosetta execution is unsupported; run native macOS ARM64 4D"))
				End if
			End if
			$architecture:=cs._Process.new().execute(File("/usr/bin/uname"; fk posix path); New collection("-m"); 1)
			If (Not(This.supportsMacOS($architecture)))
				return New object("ok"; False; "error"; New object("code"; "unsupported_architecture"; "message"; "Native macOS ARM64 could not be verified; Intel and Rosetta are unsupported"))
			End if
			$platform:="macOS"
		: (Is Windows)
			If (This.target#"Windows-x64")
				return New object("ok"; False; "error"; New object("code"; "unsupported_architecture"; "message"; "Explicit Windows-x64 selection is required; native Windows ARM64 is not supported"))
			End if
			$platform:="Windows"
			$name+=".exe"
		Else
			return New object("ok"; False; "error"; New object("code"; "unsupported_platform"; "message"; "Only macOS and Windows are supported"))
	End case
	$file:=Folder("/RESOURCES").folder("bin").folder($platform).file($name)
	If (Not($file.exists))
		return New object("ok"; False; "error"; New object("code"; "missing_executable"; "message"; $file.path))
	End if
	$file:=File($file.platformPath; fk platform path)
	$result:=New object("ok"; True; "file"; $file)

Function execute($arguments : Collection)->$result : Object
	If ($arguments=Null)
		return New object("ok"; False; "error"; New object("code"; "invalid_argument"; "message"; "Arguments collection is required"))
	End if
	$result:=This.resolve()
	If ($result.ok)
		$result:=cs._Process.new().execute($result.file; $arguments)
	End if
