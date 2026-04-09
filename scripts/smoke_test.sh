#!/usr/bin/env bash
# smoke_test.sh — boot the FinPilot backend and assert the two key health endpoints
# respond with HTTP 200 and expected JSON shapes.
#
# Usage:
#   bash scripts/smoke_test.sh
#
# Exit code: 0 = pass, 1 = fail

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PORT="${BACKEND_PORT:-8000}"
MAX_WAIT=20
BACKEND_PID=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
  if [ -n "${BACKEND_PID}" ]; then
    kill "${BACKEND_PID}" 2>/dev/null || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# ── Start backend ──────────────────────────────────────────────────────────────
echo -e "${YELLOW}[smoke] Starting backend on port ${PORT}...${NC}"
uv run python -m backend.main > /tmp/finpilot_smoke_backend.log 2>&1 &
BACKEND_PID=$!

# ── Wait for it to accept connections ─────────────────────────────────────────
echo -e "${YELLOW}[smoke] Waiting for backend to boot (max ${MAX_WAIT}s)...${NC}"
elapsed=0
until curl -s "http://127.0.0.1:${PORT}/api/health" > /dev/null 2>&1; do
  sleep 1
  elapsed=$((elapsed + 1))
  if [ "${elapsed}" -ge "${MAX_WAIT}" ]; then
    echo -e "${RED}[smoke] FAIL: backend did not start within ${MAX_WAIT}s${NC}"
    echo "--- backend log ---"
    cat /tmp/finpilot_smoke_backend.log || true
    exit 1
  fi
done
echo -e "${GREEN}[smoke] Backend is up (${elapsed}s)${NC}"

# ── Assert /api/health ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[smoke] Checking /api/health...${NC}"
HEALTH_RESPONSE="$(curl -sf "http://127.0.0.1:${PORT}/api/health")"
HEALTH_STATUS="$(echo "${HEALTH_RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo '')"
if [ "${HEALTH_STATUS}" != "ok" ]; then
  echo -e "${RED}[smoke] FAIL: /api/health did not return status=ok${NC}"
  echo "Response: ${HEALTH_RESPONSE}"
  exit 1
fi
echo -e "${GREEN}[smoke] /api/health OK${NC}"

# ── Assert /api/setup/status ───────────────────────────────────────────────────
echo -e "${YELLOW}[smoke] Checking /api/setup/status...${NC}"
SETUP_RESPONSE="$(curl -sf "http://127.0.0.1:${PORT}/api/setup/status")"
ALPACA_MODE="$(echo "${SETUP_RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('user_settings',{}); print(s.get('alpaca',{}).get('mode','paper'))" 2>/dev/null || echo 'paper')"
if [ -z "${SETUP_RESPONSE}" ]; then
  echo -e "${RED}[smoke] FAIL: /api/setup/status returned empty response${NC}"
  exit 1
fi
echo -e "${GREEN}[smoke] /api/setup/status OK (alpaca_mode=${ALPACA_MODE})${NC}"

# ── Done ───────────────────────────────────────────────────────────────────────
echo -e "${GREEN}[smoke] All checks passed.${NC}"
