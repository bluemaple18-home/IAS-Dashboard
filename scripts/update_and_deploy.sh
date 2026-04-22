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
    if ! command -v uv >/dev/null 2>&1; then
        echo "❌ uv 未安裝，無法更新依賴。請先安裝 uv：https://docs.astral.sh/uv/"
        exit 1
    fi

    if [ ! -d ".venv" ]; then
        echo "🧰 找不到 .venv，正在建立虛擬環境..."
        uv venv
    fi

    uv pip install -r requirements.txt
else
    echo "⚠️ No requirements.txt found."
fi

# 3. Restart Services
echo "🚀 Restarting Dashboard Services..."
./scripts/start_services_daemon.sh

echo "✅ Update & Deploy Complete!"
