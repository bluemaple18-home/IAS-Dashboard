#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

required_files=(
  "dashboard_app.py"
  "requirements.txt"
  "README.md"
  "data/00_全媒體整合報表_版位級別.csv"
  "data/01_可視性廣告整合報表_版位級別.csv"
  "data/02_無效流量整合報表_版位級別.csv"
  "data/03_網站品質整合報表_版位級別.csv"
  "data/04_品牌安全性整合報表_版位級別.csv"
  "data/05_優質曝光整合報表_版位級別.csv"
)

missing=0
for file in "${required_files[@]}"; do
  if [ ! -e "$file" ]; then
    echo "缺少：$file"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "打包前檢查失敗，請先補齊缺失檔案。"
  exit 1
fi

echo "打包前檢查通過。"
