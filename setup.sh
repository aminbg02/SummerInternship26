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

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
DATA="$ROOT/transfer_data"

IMAGE_TAR="$DATA/docker_images.tar"
if [ -f "$IMAGE_TAR" ]; then
  info "Loading Docker images from transfer_data (no internet pull needed)..."
  docker load -i "$IMAGE_TAR"
else
  info "No bundled images in transfer_data - 'docker compose up' will pull them."
fi

info "Starting containers..."
( cd "$ROOT" && docker compose up -d )

info "Waiting for Postgres..."
pg_up=0
for _ in $(seq 1 30); do
  if docker exec orange-postgres pg_isready -U orange -d orange >/dev/null 2>&1; then pg_up=1; break; fi
  sleep 2
done
if [ "$pg_up" = 1 ]; then ok "Postgres is ready."; else warn "Postgres never reported ready - check 'docker logs orange-postgres'."; fi

info "Creating backend virtualenv and installing dependencies (a few minutes)..."
PYBIN="$(command -v python3 || command -v python)"
( cd "$BACKEND" && "$PYBIN" -m venv .venv )
PY="$(venv_python "$BACKEND")"
"$PY" -m pip install -r "$BACKEND/requirements.txt" --only-binary mmh3,fastembed
ok "Backend dependencies installed."

ENV_FILE="$BACKEND/.env"
if [ ! -f "$ENV_FILE" ]; then
  info "Generating backend/.env with fresh secrets..."
  cp "$BACKEND/.env.example" "$ENV_FILE"
  SECRET_KEY="$("$PY" -c "import secrets; print(secrets.token_hex(32))")"
  JWT_SECRET="$("$PY" -c "import secrets; print(secrets.token_hex(32))")"
  FERNET_KEY="$("$PY" -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")"
  sed_i() { if sed --version >/dev/null 2>&1; then sed -i "$@"; else sed -i '' "$@"; fi; }
  sed_i "s#SECRET_KEY=change-me#SECRET_KEY=$SECRET_KEY#" "$ENV_FILE"
  sed_i "s#JWT_SECRET=change-me#JWT_SECRET=$JWT_SECRET#" "$ENV_FILE"
  sed_i "s#^FERNET_KEY=\$#FERNET_KEY=$FERNET_KEY#" "$ENV_FILE"
  ok "backend/.env created. Add LLM API keys (GROQ_API_KEY etc.) to it if you want live providers."
else
  ok "backend/.env already exists - leaving it alone."
fi

info "Installing frontend dependencies (npm install)..."
( cd "$FRONTEND" && npm install )
ok "Frontend dependencies installed."

demo_seed() {
  info "Seeding demo data (this asks real questions through the app - a few minutes)..."
  ( cd "$BACKEND" &&
    "$PY" -m app.seed &&
    "$PY" -m app.seed_docs &&
    "$PY" -m app.seed_providers &&
    "$PY" -m app.seed_pii_rules &&
    "$PY" -m app.seed_conversations &&
    "$PY" -m app.seed_usage_history )
  ok "Demo data seeded. Log in as admin@orange.com / password123."
}

get_user_count() {
  local out
  out="$(docker exec orange-postgres psql -U orange -d orange -tAc "select count(*) from users" 2>/dev/null || echo '')"
  out="$(echo "$out" | tr -d '[:space:]')"
  case "$out" in ''|*[!0-9]*) echo 0 ;; *) echo "$out" ;; esac
}

PG_DUMP="$DATA/postgres.sql"
restored=0

if [ -f "$PG_DUMP" ]; then
  info "Restoring REAL Postgres data from transfer_data/postgres.sql..."
  docker exec -i orange-postgres psql -U orange -d orange < "$PG_DUMP"

  users="$(get_user_count)"
  if [ "$users" -lt 1 ]; then
    warn "The dump was applied but the users table is empty - the restore did not take."
    warn "Scroll up for the psql errors. Falling back to demo data so the app is usable."
  else
    ok "Postgres data restored ($users users)."
    restored=1
  fi
elif [ -d "$DATA" ]; then
  warn "transfer_data/ exists but postgres.sql isn't directly inside it (checked: $PG_DUMP)."
  warn "That is usually a nested-extraction issue - look inside $DATA"
  warn "and move the files up so postgres.sql sits directly in transfer_data/."
  warn "Continuing with demo data instead."
  sleep 5
else
  info "No transfer_data/ folder found - using demo data."
fi

if [ "$restored" = 1 ]; then
  info "Restoring Qdrant volumes from transfer_data..."
  for c in orange-qdrant orange-qdrant-ded-1 orange-qdrant-ded-2 orange-qdrant-ded-3 \
           orange-qdrant-ded-4 orange-qdrant-ded-5 orange-qdrant-ded-6 orange-qdrant-ded-7; do
    tar_file="$DATA/qdrant-$c.tar.gz"
    [ -f "$tar_file" ] || continue
    vol="$(docker inspect "$c" --format '{{ (index .Mounts 0).Name }}')"
    docker stop "$c" >/dev/null
    docker run --rm -v "$vol:/data" -v "$DATA:/backup" busybox sh -c "rm -rf /data/* && tar xzf /backup/qdrant-$c.tar.gz -C /data"
    docker start "$c" >/dev/null
  done
  ok "Qdrant data restored."

  MLFLOW_DATA_TAR="$DATA/mlflow-data.tar.gz"
  MLFLOW_ART_TAR="$DATA/mlflow-artifacts.tar.gz"
  if [ -f "$MLFLOW_DATA_TAR" ] || [ -f "$MLFLOW_ART_TAR" ]; then
    info "Restoring MLflow volumes from transfer_data..."
    docker stop orange-mlflow >/dev/null
    if [ -f "$MLFLOW_DATA_TAR" ]; then
      vol="$(docker inspect orange-mlflow --format '{{ range .Mounts }}{{ if eq .Destination "/mlflow/data" }}{{ .Name }}{{ end }}{{ end }}')"
      docker run --rm -v "$vol:/data" -v "$DATA:/backup" busybox sh -c "rm -rf /data/* && tar xzf /backup/mlflow-data.tar.gz -C /data"
    fi
    if [ -f "$MLFLOW_ART_TAR" ]; then
      vol="$(docker inspect orange-mlflow --format '{{ range .Mounts }}{{ if eq .Destination "/mlflow/artifacts" }}{{ .Name }}{{ end }}{{ end }}')"
      docker run --rm -v "$vol:/data" -v "$DATA:/backup" busybox sh -c "rm -rf /data/* && tar xzf /backup/mlflow-artifacts.tar.gz -C /data"
    fi
    docker start orange-mlflow >/dev/null
    ok "MLflow data restored (runs, params, metrics, registry + artifacts)."
  fi
else
  demo_seed
fi

echo
ok "Setup complete."
echo "Run ./start.sh (or double-click run.bat / start.bat) from now on."
