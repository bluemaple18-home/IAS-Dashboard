import pandas as pd
import os
from io import StringIO

def inspect_and_recover(input_path, output_path):
    print(f"🚀 正在深度檢查 Excel: {input_path}")
    try:
        # 1. 讀取 Excel (不帶表頭)
        df = pd.read_excel(input_path, header=None)
        
        if df.empty:
            print("❌ 檔案完全是空的")
            return

        # 觀察前幾列內容
        print("--- 內容預覽 ---")
        for i in range(min(len(df), 3)):
            row_val = str(df.iloc[i, 0])
            print(f"Row {i} length: {len(row_val)}")
            print(f"Row {i} preview: {row_val[:100]}...")

        # 2. 拼接所有內容 (如果資料被拆在不同列)
        all_text = ""
        for i in range(len(df)):
            val = df.iloc[i, 0]
            if pd.isna(val): continue
            all_text += str(val) + " " # 補個空格防止接死

        print(f"📄 總拼接長度: {len(all_text)}")

        # 3. 處理被半形/全形逗號或空格混雜的情況
        # 把常見的怪格式正規化
        content = all_text.replace(' 2026', '\n2026') # 根據日期特徵強行換行
        
        # 4. 讀取 CSV
        cleaned_df = pd.read_csv(StringIO(content))
        
        if len(cleaned_df) == 0:
            print("⚠️ 讀取結果依然是 0 筆，可能是表頭識別失敗")
            # 嘗試手動指定表頭
            header = "日期,小時,供應商名稱,網站,網站名稱,版位編號,版位名稱,antifroud,知名媒體,子聯播網,Total Tracked Ads,Reduced Value Inventory (RVI) Ads,Incentivized Browsing (RVI) Ads,Proxy Server (RVI) Ads,seeThrough Ads,Invisible URL Ads,Total Eligible Ads for Site Quality,% Reduced Value Inventory (RVI) Ads,% seeThrough Ads,Invisible URL rate,% Incentivized Browsing (RVI) Ads,% Proxy Server (RVI) Ads"
            full_data = header + "\n" + content
            cleaned_df = pd.read_csv(StringIO(full_data))

        # 5. 存檔
        print(f"📊 最終轉換筆數: {len(cleaned_df)}")
        cleaned_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✅ CSV 已存至: {output_path}")
        
    except Exception as e:
        print(f"❌ 發生深度錯誤: {e}")

if __name__ == "__main__":
    input_file = "/Users/matt/IAS-Dashboard/data/活頁簿1.xlsx"
    output_file = "/Users/matt/IAS-Dashboard/data/recovered_all_data.csv"
    inspect_and_recover(input_file, output_file)
