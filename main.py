import pandas as pd
import os

def process_excel(input_path):
    print(f"🚀 開始處理檔案: {input_path}")
    
    # 輸出路徑
    output_path = input_path.replace(".xlsx", "_processed.xlsx")
    
    try:
        # 1. 讀取 Excel (跳過第一行非標準資訊，將第二行作為表頭)
        # 注意: 指定 dtype={'DIMENSIONS': str} 確保原始 ID 不會被科學符號化
        print("📥 正在讀取資料 (這可能需要一點時間)...")
        df = pd.read_excel(input_path, skiprows=1, dtype={'DIMENSIONS': str})
        
        # 2. 針對 'DIMENSIONS' (即 Placement Id) 進行處理
        # 原始格式範例: 20260127100448_12579
        print("✂️ 正在拆解欄位...")
        
        # 先轉成字串並處理可能的空值
        df['DIMENSIONS'] = df['DIMENSIONS'].astype(str)
        
        # 拆解底線
        split_parts = df['DIMENSIONS'].str.split('_', expand=True)
        # split_parts[0] 是時間戳記 20260127100448
        # split_parts[1] 是版位編號 12579
        
        timestamp = split_parts[0]
        
        # 建立四個新欄位 (強制為文字)
        df['日期'] = timestamp.str.slice(0, 8)
        df['小時'] = timestamp.str.slice(8, 10)
        df['分秒'] = timestamp.str.slice(10, 14)
        df['版位編號'] = split_parts[1]
        
        # 3. 調整欄位順序 (將新欄位移到最前面)
        cols = ['日期', '小時', '分秒', '版位編號'] + [c for c in df.columns if c not in ['日期', '小時', '分秒', '版位編號']]
        df = df[cols]
        
        # 4. 寫入新檔案
        print(f"📤 正在儲存至: {output_path}")
        df.to_excel(output_path, index=False)
        
        print("✅ 處理完成！")
        return output_path

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        return None

if __name__ == "__main__":
    file_path = "/Users/matt/Downloads/sample-Viewability_20260125-20260126.xlsx"
    process_excel(file_path)
