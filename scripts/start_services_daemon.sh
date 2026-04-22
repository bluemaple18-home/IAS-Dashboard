#!/bin/bash

# Navigate to project dir (portable: derive from this script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ uv 未安裝，無法啟動服務。請先安裝 uv：https://docs.astral.sh/uv/"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "🧰 找不到 .venv，正在建立虛擬環境..."
    uv venv
fi

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")"

echo "🛑 Stopping existing Dashboard (Keep Tunnel alive if possible)..."
pkill -f "streamlit run dashboard_app.py"

echo "🚀 Starting Dashboard (Streamlit)..."
# Bind to 0.0.0.0 for LAN/External access
nohup uv run streamlit run dashboard_app.py --server.headless true --server.port 8502 --server.address 0.0.0.0 > streamlit.log 2>&1 &
APP_PID=$!
echo "✅ Dashboard running (PID: $APP_PID)"

# ---------------------------------------------------
# Persistent Tunnel Logic
# ---------------------------------------------------
if pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "♻️ Existing Tunnel detected. Keeping it alive for Persistent URL."
else
    echo "🚀 Starting NEW External Tunnel (Cloudflared)..."
    PATH=$PATH:/opt/homebrew/bin
    # Use LAN IP for better stability
    nohup cloudflared tunnel --url "http://${LAN_IP}:8502" > tunnel.log 2>&1 &
    TUNNEL_PID=$!
    echo "✅ Tunnel running (PID: $TUNNEL_PID)"
    echo "⏳ Waiting for tunnel to initialize..."
    sleep 8
fi

echo "---------------------------------------------------"
echo "🎉 Update & Deploy Complete!"
echo "---------------------------------------------------"
echo "🏠 Internal URL: http://${LAN_IP}:8502"
echo "---------------------------------------------------"
echo "🌍 External URL (Current):"
grep -o 'https://.*.trycloudflare.com' tunnel.log | tail -n 1
echo "---------------------------------------------------"
echo "💡 To view logs:  tail -f streamlit.log"
echo "💡 To force NEW URL: pkill -f cloudflared && ./scripts/start_services_daemon.sh"
echo "---------------------------------------------------"
