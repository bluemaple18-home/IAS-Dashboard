#!/bin/bash

# Define the port
PORT=8502

echo "🔍 Checking for cloudflared..."

if ! command -v cloudflared &> /dev/null; then
    echo "⚠️  cloudflared not found. Attempting to install via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install cloudflared
    else
        echo "❌ Homebrew not found. Please install 'cloudflared' manually or install Homebrew."
        exit 1
    fi
else
    echo "✅ cloudflared is installed."
fi

echo "🚀 Starting Cloudflare Tunnel for port $PORT..."
echo "---------------------------------------------------"
echo "🌐 COPY THE URL BELOW ending in '.trycloudflare.com'"
echo "---------------------------------------------------"

# Run Cloudflare Tunnel
cloudflared tunnel --url http://localhost:$PORT
