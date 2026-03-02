#!/bin/bash

# Navigate to project dir
PROJECT_DIR="/Users/matt/IAS-Dashboard"
cd "$PROJECT_DIR" || exit

echo "🛑 Stopping existing Dashboard (Keep Tunnel alive if possible)..."
pkill -f "streamlit run dashboard_app.py"

echo "🚀 Starting Dashboard (Streamlit)..."
source .venv/bin/activate
# Bind to 0.0.0.0 for LAN/External access
nohup streamlit run dashboard_app.py --server.headless true --server.port 8502 --server.address 0.0.0.0 > streamlit.log 2>&1 &
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
    nohup cloudflared tunnel --url http://192.168.8.184:8502 > tunnel.log 2>&1 &
    TUNNEL_PID=$!
    echo "✅ Tunnel running (PID: $TUNNEL_PID)"
    echo "⏳ Waiting for tunnel to initialize..."
    sleep 8
fi

echo "---------------------------------------------------"
echo "🎉 Update & Deploy Complete!"
echo "---------------------------------------------------"
echo "🏠 Internal URL: http://192.168.8.184:8502"
echo "---------------------------------------------------"
echo "🌍 External URL (Current):"
grep -o 'https://.*.trycloudflare.com' tunnel.log | tail -n 1
echo "---------------------------------------------------"
echo "💡 To view logs:  tail -f streamlit.log"
echo "💡 To force NEW URL: pkill -f cloudflared && ./scripts/start_services_daemon.sh"
echo "---------------------------------------------------"
