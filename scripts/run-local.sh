#!/usr/bin/env bash
#
# Run ExhibitOS locally without Docker — for development and demos.
#
# First run sets up a Python venv, installs deps, and builds the client.
# Subsequent runs are fast. Content (SQLite + uploads) persists in ./data/
# (which is gitignored), so anything you author sticks around between runs.
#
#   ./scripts/run-local.sh
#   → http://localhost:8100/display/lobby   (public kiosk view)
#   → http://localhost:8100/admin           (admin: user "admin")
#
set -euo pipefail
cd "$(dirname "$0")/.."

# 1. Python venv + server deps
if [ ! -d .venv ]; then
  echo "→ creating Python venv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate
pip install -q -r server/requirements.txt

# 2. Build the React client if it hasn't been built yet
if [ ! -f client/dist/index.html ]; then
  echo "→ building client (first run)..."
  ( cd client && npm install --no-audit --no-fund && npm run build )
fi

# 3. Local data dir — SQLite db + uploaded images live here (gitignored)
mkdir -p data/uploads

# 4. Local environment (override by exporting before running)
export DATABASE_URL="sqlite:///./data/exhibitos.db"
export UPLOADS_DIR="./data/uploads"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-local-dev-secret-change-me}"
export DEFAULT_ADMIN_PASSWORD="${DEFAULT_ADMIN_PASSWORD:-exhibitos2026}"
export CORS_ORIGIN="http://localhost:8100"
export LOG_FORMAT="text"

echo ""
echo "ExhibitOS running:"
echo "  Kiosk display →  http://localhost:8100/display/lobby"
echo "  Admin         →  http://localhost:8100/admin"
echo ""
exec uvicorn server.main:app --host 127.0.0.1 --port 8100 --timeout-keep-alive 5
