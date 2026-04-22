## 目的
把此專案「原樣」打包到另一台電腦，用 Codex 進行開發/除錯（不包含本機的 `.venv`）。

## 專案重點（快速導覽）
- `dashboard_app.py`：Streamlit 儀表板主程式（含簡易密碼保護）。
- `scripts/start_services_daemon.sh`：啟動/重啟 Streamlit（並可選擇啟 cloudflared tunnel）。
- `scripts/update_and_deploy.sh`：更新程式碼、更新依賴、重啟服務（已改為使用 `uv`）。
- `deploy/`：launchd service 安裝腳本與 plist（目前仍含本機絕對路徑，另一台電腦若要用需改路徑）。
- `data/`：範例報表與輸入輸出資料。

## 打包檔案位置
打包完成後會生成一個 `.tar.gz` 在：
- `/tmp/IAS-Dashboard_YYYY-MM-DD_<gitsha>.tar.gz`

（若你要我改成 zip，或改成「不包含 `.git`」的更小包也可以。）

## 打包前檢查
- `scripts/check_transfer_package.sh` 會先確認 `dashboard_app.py` 與 `data/` 的必要檔案都在，避免缺件才發現。

## 另一台電腦的使用步驟（建議）
1. 解壓縮：
   - `tar -xzf IAS-Dashboard_YYYY-MM-DD_<gitsha>.tar.gz`
2. 進入資料夾：
   - `cd IAS-Dashboard`
3. 安裝 `uv`（若尚未安裝）。
4. 建立虛擬環境 + 安裝依賴：
   - `uv venv`
   - `uv pip install -r requirements.txt`
5. 啟動儀表板：
   - `uv run streamlit run dashboard_app.py`

## 需要你確認/留意的點
- `dashboard_app.py` 內有硬編碼密碼（打包後如果會交付給非信任環境，建議改成用環境變數或 secrets 管理）。
- `deploy/com.mattkuo.iasdashboard.plist` 目前寫死 `/Users/mattkuo/Projects/IAS-Dashboard`，換機使用 launchd 前需要調整成新機路徑。
