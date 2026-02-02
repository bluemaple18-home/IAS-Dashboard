import os
import re

def process_clean_text(input_path, output_path):
    print(f"🚀 正在處理純文字檔案: {input_path}")
    try:
        # 讀取剛才 textutil 轉換好的文字檔 (UTF-8)
        with open(input_path, 'r', encoding='utf-8') as f:
            full_text = f.read()

        # 把換行符號拿掉，變成一整串，再重新切割
        # 因為有些數據可能在轉換時被斷行
        single_line = " ".join([l.strip() for l in full_text.split('\n') if l.strip()])
        
        # 搜尋 "2026xxxx,xx," 格式作為開頭切割
        rows = re.split(r'(?=\d{8},\d{1,2},)', single_line)
        
        final_rows = [r.strip() for r in rows if r.strip() and re.match(r'\d{8},', r.strip())]
        
        # 寫入 CSV
        header = "日期,小時,供應商名稱,網站,網站名稱,版位編號,版位名稱,antifroud,知名媒體,子聯播網,Total Tracked Ads,Reduced Value Inventory (RVI) Ads,Incentivized Browsing (RVI) Ads,Proxy Server (RVI) Ads,seeThrough Ads,Invisible URL Ads,Total Eligible Ads for Site Quality,% Reduced Value Inventory (RVI) Ads,% seeThrough Ads,Invisible URL rate,% Incentivized Browsing (RVI) Ads,% Proxy Server (RVI) Ads"
        
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(header + "\n")
            for row in final_rows:
                f.write(row + "\n")
                
        print(f"📊 完美！從中文字串中擷取到 {len(final_rows)} 筆數據")
        if len(final_rows) > 0:
            print(f"👀 中文預覽: {final_rows[0][:100]}...")
        print(f"✅ CSV 已存至: {output_path}")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    txt_file = "/Users/matt/IAS-Dashboard/data/temp_output.txt"
    csv_file = "/Users/matt/IAS-Dashboard/data/03_網站品質整合報表_版位級別.csv"
    process_clean_text(txt_file, csv_file)
