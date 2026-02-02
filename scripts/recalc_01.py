import pandas as pd
import numpy as np

def recalc_01():
    file_path = "/Users/matt/IAS-Dashboard/data/01_可視性廣告整合報表_版位級別.csv"
    print(f"🛠️ 正在重算 01 報表: {file_path}")
    try:
        df = pd.read_csv(file_path)
        # 強制轉換基數
        cols_to_fix = ['Eligible Ads for Viewability', 'Measured Ads', 'Viewable Impressions', 'Non-Viewable Ads']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        # 重新計算百分比
        df['% Measured Ads'] = np.where(df['Eligible Ads for Viewability'] > 0, (df['Measured Ads'] / df['Eligible Ads for Viewability']) * 100, 0)
        df['% Viewable Impressions'] = np.where(df['Measured Ads'] > 0, (df['Viewable Impressions'] / df['Measured Ads']) * 100, 0)
        df['% Non-Viewable Ads'] = 100 - df['% Viewable Impressions']
        
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print("✅ 01 報表百分比重算完成！")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__": recalc_01()
