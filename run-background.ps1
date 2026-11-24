$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$dataDir = Join-Path $env:LOCALAPPDATA 'ThunderPotato'
$keyFile = Join-Path $dataDir 'tavily-key.xml'
$logFile = Join-Path $dataDir 'server.log'
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null

if (Test-Path -LiteralPath $keyFile) {
    $secureKey = Import-Clixml -LiteralPath $keyFile
    $keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try { $env:TAVILY_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr) }
}

$ErrorActionPreference = 'Continue'
& '.\.venv\Scripts\python.exe' -m uvicorn app:app --host 0.0.0.0 --port 8000 *>> $logFile
