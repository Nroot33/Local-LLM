$ErrorActionPreference = 'Stop'
$dataDir = Join-Path $env:LOCALAPPDATA 'ThunderPotato'
$keyFile = Join-Path $dataDir 'tavily-key.xml'
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null

$secureKey = Read-Host -AsSecureString 'Tavily API Key'
if ($secureKey.Length -eq 0) { throw 'API 키가 입력되지 않았습니다.' }
$secureKey | Export-Clixml -LiteralPath $keyFile
Write-Host 'Tavily 키를 현재 Windows 사용자 계정으로 암호화해 저장했습니다.'

if (Get-ScheduledTask -TaskName 'ThunderPotato-LocalAI' -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName 'ThunderPotato-LocalAI' -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    $listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
        if ($serverProcess.CommandLine -like "*$PSScriptRoot*uvicorn*app:app*") {
            Stop-Process -Id $listener.OwningProcess -ErrorAction Stop
            Start-Sleep -Seconds 2
        } else {
            throw '8000번 포트를 다른 프로그램이 사용 중입니다.'
        }
    }
    Start-ScheduledTask -TaskName 'ThunderPotato-LocalAI'
    Start-Sleep -Seconds 5
    $status = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 10
    if ($status.search_provider -ne 'tavily') { throw '서버는 실행됐지만 Tavily 설정이 적용되지 않았습니다.' }
    Write-Host '천둥감자 서버를 Tavily 검색으로 다시 시작했습니다.'
}
