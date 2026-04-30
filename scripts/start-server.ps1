$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$supervisor = Join-Path $projectRoot "backend\keep-server-alive.ps1"
$stdoutLog = Join-Path $projectRoot "backend\server.out.log"
$stderrLog = Join-Path $projectRoot "backend\server.err.log"
$supervisorPidFile = Join-Path $projectRoot "backend\server-supervisor.pid"

if (-not (Test-Path $supervisor)) {
    throw "Server supervisor was not found at $supervisor"
}

$existingSupervisor = $null
if (Test-Path $supervisorPidFile) {
    $existingSupervisorId = (Get-Content $supervisorPidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($existingSupervisorId) {
        $existingSupervisor = Get-Process -Id $existingSupervisorId -ErrorAction SilentlyContinue
    }
}

if (-not $existingSupervisor) {
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList @(
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            """$supervisor"""
        ) `
        -WorkingDirectory $projectRoot
}

Write-Output "NeuroCure+ backend start requested."
Write-Output "Health URL: http://127.0.0.1:5000/api/health"
Write-Output "Logs: $stdoutLog"
