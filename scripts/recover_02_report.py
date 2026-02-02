import os
import re

def process_02_report(input_path, output_path):
    print(f"🚀 正在處理「無效流量 (IVT)」文字檔案: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            full_text = f.read()

        single_line = " ".join([l.strip() for l in full_text.split('\n') if l.strip()])
        
        # 搜尋 2026 開頭的數據列 
        # IVT 標準欄位通常很多，切割模式同 01/03 報表
        rows = re.split(r'(?=\d{8},\d{1,2},)', single_line)
        final_rows = [r.strip() for r in rows if r.strip() and re.match(r'\d{8},', r.strip())]
        
        # 02 報表標準欄位定義 
        header = "日期,小時,供應商名稱,網站,網站名稱,版位編號,版位名稱,antifroud,知名媒體,子聯播網,Total Tracked Ads,Eligible Ads for Invalid Traffic,Invalid Traffic Ads,% Invalid Traffic,General Invalid Traffic (GIVT) Ads,% General Invalid Traffic (GIVT),Sophisticated Invalid Traffic (SIVT) Ads,% Sophisticated Invalid Traffic (SIVT)"
        
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(header + "\n")
            for row in final_rows:
                f.write(row + "\n")
                
        print(f"📊 無效流量報表處理完成！共擷取到 {len(final_rows)} 筆數據")
        if len(final_rows) > 0:
             print(f"👀 對齊檢查: {final_rows[0][:150]}...")
        print(f"✅ CSV 已存至: {output_path}")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    txt_file = "/Users/matt/IAS-Dashboard/data/temp_02.txt"
    csv_file = "/Users/matt/IAS-Dashboard/data/02_無效流量整合報表_版位級別.csv"
    process_02_report(txt_file, csv_file)
