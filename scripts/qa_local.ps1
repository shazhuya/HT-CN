$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    throw '未找到 .venv，请先运行 安装HT-CN.bat'
}
if (-not (Test-Path 'apps\web\node_modules')) {
    throw '未找到 Web 依赖，请先运行 安装HT-CN.bat'
}

Write-Host '[HT-CN QA] 1/4 Python tests'
& .venv\Scripts\python.exe -m pytest

Write-Host '[HT-CN QA] 2/4 Web build'
Push-Location apps\web
try {
    & npm run build
} finally {
    Pop-Location
}

$api = $null
$web = $null
try {
    Write-Host '[HT-CN QA] 3/4 启动测试服务'
    $api = Start-Process -FilePath '.venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port','8765' -WorkingDirectory $root -PassThru -WindowStyle Hidden
    $web = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm run dev -- --host 127.0.0.1' -WorkingDirectory (Join-Path $root 'apps\web') -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 4

    Write-Host '[HT-CN QA] 4/4 Playwright browser tests'
    Push-Location apps\web
    try {
        & npx playwright test
    } finally {
        Pop-Location
    }
} finally {
    if ($web -and -not $web.HasExited) { Stop-Process -Id $web.Id -Force -ErrorAction SilentlyContinue }
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
}

Write-Host '[HT-CN QA] 全部通过。'
