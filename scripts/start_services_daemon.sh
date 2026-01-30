#!/bin/bash

# Navigate to project dir
PROJECT_DIR="/Users/mattkuo/Projects/excel-1m-processor"
cd "$PROJECT_DIR" || exit

echo "🛑 Stopping existing services..."
pkill -f "streamlit run dashboard_app.py"
pkill -f "cloudflared tunnel"

echo "🚀 Starting Dashboard (Streamlit)..."
source venv/bin/activate
nohup streamlit run dashboard_app.py --server.headless true --server.port 8502 > streamlit.log 2>&1 &
APP_PID=$!
echo "✅ Dashboard running (PID: $APP_PID)"

echo "⏳ Waiting for dashboard to launch..."
sleep 5

echo "🚀 Starting External Tunnel (Cloudflared)..."
# Use full path we found earlier or rely on PATH if brew installed
PATH=$PATH:/opt/homebrew/bin
nohup cloudflared tunnel --url http://192.168.8.184:8502 > tunnel.log 2>&1 &
TUNNEL_PID=$!
echo "✅ Tunnel running (PID: $TUNNEL_PID)"

echo "---------------------------------------------------"
echo "🎉 Deployment Complete! You can safely close this terminal."
echo "---------------------------------------------------"
echo "🏠 Internal URL: http://192.168.8.184:8502"
echo "---------------------------------------------------"
echo "🌍 External URL (Retrieving...):"
sleep 5
grep -o 'https://.*.trycloudflare.com' tunnel.log | head -n 1
echo "---------------------------------------------------"
echo "💡 To view logs:  tail -f streamlit.log"
echo "💡 To stop all:   pkill -f 'streamlit|cloudflared'"
