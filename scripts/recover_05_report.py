import os
import re

def process_05_report(input_path, output_path):
    print(f"🚀 正在處理「優質曝光」文字檔案 (正確欄位版): {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            full_text = f.read()

        single_line = " ".join([l.strip() for l in full_text.split('\n') if l.strip()])
        
        # 搜尋 2026 開頭的數據列
        rows = re.split(r'(?=\d{8},\d{1,2},)', single_line)
        final_rows = [r.strip() for r in rows if r.strip() and re.match(r'\d{8},', r.strip())]
        
        # 根據 PM 提供的新欄位定義修正
        header = "日期,小時,供應商名稱,網站,網站名稱,版位編號,版位名稱,antifroud,知名媒體,子聯播網,Total Tracked Ads,Eligible ads for quality Impressions,Quality Ads,Non-quality Ads,Quality Ads rate,Non-quality Ads rate"
        
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(header + "\n")
            for row in final_rows:
                f.write(row + "\n")
                
        print(f"📊 優質曝光報表處理完成！共擷取到 {len(final_rows)} 筆數據")
        if len(final_rows) > 0:
             print(f"👀 第一筆對齊檢查: {final_rows[0][:150]}...")
        print(f"✅ 已修正 CSV 存至: {output_path}")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    txt_file = "/Users/matt/IAS-Dashboard/data/temp_05.txt"
    csv_file = "/Users/matt/IAS-Dashboard/data/05_優質曝光整合報表_版位級別.csv"
    process_05_report(txt_file, csv_file)
