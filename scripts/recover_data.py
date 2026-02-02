import pandas as pd
import os

def convert_long_row_to_csv(input_path, output_path):
    print(f"🚀 正在讀取 Excel: {input_path}")
    try:
        # 1. 讀取 Excel，不預設表頭
        df = pd.read_excel(input_path, header=None)
        
        if df.empty:
            print("❌ 檔案是空的")
            return
        
        # 2. 取得第一列的所有資料
        # 您提到「裡面第一列有全部的資料」，推測這是一列長長的、用逗號或空格隔開的字串
        raw_content = str(df.iloc[0, 0])
        print(f"📄 讀取到原始內容長度: {len(raw_content)}")
        
        # 3. 處理格式
        # 觀察之前貼上的內容，是 CSV 格式 (逗號隔開)，每行數據之間可能有空格或換行
        # 我們將其當作 CSV 處理
        from io import StringIO
        
        # 先嘗試用 StringIO 包裝，然後用 pandas 讀取
        cleaned_df = pd.read_csv(StringIO(raw_content))
        
        # 4. 存檔
        print(f"📊 成功轉換成 {len(cleaned_df)} 筆數據")
        cleaned_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✅ CSV 已存至: {output_path}")
        
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    input_file = "/Users/matt/IAS-Dashboard/data/活頁簿1.xlsx"
    output_file = "/Users/matt/IAS-Dashboard/data/recovered_all_data.csv"
    convert_long_row_to_csv(input_file, output_file)
