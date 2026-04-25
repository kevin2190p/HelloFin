#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# HelloFin – One-Command Demo Launcher
# TNG Digital FINHACK 2026
# ═══════════════════════════════════════════════════════════════
#
# Usage: ./start.sh
#
# Starts ALL services:
#   1. Redis          (in-memory state store)
#   2. FastAPI        (Jane's backend: Groq Whisper + Qwen3 + Risk)
#   3. n8n            (orchestrator)
#   4. OpenClaw       (WhatsApp interceptor — scan QR!)
#   5. Svelte UI      (SY's caregiver dashboard)
#
# Flow:
#   Scammer texts/calls → OpenClaw → n8n → FastAPI (Groq+Qwen3) → Dashboard

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() {
  echo ""
  echo -e "${BOLD}${CYAN}"
  echo "  ██╗  ██╗███████╗██╗     ██╗      ██████╗ ███████╗██╗███╗   ██╗"
  echo "  ██║  ██║██╔════╝██║     ██║     ██╔═══██╗██╔════╝██║████╗  ██║"
  echo "  ███████║█████╗  ██║     ██║     ██║   ██║█████╗  ██║██╔██╗ ██║"
  echo "  ██╔══██║██╔══╝  ██║     ██║     ██║   ██║██╔══╝  ██║██║╚██╗██║"
  echo "  ██║  ██║███████╗███████╗███████╗╚██████╔╝██║     ██║██║ ╚████║"
  echo "  ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝"
  echo -e "${RESET}"
  echo -e "${BOLD}  🛡️  Voice Phishing Detection System — FINHACK 2026${RESET}"
  echo -e "  Watching: ${RED}+60 16-356 9782${RESET} | Stack: OpenClaw + n8n + Groq + Qwen3 + Svelte"
  echo ""
}

log() { echo -e "${GREEN}[HelloFin]${RESET} $1"; }
warn() { echo -e "${YELLOW}[WARN]${RESET} $1"; }
error() { echo -e "${RED}[ERROR]${RESET} $1"; }

# ── Cleanup on exit ──────────────────────────────────────────
cleanup() {
  echo ""
  log "Shutting down all services..."
  kill $PID_BACKEND $PID_N8N $PID_OPENCLAW $PID_FRONTEND 2>/dev/null || true
  brew services stop redis 2>/dev/null || true
  echo -e "${CYAN}Goodbye!${RESET}"
}
trap cleanup EXIT INT TERM

# ════════════════════════════════════════════════════════════════
banner

# ── Check .env ──────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  error ".env file not found! Run from the HelloFin directory."
  exit 1
fi

source "$SCRIPT_DIR/.env"

# ── Check GROQ key ──────────────────────────────────────────
if [ -z "$GROQ_API_KEY" ] || [[ "$GROQ_API_KEY" == "REPLACE"* ]]; then
  error "GROQ_API_KEY not set in .env!"
  error "Get your key from https://console.groq.com"
  exit 1
fi

log "✅ Groq API key found"
log "📡 Watchlist: +${WATCHLIST_NUMBERS}"
log "📱 Owner:     +${OWNER_PHONE}"
echo ""

# ─────────────────────────────────────────────────────────────
# SERVICE 1: Redis
# ─────────────────────────────────────────────────────────────
log "Starting Redis..."
brew services start redis 2>/dev/null || warn "Redis already running or brew not available"
sleep 1

# Test Redis
if redis-cli ping 2>/dev/null | grep -q PONG; then
  log "✅ Redis is running"
else
  warn "Redis ping failed — trying to continue anyway"
fi

# ─────────────────────────────────────────────────────────────
# SERVICE 2: FastAPI Backend (Jane)
# ─────────────────────────────────────────────────────────────
log "Starting FastAPI backend (Jane)..."
cd "$SCRIPT_DIR/backend"

# Set up virtualenv if not present
if [ ! -d "venv" ]; then
  log "Creating Python virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate
log "Installing backend dependencies..."
pip install -q -r requirements.txt

# Create audios dir
mkdir -p "$SCRIPT_DIR/audios"

# Start FastAPI
PYTHONPATH="$SCRIPT_DIR/backend" uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --reload \
  --log-level warning \
  > "$SCRIPT_DIR/logs/backend.log" 2>&1 &
PID_BACKEND=$!

log "✅ FastAPI starting on http://localhost:8000 (PID: $PID_BACKEND)"
sleep 3

# Verify backend is up
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  log "✅ Backend health check passed"
else
  warn "Backend not responding yet — may still be starting"
fi

# ─────────────────────────────────────────────────────────────
# SERVICE 3: n8n (Orchestrator)
# ─────────────────────────────────────────────────────────────
log "Starting n8n orchestrator..."
cd "$SCRIPT_DIR"

N8N_BASIC_AUTH_ACTIVE=true \
N8N_BASIC_AUTH_USER="${N8N_BASIC_AUTH_USER:-admin}" \
N8N_BASIC_AUTH_PASSWORD="${N8N_BASIC_AUTH_PASSWORD:-hellofin2026}" \
  npx n8n start \
  > "$SCRIPT_DIR/logs/n8n.log" 2>&1 &
PID_N8N=$!

log "✅ n8n starting on http://localhost:5678 (PID: $PID_N8N)"
sleep 4

# ─────────────────────────────────────────────────────────────
# SERVICE 4: OpenClaw (WhatsApp Bridge — KV)
# ─────────────────────────────────────────────────────────────
log "Starting OpenClaw WhatsApp bridge..."
cd "$SCRIPT_DIR/openclaw"

if [ ! -d "node_modules" ]; then
  log "Installing OpenClaw dependencies..."
  npm install --silent
fi

# OpenClaw runs in FOREGROUND so QR code is visible
echo ""
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}${YELLOW}  📱 SCAN QR CODE WITH YOUR WHATSAPP TO CONNECT!         ${RESET}"
echo -e "${BOLD}${YELLOW}  WhatsApp → Settings → Linked Devices → Link a Device   ${RESET}"
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

node server.js &
PID_OPENCLAW=$!

sleep 5

# ─────────────────────────────────────────────────────────────
# SERVICE 5: Svelte Dashboard (SY)
# ─────────────────────────────────────────────────────────────
log "Starting Svelte caregiver dashboard (SY)..."
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
  log "Installing frontend dependencies..."
  npm install --silent
fi

npm run dev > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
PID_FRONTEND=$!

log "✅ Dashboard starting on http://localhost:3000 (PID: $PID_FRONTEND)"
sleep 2

# ─────────────────────────────────────────────────────────────
# ALL SERVICES RUNNING
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}${GREEN}  ✅ ALL SYSTEMS GO — HelloFin is LIVE!                   ${RESET}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  📊 Dashboard:       ${CYAN}http://localhost:3000${RESET}"
echo -e "  ⚙️  n8n Console:    ${CYAN}http://localhost:5678${RESET}"
echo -e "  🔌 Backend API:     ${CYAN}http://localhost:8000/docs${RESET}"
echo -e "  🔴 Watching:        ${RED}+${WATCHLIST_NUMBERS}${RESET}"
echo ""
echo -e "  ${BOLD}📋 IMPORT n8n WORKFLOW:${RESET}"
echo -e "  Go to http://localhost:5678 → Workflows → Import"
echo -e "  File: ${CYAN}n8n/voice_phishing_workflow.json${RESET} → Toggle ACTIVE"
echo ""
echo -e "  ${BOLD}🎤 TO TEST:${RESET}"
echo -e "  Ask +60163569782 to text or voice note your WhatsApp"
echo -e "  Watch the dashboard light up! 🚨"
echo ""
echo -e "${YELLOW}  Press Ctrl+C to stop all services${RESET}"
echo ""

# ─────────────────────────────────────────────────────────────
# Keep running — tail logs
# ─────────────────────────────────────────────────────────────
wait $PID_OPENCLAW
