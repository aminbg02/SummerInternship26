<#
  stop.ps1 - shut down everything the project started.

  Does the reverse of start.ps1:
    1. Stops the Flask backend  (whatever is listening on port 5000).
    2. Stops the Angular frontend (whatever is listening on port 4200).
    3. Stops the database containers (Postgres, Qdrant, pgAdmin) - data is KEPT.

  Usage:   .\stop.ps1        (or double-click stop.bat)

  This never deletes data. Your companies/users/KB survive - `docker compose
  stop` only pauses the containers; `run.bat` brings everything back.
  It also leaves Docker Desktop itself running (that's shared infrastructure);
  quit it from the tray whale icon if you want to free its memory too.
#>
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot

function Info($m) { Write-Host "[stop] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[ ok ] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[warn] $m" -ForegroundColor Yellow }

function Stop-Port($port, $label) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop
    } catch {
        Info "$label - nothing listening on port $port."
        return
    }
    $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $procIds) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Ok "$label stopped (port $port, PID $procId)."
        } catch {
            Warn "Could not stop $label (PID $procId): $($_.Exception.Message)"
        }
    }
}

# --- 1) + 2) Backend and frontend -----------------------------------------
Info "Stopping the Flask backend..."
Stop-Port 5000 "Backend (Flask)"

Info "Stopping the Angular frontend..."
Stop-Port 4200 "Frontend (Angular)"

# --- 3) Database containers ------------------------------------------------
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Warn "Docker engine isn't running - no containers to stop."
} else {
    Info "Stopping database containers (data is kept)..."
    Push-Location $root
    docker compose stop
    Pop-Location
    Ok "Containers stopped."
}

Write-Host ""
Ok "Everything project-related is shut down."
Write-Host "Restart it all any time with:  run.bat  (or .\start.ps1)" -ForegroundColor DarkGray
