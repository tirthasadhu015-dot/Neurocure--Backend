$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$runner = Join-Path $projectRoot "backend\run_server.py"
$stdoutLog = Join-Path $projectRoot "backend\server.out.log"
$stderrLog = Join-Path $projectRoot "backend\server.err.log"
$supervisorPidFile = Join-Path $projectRoot "backend\server-supervisor.pid"

if (-not (Test-Path $python)) {
    throw "Virtualenv Python was not found at $python"
}

if (-not (Test-Path $runner)) {
    throw "Server runner was not found at $runner"
}

Set-Content -Path $supervisorPidFile -Value $PID

function Get-BackendProcess {
    Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object -First 1
}

while ($true) {
    $existing = Get-BackendProcess

    if (-not $existing) {
        Start-Process -FilePath $python `
            -ArgumentList @("""$runner""") `
            -WorkingDirectory $projectRoot `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog
    }

    Start-Sleep -Seconds 10
}
