import pandas as pd
import numpy as np
import os

def process_ivt_hourly(input_path):
    print(f"🚀 開始處理 Invalid Traffic 檔案: {input_path}")
    output_temp = input_path.replace(".xlsx", "_hourly_report.xlsx")
    
    try:
        # 1. 讀取原始資料 (跳過前兩行，指定類型確保 ID 完整)
        # 注意: Invalid Traffic 的 sub-header 在第 2 行 (skip 1, header is next line)
        df_raw = pd.read_excel(input_path, skiprows=1, dtype={'DIMENSIONS': str})
        headers = df_raw.iloc[0].values
        df = df_raw.iloc[1:].copy()
        df.columns = headers
        
        target_col = 'Placement Id'
        if target_col not in df.columns:
            df.columns = [str(c).strip() for c in df.columns]
        
        print("✂️ 正在進行欄位拆解與數值轉換...")
        df[target_col] = df[target_col].astype(str)
        split_parts = df[target_col].str.split('_', expand=True)
        timestamp = split_parts[0]
        
        df['日期'] = timestamp.str.slice(0, 8)
        df['小時'] = timestamp.str.slice(8, 10)
        df['版位編號'] = split_parts[1]
        
        # 數值化 (排除 ID 欄位)
        numeric_cols = [c for c in df.columns if '%' not in str(c) and c not in ['日期', '小時', '版位編號', 'Placement Id']]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        # 2. 執行聚合 (Group By 日期, 小時, 版位編號)
        print("📊 正在產出時報物件 (加總各項數值)...")
        agg_logic = {c: 'sum' for c in numeric_cols}
        hourly_df = df.groupby(['日期', '小時', '版位編號'], as_index=False).agg(agg_logic)
        
        # 3. 重新計算百分比指標 (根據推導公式)
        print("🧮 正在重新計算百分比公式...")
        # 分母：Eligible Ads for Invalid Traffic
        den = 'Eligible Ads for Invalid Traffic'
        
        if den in hourly_df.columns:
            # % Eligible (相對於 Total Tracked)
            if 'Total Tracked Ads' in hourly_df.columns:
                hourly_df['% Eligible for Invalid Traffic'] = (hourly_df[den] / hourly_df['Total Tracked Ads']).fillna(0) * 100
                
            # % Invalid Traffic Ads = IVT / Eligible
            if 'Invalid Traffic Ads' in hourly_df.columns:
                hourly_df['% Invalid Traffic Ads'] = (hourly_df['Invalid Traffic Ads'] / hourly_df[den]).fillna(0) * 100
            
            # % GIVT = GIVT / Eligible
            if 'General Invalid Traffic (GIVT) Ads' in hourly_df.columns:
                 hourly_df['% General Invalid Traffic (GIVT) Ads'] = (hourly_df['General Invalid Traffic (GIVT) Ads'] / hourly_df[den]).fillna(0) * 100
            
            # % SIVT = SIVT / Eligible
            if 'Sophisticated Invalid Traffic (SIVT) Ads' in hourly_df.columns:
                 hourly_df['% Sophisticated Invalid Traffic (SIVT) Ads'] = (hourly_df['Sophisticated Invalid Traffic (SIVT) Ads'] / hourly_df[den]).fillna(0) * 100
                 
            # 子項比例 (Bots, Domain Spoofing, Hidden) -> 通常也是以 Eligible 或 SIVT 為分母? 
            # 根據剛分析，IVT 報表的個別 % 欄位分母通常是 Eligible
            for sub in ['Bots (SIVT) Ads', 'Domain Spoofing (SIVT) Ads', 'Hidden Ads (SIVT) Ads']:
                if sub in hourly_df.columns:
                    col_name = f"% {sub}"
                    hourly_df[col_name] = (hourly_df[sub] / hourly_df[den]).fillna(0) * 100

        # 清除 inf
        hourly_df = hourly_df.replace([np.inf, -np.inf], 0)
        
        print(f"📤 儲存過渡時報檔案...")
        hourly_df.to_excel(output_temp, index=False)
        return output_temp

    except Exception as e:
        print(f"❌ 處理失敗: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import sys
    path = '/Users/matt/Downloads/sample--Invalid-Traffic_20260125-20260126.xlsx'
    process_ivt_hourly(path)
