# Excel 百萬數據處理專案

本專案專為高效處理百萬級 Excel 資料而設計，具備自動化拆解、數值邏輯分析、時報聚合及媒體資訊掛載功能。

## 目錄結構
- `inspect_excel.py`: 探查檔案欄位與結構。
- `analyze_logic.py`: 偵測數值欄位間的加總、比例關係。
- `aggregate_hourly.py`: 產出時報（含加權平均與公式重算）。
- `merge_reports.py`: 整合時報與媒體供應商資訊。

## 環境啟動
```bash
cd /path/to/IAS-Dashboard
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 使用說明
1. 先將待處理檔案放入此目錄或 Downloads。
2. 執行相對應腳本進行處理。

## 儀表板（Streamlit）
```bash
streamlit run dashboard_app.py
```
