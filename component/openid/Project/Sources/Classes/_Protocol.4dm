Function failure($code : Text)->$result : Object
	$result:=New object("ok"; False; "error"; New object("code"; $code; "message"; "OIDC request failed; no credential-bearing diagnostics are retained"))

Function decode($stdout : Text; $exit : Variant; $command : Text; $configuration : Object)->$result : Object
	var $payload : Variant
	var $previous; $code : Text
	var CLI_LastErrors : Collection
	var $bytes : Blob
	CONVERT FROM TEXT($stdout; "UTF-8"; $bytes)
	If ((BLOB size($bytes)>262144) | (Length($stdout)<3))
		return This.failure("invalid_protocol")
	End if
	If ((Substring($stdout; Length($stdout); 1)#Char(10)) | (Position(Char(65533); $stdout; *)>0))
		return This.failure("invalid_protocol")
	End if
	If (Position(Char(10); Substring($stdout; 1; Length($stdout)-1); *)>0)
		return This.failure("invalid_protocol")
	End if
	If (Not(cs._JSON.new().valid($stdout)))
		return This.failure("invalid_protocol")
	End if
	$previous:=Method called on error(ek local)
	CLI_LastErrors:=Null
	ON ERR CALL("_CaptureError"; ek local)
	$payload:=JSON Parse($stdout)
	ON ERR CALL($previous; ek local)
	If (CLI_LastErrors#Null)
		CLI_LastErrors:=Null
		return This.failure("invalid_protocol")
	End if
	If (Value type($payload)#Is object)
		return This.failure("invalid_protocol")
	End if
	If ($payload=Null)
		return This.failure("invalid_protocol")
	End if
	If ((Value type($payload.protocol_version)#Is real) & (Value type($payload.protocol_version)#Is longint))
		return This.failure("invalid_protocol")
	End if
	If ($payload.protocol_version#1)
		return This.failure("protocol_version")
	End if
	If (Value type($payload.ok)#Is Boolean)
		return This.failure("invalid_protocol")
	End if
	If ((Value type($exit)#Is real) & (Value type($exit)#Is longint))
		return This.failure("process_terminated")
	End if
	If ($payload.ok)
		If ($exit#0)
			return This.failure("exit_mismatch")
		End if
		If ($command="version")
			If (Value type($payload.version)#Is text)
				return This.failure("invalid_protocol")
			End if
			If (Not(Match regex("^[0-9]+\\.[0-9]+\\.[0-9]+(-[a-zA-Z0-9.\\-]+)?$"; $payload.version)))
				return This.failure("invalid_protocol")
			End if
			return New object("ok"; True; "version"; $payload.version)
		End if
		If (Value type($payload.identity)#Is object)
			return This.failure("invalid_protocol")
		End if
		If ($payload.identity=Null)
			return This.failure("invalid_protocol")
		End if
		If ((Value type($payload.identity.issuer)#Is text) | (Value type($payload.identity.subject)#Is text))
			return This.failure("invalid_protocol")
		End if
		If ((Not(cs._Text.new().equal($payload.identity.issuer; $configuration.issuer))) | ($payload.identity.subject=""))
			return This.failure("invalid_protocol")
		End if
		$result:=New object("ok"; True; "identity"; New object("issuer"; $payload.identity.issuer; "subject"; $payload.identity.subject))
		If (OB Is defined($payload; "tokens"))
			If (Not($configuration.include_tokens))
				return This.failure("unexpected_tokens")
			End if
			If (Value type($payload.tokens)#Is object)
				return This.failure("invalid_protocol")
			End if
			If ($payload.tokens=Null)
				return This.failure("invalid_protocol")
			End if
			For each ($code; New collection("id_token"; "access_token"; "token_type"; "expires_at"))
				If (Value type($payload.tokens[$code])#Is text)
					return This.failure("invalid_protocol")
				End if
			End for each
			$result.tokens:=New object("id_token"; $payload.tokens.id_token; "access_token"; $payload.tokens.access_token; "token_type"; $payload.tokens.token_type; "expires_at"; $payload.tokens.expires_at)
		End if
		return $result
	End if
	If (Value type($payload.error)#Is object)
		return This.failure("invalid_protocol")
	End if
	If ($payload.error=Null)
		return This.failure("invalid_protocol")
	End if
	If ((Value type($payload.error.code)#Is text) | (Value type($payload.error.message)#Is text))
		return This.failure("invalid_protocol")
	End if
	$code:=$payload.error.code
	Case of
		: (($exit=2) & (cs._Text.new().equal($code; "invalid_input")))
		: (($exit=3) & (cs._Text.new().includes(New collection("discovery_failed"; "listener_failed"; "browser_failed"; "oauth_error"; "token_exchange_failed"; "token_invalid"); $code)))
		: (($exit=4) & (cs._Text.new().equal($code; "timeout")))
		: (($exit=5) & (cs._Text.new().equal($code; "cancelled")))
		: (($exit=10) & (cs._Text.new().equal($code; "internal_error")))
		Else
			return This.failure("exit_mismatch")
	End case
	$result:=This.failure($code)
	$result.exitCode:=$exit
