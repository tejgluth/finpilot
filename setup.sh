#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

read_env_value() {
  local key="$1"
  local fallback="$2"
  local env_file="${3:-.env}"

  if [ ! -f "$env_file" ]; then
    printf '%s' "$fallback"
    return
  fi

  local raw
  raw="$(grep -E "^${key}=" "$env_file" | tail -n 1 | cut -d '=' -f 2- || true)"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"

  if [ -z "$raw" ]; then
    printf '%s' "$fallback"
  else
    printf '%s' "$raw"
  fi
}

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         FinPilot Setup v0.1          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"

OS="$(uname -s)"
case "${OS}" in
  Linux*) MACHINE=Linux ;;
  Darwin*) MACHINE=Mac ;;
  *) MACHINE=WSL ;;
esac
echo -e "${BLUE}Detected: ${MACHINE}${NC}"

if ! command -v uv &> /dev/null; then
  echo -e "${YELLOW}Installing uv...${NC}"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"
fi

if ! command -v pnpm &> /dev/null; then
  echo -e "${YELLOW}Installing pnpm...${NC}"
  curl -fsSL https://get.pnpm.io/install.sh | sh -
  export PNPM_HOME="${PNPM_HOME:-$HOME/.local/share/pnpm}"
  export PATH="$PNPM_HOME:$PATH"
fi

mkdir -p data/cache data/artifacts

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo -e "${YELLOW}Created a local .env file from .env.example.${NC}"
  else
    touch .env
    echo -e "${YELLOW}.env.example was missing, so FinPilot created a blank local .env file instead.${NC}"
  fi
  echo -e "${YELLOW}FinPilot will open the local onboarding flow so you can add keys in the browser.${NC}"
fi

BACKEND_PORT="$(read_env_value BACKEND_PORT 8000)"
FRONTEND_PORT="$(read_env_value FRONTEND_PORT 5173)"

echo -e "${BLUE}Installing Python deps...${NC}"
uv sync

echo -e "${BLUE}Installing frontend deps...${NC}"
pnpm --dir frontend install --silent

echo -e "${BLUE}Validating local config...${NC}"
uv run python scripts/validate_env.py

echo -e "${GREEN}Starting FinPilot at http://localhost:${FRONTEND_PORT}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop.${NC}"

uv run python scripts/run_dev.py &
BACKEND_PID=$!

pnpm --dir frontend dev --host --port "${FRONTEND_PORT}" &
FRONTEND_PID=$!

sleep 3
command -v open &>/dev/null && open "http://localhost:${FRONTEND_PORT}" 2>/dev/null &
command -v xdg-open &>/dev/null && xdg-open "http://localhost:${FRONTEND_PORT}" 2>/dev/null &

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
