#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

bash scripts/check_transfer_package.sh

DATE_STAMP="$(date +%F)"
GIT_SHA="nogit"
if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
  GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
fi

OUT="/tmp/IAS-Dashboard_${DATE_STAMP}_${GIT_SHA}.tar.gz"

echo "📦 Packaging to: $OUT"

tar -czf "$OUT" \
  --exclude=".git" \
  --exclude=".venv" \
  --exclude="__pycache__" \
  --exclude="**/__pycache__" \
  --exclude="*.log" \
  --exclude=".DS_Store" \
  --exclude="dev_sandbox" \
  .

echo "✅ Done: $OUT"
