#!/usr/bin/env bash
set +e

info() { echo -e "\033[36m[info]\033[0m $*"; }
ok()   { echo -e "\033[32m[ ok ]\033[0m $*"; }
warn() { echo -e "\033[33m[warn]\033[0m $*"; }

pid_on_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$port" 2>/dev/null
    return
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u
    return
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -ano 2>/dev/null | awk -v p=":$port" '$0 ~ p && $0 ~ /LISTEN/ {print $NF}' | sort -u
    return
  fi
}

kill_pid() {
  local pid="$1"
  if command -v taskkill.exe >/dev/null 2>&1; then
    taskkill.exe //PID "$pid" //F >/dev/null 2>&1
  else
    kill -9 "$pid" >/dev/null 2>&1
  fi
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

stop_port() {
  local port="$1" label="$2"
  local pids
  pids="$(pid_on_port "$port")"
  if [ -z "$pids" ]; then
    info "$label - nothing listening on port $port."
    return
  fi
  local pid
  for pid in $pids; do
    if kill_pid "$pid"; then
      ok "$label stopped (port $port, PID $pid)."
    else
      warn "Could not stop $label (PID $pid)."
    fi
  done
}

info "Stopping the Flask backend..."
stop_port 5000 "Backend (Flask)"

info "Stopping the Angular frontend..."
stop_port 4200 "Frontend (Angular)"

if ! docker info >/dev/null 2>&1; then
  warn "Docker engine isn't running - no containers to stop."
else
  info "Stopping database containers (data is kept)..."
  ( cd "$ROOT" && docker compose stop )
  ok "Containers stopped."
fi

echo
ok "Everything project-related is shut down."
echo "Restart it all any time with:  ./start.sh  (or run.bat)"
