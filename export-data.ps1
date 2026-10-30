<#
  export-data.ps1 - packages THIS machine's real data + Docker images for a
  full-fidelity transfer, instead of the friend re-seeding demo data from
  scratch.

  Produces .\transfer_data\ containing:
    postgres.sql          - full pg_dump of the orange database (all real rows)
    qdrant-<container>.tar.gz    - one per Qdrant volume (shared + 7 dedicated)
    mlflow-data.tar.gz           - orange-mlflow's /mlflow/data volume (the
                                    sqlite backend store: runs, params, metrics,
                                    the model/prompt registry)
    mlflow-artifacts.tar.gz      - orange-mlflow's /mlflow/artifacts volume
                                    (logged artifacts: models, plots, files)
    docker_images.tar     - the 5 images docker-compose.yml needs, so the
                             target machine doesn't need internet just to get
                             the stack up

  Requires `docker compose up -d` to already be running on THIS machine.
  Zip the transfer_data folder alongside the project zip and send both.
#>
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$out  = Join-Path $root "transfer_data"
New-Item -ItemType Directory -Force -Path $out | Out-Null

function Info($m) { Write-Host "[export] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[ ok  ] $m" -ForegroundColor Green }

# --- Sanity check: containers must be up ------------------------------------
docker inspect orange-postgres *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "orange-postgres isn't running. Run 'docker compose up -d' first." -ForegroundColor Yellow
    exit 1
}

# --- 1) Postgres: real data, not the seed scripts ---------------------------
Info "Dumping Postgres (orange-postgres)..."
$pgOut = Join-Path $out "postgres.sql"
docker exec orange-postgres pg_dump -U orange -d orange | Out-File -Encoding utf8 $pgOut
if ($LASTEXITCODE -ne 0 -or (Get-Item $pgOut).Length -eq 0) {
    Write-Host "pg_dump failed or produced an empty file - is orange-postgres actually running/healthy?" -ForegroundColor Red
    exit 1
}
Ok "postgres.sql written ($((Get-Item $pgOut).Length) bytes)."

# --- 2) Qdrant: one archive per container's volume --------------------------
# Read the volume name off each container instead of guessing the compose
# project prefix (which depends on the folder name and would break if either
# of you renamed the folder after unzipping).
$qdrantContainers = @(
    "orange-qdrant",
    "orange-qdrant-ded-1", "orange-qdrant-ded-2", "orange-qdrant-ded-3",
    "orange-qdrant-ded-4", "orange-qdrant-ded-5", "orange-qdrant-ded-6", "orange-qdrant-ded-7"
)
foreach ($c in $qdrantContainers) {
    docker inspect $c *> $null
    if ($LASTEXITCODE -ne 0) { Write-Host "  skipping $c (not running)" -ForegroundColor Yellow; continue }
    $vol = docker inspect $c --format '{{ (index .Mounts 0).Name }}'
    Info "Archiving $c (volume $vol)..."
    docker run --rm -v "${vol}:/data" -v "${out}:/backup" busybox tar czf "/backup/qdrant-$c.tar.gz" -C /data .
}
Ok "Qdrant volumes archived."

# --- 3) MLflow: data volume (sqlite db) + artifacts volume -------------------
# Parsed as JSON rather than a Go-template with embedded double quotes: passing
# `"/mlflow/data"` inside a --format string gets mangled when PowerShell hands
# the argument to the native docker.exe, so plain JSON + ConvertFrom-Json avoids
# the quoting problem entirely.
docker inspect orange-mlflow *> $null
if ($LASTEXITCODE -eq 0) {
    Info "Archiving orange-mlflow's data + artifacts volumes..."
    $mounts          = docker inspect orange-mlflow --format '{{json .Mounts}}' | ConvertFrom-Json
    $mlflowData      = ($mounts | Where-Object { $_.Destination -eq "/mlflow/data" }).Name
    $mlflowArtifacts = ($mounts | Where-Object { $_.Destination -eq "/mlflow/artifacts" }).Name
    if (-not $mlflowData -or -not $mlflowArtifacts) {
        Write-Host "  could not resolve mlflow volume names - skipping" -ForegroundColor Yellow
    } else {
        docker run --rm -v "${mlflowData}:/data" -v "${out}:/backup" busybox tar czf "/backup/mlflow-data.tar.gz" -C /data .
        docker run --rm -v "${mlflowArtifacts}:/data" -v "${out}:/backup" busybox tar czf "/backup/mlflow-artifacts.tar.gz" -C /data .
        Ok "MLflow volumes archived (runs, params, metrics, registry + logged artifacts)."
    }
} else {
    Write-Host "  skipping orange-mlflow (not running)" -ForegroundColor Yellow
}

# --- 4) Docker images: so the target PC doesn't need to pull ----------------
Info "Saving Docker images (a few minutes, ~1-2GB total)..."
docker save -o (Join-Path $out "docker_images.tar") `
    postgres:16 qdrant/qdrant:latest dpage/pgadmin4:latest ghcr.io/mlflow/mlflow:v3.15.0
Ok "docker_images.tar written."

Write-Host ""
Ok "Done. Send the transfer_data folder together with the project zip:"
Write-Host "     $out"
