Function failure()->$error : Object
	$error:=New object("ok"; False; "error"; New object("code"; "invalid_configuration"; "message"; "Use trusted issuer/public client configuration and supported protocol v1 settings"))

Function validate($input : Object; $command : Text)->$result : Object
	var $previous : Text
	var CLI_LastErrors : Collection
	$previous:=Method called on error(ek local)
	CLI_LastErrors:=Null
	ON ERR CALL("_CaptureError"; ek local)
	$result:=This._validate($input; $command)
	ON ERR CALL($previous; ek local)
	If (CLI_LastErrors#Null)
		$result:=This.failure()
	End if
	CLI_LastErrors:=Null

Function _validate($input : Object; $command : Text)->$result : Object
	var $config : Object
	var $name; $scope; $issuer; $key; $inline; $path : Text
	var $value : Variant
	var $bytes : Blob
	var $addressParts : Collection
	If (cs._Text.new().equal($command; "version"))
		return New object("ok"; True; "value"; New object)
	End if
	If (Not(cs._Text.new().equal($command; "authenticate")))
		return This.failure()
	End if
	If ($input=Null)
		return This.failure()
	End if
	$config:=OB Copy($input)
	For each ($name; OB Keys($config))
		If (Not(cs._Text.new().includes(New collection("issuer"; "client_id"; "protocol_version"; "scopes"; "listen_address"; "callback_path"; "timeout_seconds"; "http_timeout_seconds"; "open_browser"; "allow_insecure_loopback_http"; "include_tokens"; "parent_pid"; "success_html"; "success_html_file"; "failure_html"; "failure_html_file"); $name)))
			return This.failure()
		End if
	End for each
	For each ($name; New collection("issuer"; "client_id"))
		If (Value type($config[$name])#Is text)
			return This.failure()
		End if
		If (Not(Match regex("^\\S([^\\x00-\\x1f]*\\S)?$"; $config[$name])))
			return This.failure()
		End if
	End for each
	For each ($name; New collection("open_browser"; "allow_insecure_loopback_http"; "include_tokens"))
		If (OB Is defined($config; $name))
			If (Value type($config[$name])#Is Boolean)
				return This.failure()
			End if
		Else
			$config[$name]:=($name="open_browser")
		End if
	End for each
	$issuer:=$config.issuer
	If (Not(Match regex("^https://[^/@?#\\s\\\\]+(/[^?#\\s\\\\]*)?$"; $issuer)))
		If (Not($config.allow_insecure_loopback_http))
			return This.failure()
		End if
		If (Not(Match regex("^http://(127(\\.[0-9]{1,3}){3}|\\[::1\\])(:[0-9]{1,5})?(/[^?#\\s\\\\]*)?$"; $issuer)))
			return This.failure()
		End if
	End if
	For each ($name; New collection("protocol_version"; "timeout_seconds"; "http_timeout_seconds"; "parent_pid"))
		If (OB Is defined($config; $name))
			If ((Value type($config[$name])#Is real) & (Value type($config[$name])#Is longint))
				return This.failure()
			End if
			$value:=$config[$name]
			If (($value#Int($value)) | ($value<0))
				return This.failure()
			End if
		End if
	End for each
	If (OB Is defined($config; "protocol_version"))
		If ($config.protocol_version#1)
			return This.failure()
		End if
	End if
	$config.protocol_version:=1
	If (Not(OB Is defined($config; "timeout_seconds")))
		$config.timeout_seconds:=180
	End if
	If ($config.timeout_seconds=0)
		$config.timeout_seconds:=180
	End if
	If ($config.timeout_seconds>900)
		return This.failure()
	End if
	If (Not(OB Is defined($config; "http_timeout_seconds")))
		$config.http_timeout_seconds:=15
	End if
	If ($config.http_timeout_seconds=0)
		$config.http_timeout_seconds:=15
	End if
	If ($config.http_timeout_seconds>60)
		return This.failure()
	End if
	If (OB Is defined($config; "parent_pid"))
		If ($config.parent_pid>2147483647)
			return This.failure()
		End if
	End if
	If (Not(OB Is defined($config; "scopes")))
		$config.scopes:=New collection("openid")
	End if
	If (Value type($config.scopes)#Is collection)
		return This.failure()
	End if
	For each ($value; $config.scopes)
		If (Value type($value)#Is text)
			return This.failure()
		End if
		$scope:=$value
		If ((Not(Match regex("^[^\\s\\x00-\\x1f]+$"; $scope))) | (cs._Text.new().equal($scope; "offline_access")))
			return This.failure()
		End if
	End for each
	If (Not(cs._Text.new().includes($config.scopes; "openid")))
		return This.failure()
	End if
	If (Not(OB Is defined($config; "listen_address")))
		$config.listen_address:="127.0.0.1:0"
	End if
	If (Value type($config.listen_address)#Is text)
		return This.failure()
	End if
	If (Not(Match regex("^(127(\\.[0-9]{1,3}){3}|\\[::1\\]):[0-9]{1,5}$"; $config.listen_address)))
		return This.failure()
	End if
	$addressParts:=Split string($config.listen_address; ":")
	If (Num($addressParts.pop())>65535)
		return This.failure()
	End if
	If (Not(OB Is defined($config; "callback_path")))
		$config.callback_path:="/callback"
	End if
	If (Value type($config.callback_path)#Is text)
		return This.failure()
	End if
	If (Not(Match regex("^/[a-zA-Z0-9/_\\-.]*$"; $config.callback_path)))
		return This.failure()
	End if
	If ((Position("//"; $config.callback_path; *)>0) | (Position("/."; $config.callback_path; *)>0))
		return This.failure()
	End if
	// Empty page values mean the CLI default; the CLI reads and validates page files itself.
	For each ($name; New collection("success_html"; "failure_html"))
		For each ($key; New collection($name; $name+"_file"))
			If (OB Is defined($config; $key))
				If (Value type($config[$key])#Is text)
					return This.failure()
				End if
			End if
		End for each
		$inline:=""
		$path:=""
		If (OB Is defined($config; $name))
			$inline:=$config[$name]
		End if
		If (OB Is defined($config; $name+"_file"))
			$path:=$config[$name+"_file"]
		End if
		If ((Length($inline)>0) & (Length($path)>0))
			return This.failure()
		End if
		If (Length($inline)>0)
			CONVERT FROM TEXT($inline; "UTF-8"; $bytes)
			If (BLOB size($bytes)>65536)
				return This.failure()
			End if
		End if
		If (Length($path)>0)
			If (Not(Match regex("^(/|[A-Za-z]:[\\\\/]|\\\\\\\\)[^\\x00-\\x1f]*$"; $path)))
				return This.failure()
			End if
		End if
	End for each
	CONVERT FROM TEXT(JSON Stringify($config); "UTF-8"; $bytes)
	If (BLOB size($bytes)>65536)
		return This.failure()
	End if
	$result:=New object("ok"; True; "value"; $config)
