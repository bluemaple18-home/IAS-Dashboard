import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def process_new_viewability(input_path):
    print(f"🚀 開始處理新格式資料: {input_path}")
    
    # 輸出路徑
    output_dir = DATA_DIR
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(input_path).replace(".xlsx", "_hourly_report.xlsx")
    output_path = os.path.join(output_dir, base_name)
    
    try:
        # 1. 智慧讀取：先讀取前 5 行來定位真正表頭
        print("📥 正在偵測資料結構與定位表頭...")
        df_scan = pd.read_excel(input_path, nrows=5)
        
        # 找出包含 "Total Tracked Ads" 或 "Measured Ads" 的那一行
        header_row_idx = 0
        for i, row in df_scan.iterrows():
            row_str = " ".join(row.astype(str).tolist())
            if "Total Tracked Ads" in row_str or "Measured Ads" in row_str:
                header_row_idx = i + 1
                print(f"📍 定位到表頭於第 {header_row_idx + 1} 行")
                break
        
        # 重新讀取
        df = pd.read_excel(input_path, skiprows=header_row_idx)
        
        # 2. 修正 Unnamed 欄位 (手動對應 IAS 標準順序)
        # 根據觀察，Unnamed 順序通常是穩定與表頭對齊的
        # 我們將含有特定關鍵字的 Unnamed 修正
        column_mapping = {
            'DIMENSIONS': '版位編號',
            'Placement Id': '版位編號',
            'Total Tracked Ads': 'Total Tracked Ads',
            'Eligible Ads for Viewability': 'Eligible Ads for Viewability',
            'Measured Ads': 'Measured Ads',
            'Viewable Impressions': 'Viewable Impressions',
            'Non-Viewable Ads': 'Non-Viewable Ads',
            'Average Time In View (Sec)': 'Average Time In View (Sec)'
        }
        
        # 如果 Pandas 自動讀取的欄位名稱不準，我們手動暴力偵測前兩行內容來 rename
        if 'Total Tracked Ads' not in df.columns:
             # 有可能在 Unnamed 裡，我們尋找含有數據的邏輯
             new_cols = []
             for col in df.columns:
                 # 檢查該欄位的前幾行是否含有關鍵指標名稱
                 col_name = str(col)
                 new_cols.append(col_name)
             df.columns = new_cols

        # 基礎維度拆解 (正規邏輯)
        print("✂️ 正在從 DIMENSIONS 拆解時間維度...")
        
        # 確保定位 ID 欄位
        id_col_source = 'DIMENSIONS' if 'DIMENSIONS' in df.columns else df.columns[0]
        df['DIM'] = df[id_col_source].astype(str).str.strip()
        
        # 邏輯：處理 YYYYMMDDHHMMSS_ID 格式，排除非標準行
        df = df[df['DIM'].str.contains('_', na=False)]
        
        split_parts = df['DIM'].str.split('_', expand=True)
        
        # 建立維度欄位
        df['日期'] = split_parts[0].str.slice(0, 8)
        df['小時'] = split_parts[0].str.slice(8, 10)
        df['版位編號'] = split_parts[1]
        
        # 重新命名欄位以符合小時聚合預期
        print("📊 執行小時聚合計算 (GroupBy)...")
        
        # 動態偵測存在的數值欄位
        numeric_candidates = ['Total Tracked Ads', 'Eligible Ads for Viewability', 'Measured Ads', 'Viewable Impressions', 'Non-Viewable Ads']
        actual_numeric_cols = [c for c in numeric_candidates if c in df.columns]
        
        for col in actual_numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 執行整合
        agg_ops = {col: 'sum' for col in actual_numeric_cols}
        if 'Average Time In View (Sec)' in df.columns:
            df['Average Time In View (Sec)'] = pd.to_numeric(df['Average Time In View (Sec)'], errors='coerce').fillna(0)
            agg_ops['Average Time In View (Sec)'] = 'mean'
            
        print(f"🔄 正在對 {len(df)} 筆原始資料進行正規聚合...")
        final_df = df.groupby(['日期', '小時', '版位編號'], as_index=False).agg(agg_ops)
        
        print(f"📤 正在儲存至: {output_path} (聚合後剩餘 {len(final_df)} 筆小時級別資料)")
        final_df.to_excel(output_path, index=False)
        
        print("✅ 處理完成！")
        return output_path

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    file_path = "/Users/mattkuo/Downloads/sample-Viewability_20260315-20260413.xlsx"
    process_new_viewability(file_path)
