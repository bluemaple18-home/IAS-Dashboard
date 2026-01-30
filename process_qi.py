import pandas as pd
import numpy as np
import os

def process_qi_hourly(input_path):
    print(f"🚀 開始處理 Quality Impressions 檔案: {input_path}")
    output_temp = input_path.replace(".xlsx", "_hourly_report.xlsx")
    
    try:
        df_raw = pd.read_excel(input_path, skiprows=1, dtype={'DIMENSIONS': str})
        headers = df_raw.iloc[0].values
        df = df_raw.iloc[1:].copy()
        df.columns = headers
        
        target_col = 'Placement Id'
        print("✂️ 正在進行欄位拆解與數值轉換...")
        df[target_col] = df[target_col].astype(str)
        split_parts = df[target_col].str.split('_', expand=True)
        timestamp = split_parts[0]
        
        df['日期'] = timestamp.str.slice(0, 8)
        df['小時'] = timestamp.str.slice(8, 10)
        df['版位編號'] = split_parts[1]
        
        # 數值化
        numeric_cols = [c for c in df.columns if '%' not in str(c) and 'rate' not in str(c).lower() and c not in ['日期', '小時', '版位編號', 'Placement Id']]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        print("📊 正在產出時報物件 (加總各項數值)...")
        agg_logic = {c: 'sum' for c in numeric_cols}
        hourly_df = df.groupby(['日期', '小時', '版位編號'], as_index=False).agg(agg_logic)
        
        print("🧮 正在重新計算百分比公式...")
        den = 'Eligible ads for quality Impressions'
        
        if den in hourly_df.columns:
            # Quality Ads rate
            if 'Quality Ads' in hourly_df.columns:
                hourly_df['Quality Ads rate'] = (hourly_df['Quality Ads'] / hourly_df[den]).fillna(0) * 100
            
            # Non-quality Ads rate
            if 'Non-quality Ads' in hourly_df.columns:
                hourly_df['Non-quality Ads rate'] = (hourly_df['Non-quality Ads'] / hourly_df[den]).fillna(0) * 100

        hourly_df = hourly_df.replace([np.inf, -np.inf], 0)
        print(f"📤 儲存過渡時報檔案...")
        hourly_df.to_excel(output_temp, index=False)
        return output_temp

    except Exception as e:
        print(f"❌ 處理失敗: {e}")
        return None

if __name__ == "__main__":
    path = '/Users/mattkuo/Downloads/sample--Quality-Impressions_20260125-20260126.xlsx'
    process_qi_hourly(path)
