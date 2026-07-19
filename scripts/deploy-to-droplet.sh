#!/usr/bin/env bash
# Deploy CauseSense AI to a DigitalOcean Droplet (Docker pre-installed).
# Usage: ./scripts/deploy-to-droplet.sh root@YOUR_DROPLET_IP
set -euo pipefail

TARGET="${1:?Usage: $0 root@DROPLET_IP}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "Missing .env — copy .env.example and set GROQ_API_KEY + SECRET_KEY"
  exit 1
fi

echo "==> Syncing project to $TARGET:~/causesense"
rsync -avz --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/build' \
  --exclude '.emergent' \
  --exclude 'memory' \
  --exclude 'test_reports' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.venv' \
  "$ROOT_DIR/" "$TARGET:~/causesense/"

echo "==> Building and starting containers"
ssh "$TARGET" 'bash -s' <<'REMOTE'
set -euo pipefail
cd ~/causesense
# Ensure Docker Compose plugin is available
docker compose version >/dev/null
docker compose up -d --build
docker compose ps
curl -sf http://localhost/api/health || true
echo "Deploy complete. Point Cloudflare A records to this droplet IP."
REMOTE
