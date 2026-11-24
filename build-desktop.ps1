$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw '먼저 requirements-desktop.txt의 패키지를 설치해 주세요.'
}
if (-not (Test-Path -LiteralPath 'web\dist\index.html')) {
    throw 'web 폴더에서 npm run build를 먼저 실행해 주세요.'
}

& $python create_desktop_icon.py
if ($LASTEXITCODE -ne 0) { throw '아이콘 생성 실패' }

& $python -m PyInstaller `
    --noconfirm --clean --onefile --windowed `
    --name '천둥감자' `
    --icon 'assets\thunder-potato.ico' `
    --add-data 'web\dist;web\dist' `
    --add-data 'personal-instructions.txt;.' `
    --add-data 'desktop_status.html;.' `
    --add-data 'melo_worker.py;.' `
    --add-data 'eunjeon.py;.' `
    --collect-all webview `
    --collect-submodules uvicorn `
    --collect-submodules tzdata `
    desktop_app.py
if ($LASTEXITCODE -ne 0) { throw '실행 파일 빌드 실패' }

$output = Join-Path $PSScriptRoot 'dist\천둥감자.exe'
Write-Output $output
