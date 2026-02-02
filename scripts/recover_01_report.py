import os
import re

def process_01_report(input_path, output_path):
    print(f"🚀 正在處理「可視性廣告」文字檔案: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            full_text = f.read()

        single_line = " ".join([l.strip() for l in full_text.split('\n') if l.strip()])
        
        # 搜尋 2026 開頭的數據列 
        rows = re.split(r'(?=\d{8},\d{1,2},)', single_line)
        final_rows = [r.strip() for r in rows if r.strip() and re.match(r'\d{8},', r.strip())]
        
        # 01 報表標準欄位 (根據 aggregate_hourly.py 邏輯對齊)
        header = "日期,小時,供應商名稱,網站,網站名稱,版位編號,版位名稱,antifroud,知名媒體,子聯播網,Total Tracked Ads,Eligible Ads for Viewability,Measured Ads,% Measured Ads,Viewable Impressions,% Viewable Impressions,Non-Viewable Ads,% Non-Viewable Ads,Average Time In View (Sec)"
        
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(header + "\n")
            for row in final_rows:
                f.write(row + "\n")
                
        print(f"📊 可視性報表處理完成！共擷取到 {len(final_rows)} 筆數據")
        if len(final_rows) > 0:
             print(f"👀 第一筆對齊檢查: {final_rows[0][:150]}...")
        print(f"✅ CSV 已存至: {output_path}")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    txt_file = "/Users/matt/IAS-Dashboard/data/temp_01.txt"
    csv_file = "/Users/matt/IAS-Dashboard/data/01_可視性廣告整合報表_版位級別.csv"
    process_01_report(txt_file, csv_file)
