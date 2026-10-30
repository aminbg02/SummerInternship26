<#
  start.ps1 - one-shot launcher for the Orange RAG platform.

  Does the whole startup dance for you, in order:
    1. Starts the Docker engine (Docker Desktop) if it isn't running.
    2. Starts the database containers (Postgres, Qdrant, pgAdmin) and waits
       until Postgres is actually accepting connections.
    3. Launches the Flask backend in its own window   (http://localhost:5000).
    4. Launches the Angular frontend in its own window (http://localhost:4200).
    5. Waits for each service to answer, then opens it in your browser:
       the app, the API health check, the Qdrant dashboard and pgAdmin.

  Every step is SKIPPED if that piece is already up, so this is safe to run
  twice - you won't get a second backend window fighting for port 5000. Re-run
  it any time just to reopen the browser tabs.

  Usage:   .\start.ps1        (or just double-click run.bat)
           .\start.ps1 -NoBrowser    (start what's down, open nothing)

  Note: this only STARTS things; it never seeds or wipes data. The backend and
  frontend each open in their own window - close those windows to stop them.
#>
param([switch]$NoBrowser)

$ErrorActionPreference = "Stop"
$root     = $PSScriptRoot
$backend  = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$docker   = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

function Info($m) { Write-Host "[start] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[ ok  ] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[warn ] $m" -ForegroundColor Yellow }

# Is something listening on this port right now? Instant, no waiting.
#
# Ask Windows for the listener rather than dialing a socket: these four
# services each bind a different address family. Flask listens on 127.0.0.1,
# the Angular dev server on ::1 ONLY, and Docker publishes on 0.0.0.0. A
# connect to a hardcoded 127.0.0.1 silently misses Angular; a connect to
# "localhost" stalls on the ::1 attempt when the port is closed.
function Test-Port($portNumber) {
    return [bool](Get-NetTCPConnection -LocalPort $portNumber -State Listen -ErrorAction SilentlyContinue)
}

# Poll a TCP port until something is listening on it. Angular in particular
# needs ~20s to compile before it binds 4200, so we wait rather than opening a
# tab onto a connection-refused page.
function Wait-Port($portNumber, $label, $timeoutSeconds = 90) {
    # Deadline-based, not iteration-based: a refused connect can itself cost a
    # second or two, so counting attempts would overshoot the timeout badly.
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $portNumber) { return $true }
        Start-Sleep -Milliseconds 500
    }
    Warn "$label (port $portNumber) never answered - skipping its browser tab."
    return $false
}

# Does the Flask backend answer on :5000, or is some other process squatting
# on the port? Only our app serves /api/health.
function Test-BackendHealthy {
    try {
        $r = Invoke-WebRequest "http://localhost:5000/api/health" -UseBasicParsing -TimeoutSec 5
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

# Open a URL in the default browser, but only once its port is actually up.
function Open-When-Ready($url, $portNumber, $label, $timeoutSeconds = 90) {
    if ($NoBrowser) { return }
    if (Wait-Port $portNumber $label $timeoutSeconds) {
        Ok "$label is up - opening $url"
        Start-Process $url
        Start-Sleep -Milliseconds 700   # let the browser settle between tabs
    }
}

# --- 1) Docker engine ------------------------------------------------------
Info "Checking the Docker engine..."
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Info "Engine not running - launching Docker Desktop..."
    if (-not (Test-Path $docker)) { Warn "Docker Desktop not found at $docker. Start it manually, then re-run."; exit 1 }
    Start-Process $docker
    Info "Waiting for the engine (up to ~3 min)..."
    $up = $false
    for ($i = 0; $i -lt 36; $i++) {
        Start-Sleep -Seconds 5
        docker info *> $null
        if ($LASTEXITCODE -eq 0) { $up = $true; break }
        Write-Host "." -NoNewline
    }
    Write-Host ""
    if (-not $up) { Warn "Engine still not ready. Open Docker Desktop, wait for the whale icon to settle, then re-run."; exit 1 }
}
Ok "Docker engine is running."

# --- 2) Database containers ------------------------------------------------
# @() forces an array even when docker prints a single name, so -notcontains
# compares names rather than doing a substring match on one long string.
$wanted  = @("orange-postgres", "orange-qdrant", "orange-pgadmin")
$running = @(docker ps --filter "status=running" --format "{{.Names}}")
$missing = @($wanted | Where-Object { $running -notcontains $_ })

if ($missing.Count -eq 0) {
    Ok "Containers already running (Postgres, Qdrant, pgAdmin) - nothing to start."
} else {
    Info "Starting containers: $($missing -join ', ')..."
    Push-Location $root
    docker compose up -d          # idempotent: only brings up what's down
    Pop-Location
}

Info "Waiting for Postgres to accept connections..."
$pgUp = $false
for ($i = 0; $i -lt 30; $i++) {
    docker exec orange-postgres pg_isready -U orange -d orange *> $null
    if ($LASTEXITCODE -eq 0) { $pgUp = $true; break }
    Start-Sleep -Seconds 2
    Write-Host "." -NoNewline
}
Write-Host ""
if ($pgUp) { Ok "Postgres is ready." } else { Warn "Postgres didn't report ready in time - continuing anyway." }

# --- 3) Backend (Flask) ----------------------------------------------------
# Starting a second backend would just fail to bind :5000, so check first.
if (Test-Port 5000) {
    if (Test-BackendHealthy) {
        Ok "Backend already running on :5000 - not starting another."
    } else {
        Warn "Port 5000 is taken, but /api/health doesn't answer - something"
        Warn "other than the backend is using it. Free the port, then re-run."
        Warn "Find it with:  Get-NetTCPConnection -LocalPort 5000 -State Listen"
        exit 1
    }
} else {
    $py = Join-Path $backend ".venv\Scripts\python.exe"
    if (-not (Test-Path $py)) {
        Warn "No virtualenv at $py"
        Warn "Create it once:  cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
        exit 1
    }
    Info "Launching Flask backend (new window) -> http://localhost:5000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$backend`"; & `"$py`" run.py"
}

# --- 4) Frontend (Angular) -------------------------------------------------
if (Test-Port 4200) {
    Ok "Frontend already running on :4200 - not starting another."
} else {
    if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
        Info "Installing frontend dependencies (first run only, may take a few minutes)..."
        Push-Location $frontend
        npm install
        Pop-Location
    }
    Info "Launching Angular frontend (new window) -> http://localhost:4200"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$frontend`"; npm start"
}

# --- 5) Open everything in the browser -------------------------------------
if ($NoBrowser) {
    Info "-NoBrowser given - not opening any tabs."
} else {
    Write-Host ""
    Info "Waiting for each service, then opening it in the browser..."

    # Infrastructure first (already up), then API, then the app last so the
    # Angular tab ends up focused - that's the one you actually work in.
    Open-When-Ready "http://localhost:5050"                  5050 "pgAdmin"          60
    Open-When-Ready "http://localhost:6333/dashboard"        6333 "Qdrant dashboard" 60
    Open-When-Ready "http://localhost:5000/api/health"       5000 "Flask API"        60
    Open-When-Ready "http://localhost:4200"                  4200 "Angular app"      180
}

# --- Done ------------------------------------------------------------------
Write-Host ""
Ok "Everything is up (or on its way)."
Write-Host ""
Write-Host "  App (Angular):  http://localhost:4200"
Write-Host "  API (Flask):    http://localhost:5000/api/health"
Write-Host "  Qdrant:         http://localhost:6333/dashboard"
Write-Host "  pgAdmin:        http://localhost:5050   (admin@orange.com / orange)"
Write-Host ""
Write-Host "Backend + frontend run in their own windows - close them to stop." -ForegroundColor DarkGray
Write-Host "To stop the databases too:  docker compose stop" -ForegroundColor DarkGray
