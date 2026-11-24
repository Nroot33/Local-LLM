$ErrorActionPreference = 'SilentlyContinue'
$client = New-Object System.Net.Sockets.TcpClient
try {
    $connect = $client.BeginConnect('127.0.0.1', 8000, $null, $null)
    $connected = $connect.AsyncWaitHandle.WaitOne(1500, $false) -and $client.Connected
} catch { $connected = $false }
finally { $client.Close() }

if (-not $connected) {
    Start-ScheduledTask -TaskName 'ThunderPotato-LocalAI'
}
