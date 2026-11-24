$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$secureKey = Read-Host -AsSecureString 'Tavily API Key'
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try { $env:TAVILY_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr) }
if (-not $env:TAVILY_API_KEY) { throw 'API 키가 입력되지 않았습니다.' }
& '.\.venv\Scripts\python.exe' -m uvicorn app:app --host 127.0.0.1 --port 8000
