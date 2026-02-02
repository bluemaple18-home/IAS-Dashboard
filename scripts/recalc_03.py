import pandas as pd
import numpy as np

def recalc_03():
    file_path = "/Users/matt/IAS-Dashboard/data/03_網站品質整合報表_版位級別.csv"
    print(f"🛠️ 正在重算 03 報表: {file_path}")
    try:
        df = pd.read_csv(file_path)
        # 強制轉換基數欄位為數字，移除逗號
        cols_to_fix = ['Total Eligible Ads for Site Quality', 'Reduced Value Inventory (RVI) Ads', 'seeThrough Ads']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        # 重新計算百分比 (避免原本 RTF 帶來的亂碼)
        base = df['Total Eligible Ads for Site Quality']
        df['% Reduced Value Inventory (RVI) Ads'] = np.where(base > 0, (df['Reduced Value Inventory (RVI) Ads'] / base) * 100, 0)
        df['% seeThrough Ads'] = np.where(base > 0, (df['seeThrough Ads'] / base) * 100, 0)
        
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print("✅ 03 報表百分比重算完成！")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__": recalc_03()
