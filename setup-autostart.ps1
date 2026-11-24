$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskName = 'ThunderPotato-LocalAI'
$shellPath = (Get-Command powershell.exe).Source
$runnerPath = Join-Path $PSScriptRoot 'run-background.ps1'
$action = New-ScheduledTaskAction -Execute $shellPath -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $runnerPath)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Days 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Unregister-ScheduledTask -TaskName 'ThunderPotato-Watchdog' -Confirm:$false -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName $taskName
Write-Host '자동 시작 등록 완료. Windows 로그인 시 천둥감자 서버가 시작됩니다.'
