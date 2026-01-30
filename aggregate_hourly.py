import pandas as pd
import numpy as np

def aggregate_hourly(input_path):
    print(f"🚀 開始產出時報: {input_path}")
    output_path = input_path.replace(".xlsx", "_hourly_report.xlsx")
    
    try:
        # 1. 讀取原始資料 (跳過前兩行，指定類型確保 ID 完整)
        print("📥 正在讀取資料...")
        df_raw = pd.read_excel(input_path, skiprows=1, dtype={'DIMENSIONS': str})
        
        # 修正欄位名稱
        headers = df_raw.iloc[0].values
        df = df_raw.iloc[1:].copy()
        df.columns = headers
        
        print(f"檢測到的欄位: {df.columns.tolist()}")
        
        # 鍵欄位是 'Placement Id' (這是 DIMENSIONS 下方的真正的欄位名)
        if 'Placement Id' not in df.columns:
             print("❌ 找不到 'Placement Id' 欄位，嘗試搜尋類似名稱...")
             # 有時候會有空格或換行
             df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
        
        target_col = 'Placement Id'
        
        print("✂️ 正在進行初步解析與清理...")
        # 提取日期、小時、版位編號
        df[target_col] = df[target_col].astype(str)
        split_parts = df[target_col].str.split('_', expand=True)
        timestamp = split_parts[0]
        
        df['日期'] = timestamp.str.slice(0, 8)
        df['小時'] = timestamp.str.slice(8, 10)
        df['版位編號'] = split_parts[1]
        
        # 數值化 (除 ID 以外)
        numeric_cols = [
            'Total Tracked Ads', 'Eligible Ads for Viewability', 'Measured Ads', 
            'Viewable Impressions', 'Non-Viewable Ads', 'Average Time In View (Sec)'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 2. 準備加權平均時間的「總時間」
        # 總時間 = 平均時間 * 測量廣告數
        df['Total Time (Internal)'] = df['Average Time In View (Sec)'] * df['Measured Ads']
        
        # 3. 執行聚合 (Group By 日期, 小時, 版位編號)
        print("📊 正在執行數據聚合 (加總各項數值)...")
        agg_logic = {
            'Total Tracked Ads': 'sum',
            'Eligible Ads for Viewability': 'sum',
            'Measured Ads': 'sum',
            'Viewable Impressions': 'sum',
            'Non-Viewable Ads': 'sum',
            'Total Time (Internal)': 'sum'
        }
        
        hourly_df = df.groupby(['日期', '小時', '版位編號'], as_index=False).agg(agg_logic)
        
        # 4. 重新計算百分比與平均值 (公式重算)
        print("🧮 正在根據加總後數據重算公式指標...")
        
        # (1) 測量率 = 總測量數 / 總合格數
        hourly_df['% Measured Ads'] = (hourly_df['Measured Ads'] / hourly_df['Eligible Ads for Viewability']).fillna(0).replace([np.inf, -np.inf], 0) * 100
        
        # (2) 可視率 = 總可視數 / 總測量數
        hourly_df['% Viewable Impressions'] = (hourly_df['Viewable Impressions'] / hourly_df['Measured Ads']).fillna(0).replace([np.inf, -np.inf], 0) * 100
        
        # (3) 不可視率 = 總不可視數 / 總測量數
        hourly_df['% Non-Viewable Ads'] = (hourly_df['Non-Viewable Ads'] / hourly_df['Measured Ads']).fillna(0).replace([np.inf, -np.inf], 0) * 100
        
        # (4) 平均平均時間 = 總時間 / 總測量數 (加權平均)
        hourly_df['Average Time In View (Sec)'] = (hourly_df['Total Time (Internal)'] / hourly_df['Measured Ads']).fillna(0).replace([np.inf, -np.inf], 0)
        
        # 移除內部暫存欄位並整理順序
        hourly_df = hourly_df.drop(columns=['Total Time (Internal)'])
        
        # 整理欄位顯示順序
        final_cols = [
            '日期', '小時', '版位編號', 'Total Tracked Ads', 'Eligible Ads for Viewability', 
            'Measured Ads', '% Measured Ads', 'Viewable Impressions', '% Viewable Impressions', 
            'Non-Viewable Ads', '% Non-Viewable Ads', 'Average Time In View (Sec)'
        ]
        hourly_df = hourly_df[final_cols]
        
        # 5. 寫入檔案
        print(f"📤 正在儲存時報至: {output_path}")
        hourly_df.to_excel(output_path, index=False)
        
        print(f"✅ 時報產出完成！總行數: {len(hourly_df)}")
        return output_path

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        aggregate_hourly(file_path)
    else:
        print("💡 請提供 Excel 檔案路徑。範例：python3 aggregate_hourly.py 檔案路徑.xlsx")
