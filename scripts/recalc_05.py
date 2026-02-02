import pandas as pd
import numpy as np

def recalc_05():
    file_path = "/Users/matt/IAS-Dashboard/data/05_優質曝光整合報表_版位級別.csv"
    print(f"🛠️ 正在重算 05 報表: {file_path}")
    try:
        df = pd.read_csv(file_path)
        # 強制轉換基數
        cols_to_fix = ['Eligible ads for quality Impressions', 'Quality Ads', 'Non-quality Ads']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        # 重新計算百分比
        base = df['Eligible ads for quality Impressions']
        df['Quality Ads rate'] = np.where(base > 0, (df['Quality Ads'] / base) * 100, 0)
        df['Non-quality Ads rate'] = 100 - df['Quality Ads rate']
        
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print("✅ 05 報表百分比重算完成！")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__": recalc_05()
