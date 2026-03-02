#!/bin/bash

# Navigate to project root (assuming script is in scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit

echo "🔄 Checking for updates..."

# 1. Pull latest code
if [ -d ".git" ]; then
    echo "📥 Pulling latest Code from Git..."
    git pull origin main
else
    echo "⚠️ Not a git repository. Skipping git pull."
fi

# 2. Update Dependencies
if [ -f "requirements.txt" ]; then
    echo "📦 Checking dependencies..."
    source .venv/bin/activate
    pip install -r requirements.txt
else
    echo "⚠️ No requirements.txt found."
fi

# 3. Restart Services
echo "🚀 Restarting Dashboard Services..."
./scripts/start_services_daemon.sh

echo "✅ Update & Deploy Complete!"
