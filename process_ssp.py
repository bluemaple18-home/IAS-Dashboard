import pandas as pd
import os

def process_ssp(input_path):
    print(f"🚀 開始處理 SSP 檔案: {input_path}")
    
    # 輸出路徑
    output_path = input_path.replace(".xlsx", "_processed.xlsx")
    
    try:
        # 1. 讀取 Excel (指定 header=1 因為第 1 行才是真正的欄位名)
        print("📥 正在讀取資料...")
        df = pd.read_excel(input_path, header=1)
        
        if '時間' not in df.columns:
            print(f"❌ 找不到 '時間' 欄位，現有欄位: {df.columns.tolist()}")
            return
            
        print("✂️ 正在進行時間欄位拆解...")
        
        # 確保 '時間' 是字串格式處理，避免自動轉為 datetime 導致格式丟失
        time_str = df['時間'].astype(str)
        
        # 邏輯: "2026-01-26 00:00:00"
        # 拆分日期與時間部分
        datetime_split = time_str.str.split(' ', expand=True)
        # datetime_split[0] -> "2026-01-26"
        # datetime_split[1] -> "00:00:00"
        
        date_part = datetime_split[0].str.replace('-', '', regex=False)
        
        time_parts = datetime_split[1].str.split(':', expand=True)
        # time_parts[0] -> "00" (時)
        # time_parts[1] -> "00" (分)
        # time_parts[2] -> "00" (秒)
        
        # 建立新欄位
        df['日期'] = date_part
        df['小時'] = time_parts[0]
        df['分秒'] = time_parts[1] + time_parts[2]
        
        # 檢查是否為空或處理異常 (補齊)
        df['日期'] = df['日期'].fillna('')
        df['小時'] = df['小時'].fillna('00')
        df['分秒'] = df['分秒'].fillna('0000')
        
        # 3. 調整欄位順序 (將新欄位移到最前面)
        cols = ['日期', '小時', '分秒'] + [c for c in df.columns if c not in ['日期', '小時', '分秒']]
        df = df[cols]
        
        # 4. 寫入新檔案
        print(f"📤 正在儲存至: {output_path}")
        df.to_excel(output_path, index=False)
        
        print("✅ SSP 資料處理完成！")
        return output_path

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    file_path = "/Users/matt/Downloads/SSP_2026-01-26_2026-01-27_(一般媒體).xlsx"
    process_ssp(file_path)
