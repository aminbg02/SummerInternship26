#!/usr/bin/env bash
set -euo pipefail

export MSYS_NO_PATHCONV=1

info() { echo -e "\033[36m[info]\033[0m $*"; }
ok()   { echo -e "\033[32m[ ok ]\033[0m $*"; }
warn() { echo -e "\033[33m[warn]\033[0m $*"; }

venv_python() {
  local dir="$1"
  if [ -f "$dir/.venv/Scripts/python.exe" ]; then echo "$dir/.venv/Scripts/python.exe";
  elif [ -f "$dir/.venv/bin/python" ]; then echo "$dir/.venv/bin/python";
  fi
}

port_open() {
  (exec 3<>"/dev/tcp/localhost/$1") 2>/dev/null && { exec 3<&- 3>&-; return 0; }
  return 1
}

wait_port() {
  local port="$1" label="$2" timeout="${3:-90}"
  local deadline=$((SECONDS + timeout))
  while [ "$SECONDS" -lt "$deadline" ]; do
    port_open "$port" && return 0
    sleep 0.5
  done
  warn "$label (port $port) never answered - skipping."
  return 1
}

open_url() {
  local url="$1"
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$url" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then open "$url" >/dev/null 2>&1 &
  elif command -v cmd.exe >/dev/null 2>&1; then cmd.exe /c start "" "$url" >/dev/null 2>&1 &
  elif command -v explorer.exe >/dev/null 2>&1; then explorer.exe "$url" >/dev/null 2>&1 &
  fi
}

docker_desktop_exe() {
  local p
  for p in "/c/Program Files/Docker/Docker/Docker Desktop.exe" \
           "/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe"; do
    [ -f "$p" ] && { echo "$p"; return; }
  done
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
LOGS="$ROOT/logs"
mkdir -p "$LOGS"

NO_BROWSER=0
for arg in "$@"; do
  [ "$arg" = "--no-browser" ] && NO_BROWSER=1
done

backend_healthy() {
  curl -sf -o /dev/null -m 5 "http://localhost:5000/api/health"
}

open_when_ready() {
  local url="$1" port="$2" label="$3" timeout="${4:-90}"
  [ "$NO_BROWSER" = 1 ] && return
  if wait_port "$port" "$label" "$timeout"; then
    ok "$label is up - opening $url"
    open_url "$url"
    sleep 0.7
  fi
}

info "Checking the Docker engine..."
if ! docker info >/dev/null 2>&1; then
  info "Engine not running - launching Docker Desktop..."
  DOCKER_EXE="$(docker_desktop_exe)"
  if [ -z "$DOCKER_EXE" ]; then
    warn "Docker Desktop not found. Start the Docker daemon manually, then re-run."
    exit 1
  fi
  "$DOCKER_EXE" >/dev/null 2>&1 &
  info "Waiting for the engine (up to ~3 min)..."
  up=0
  for _ in $(seq 1 36); do
    sleep 5
    if docker info >/dev/null 2>&1; then up=1; break; fi
    printf '.'
  done
  echo
  if [ "$up" = 0 ]; then
    warn "Engine still not ready. Open Docker Desktop, wait for the whale icon to settle, then re-run."
    exit 1
  fi
fi
ok "Docker engine is running."

running="$(docker ps --filter "status=running" --format '{{.Names}}')"
missing=""
for name in orange-postgres orange-qdrant orange-pgadmin; do
  grep -qxF "$name" <<< "$running" || missing="$missing $name"
done

if [ -z "$missing" ]; then
  ok "Containers already running (Postgres, Qdrant, pgAdmin) - nothing to start."
else
  info "Starting containers:$missing..."
  ( cd "$ROOT" && docker compose up -d )
fi

info "Waiting for Postgres to accept connections..."
pg_up=0
for _ in $(seq 1 30); do
  if docker exec orange-postgres pg_isready -U orange -d orange >/dev/null 2>&1; then pg_up=1; break; fi
  sleep 2
  printf '.'
done
echo
if [ "$pg_up" = 1 ]; then ok "Postgres is ready."; else warn "Postgres didn't report ready in time - continuing anyway."; fi

if port_open 5000; then
  if backend_healthy; then
    ok "Backend already running on :5000 - not starting another."
  else
    warn "Port 5000 is taken, but /api/health doesn't answer - something"
    warn "other than the backend is using it. Free the port, then re-run."
    warn "Find it with:  lsof -i :5000   (or, on Windows, netstat -ano | grep :5000)"
    exit 1
  fi
else
  PY="$(venv_python "$BACKEND")"
  if [ -z "$PY" ]; then
    warn "No virtualenv at $BACKEND/.venv"
    warn "Create it once:  cd backend && python -m venv .venv && ./.venv/*/pip install -r requirements.txt"
    exit 1
  fi
  info "Launching Flask backend (background) -> http://localhost:5000  (log: logs/backend.log)"
  ( cd "$BACKEND" && nohup "$PY" run.py > "$LOGS/backend.log" 2>&1 & )
fi

if port_open 4200; then
  ok "Frontend already running on :4200 - not starting another."
else
  if [ ! -d "$FRONTEND/node_modules" ]; then
    info "Installing frontend dependencies (first run only, may take a few minutes)..."
    ( cd "$FRONTEND" && npm install )
  fi
  info "Launching Angular frontend (background) -> http://localhost:4200  (log: logs/frontend.log)"
  ( cd "$FRONTEND" && nohup npm start > "$LOGS/frontend.log" 2>&1 & )
fi

if [ "$NO_BROWSER" = 1 ]; then
  info "--no-browser given - not opening any tabs."
else
  echo
  info "Waiting for each service, then opening it in the browser..."

  open_when_ready "http://localhost:5050"             5050 "pgAdmin"          60
  open_when_ready "http://localhost:6333/dashboard"   6333 "Qdrant dashboard" 60
  open_when_ready "http://localhost:5000/api/health"  5000 "Flask API"        60
  open_when_ready "http://localhost:4200"             4200 "Angular app"      180
fi

echo
ok "Everything is up (or on its way)."
echo
echo "  App (Angular):  http://localhost:4200"
echo "  API (Flask):    http://localhost:5000/api/health"
echo "  Qdrant:         http://localhost:6333/dashboard"
echo "  pgAdmin:        http://localhost:5050   (admin@orange.com / orange)"
echo
echo "Backend + frontend run in the background - logs in ./logs, stop with ./end.sh."
echo "To stop just the databases:  docker compose stop"
