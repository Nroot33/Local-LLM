# Run once from an administrator PowerShell window.
# The rule permits connections only from the local subnet on private networks.
$ErrorActionPreference = 'Stop'
$ruleName = 'ThunderPotato Local WiFi'
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existing) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Private -RemoteAddress LocalSubnet | Out-Null
}
$addresses = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254*' } |
    Select-Object -ExpandProperty IPAddress
foreach ($address in $addresses) {
    Write-Host "Phone URL: http://${address}:8000/"
}
