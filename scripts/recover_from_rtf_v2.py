import os
import re

def convert_rtf_to_csv_v2(input_path, output_path):
    print(f"🚀 正在處理 RTF 檔案 (V2 中文強化版): {input_path}")
    try:
        # 使用 utf-8 讀取，並處理 RTF 特有的轉義符
        with open(input_path, 'r', encoding='ascii', errors='ignore') as f:
            content = f.read()

        # 1. 先處理 RTF 中的 hex 編碼中文 (例如 \'b4\'fa)
        def hex_to_char(match):
            hex_str = match.group(0).replace("\\'", "")
            try:
                return bytes.fromhex(hex_str).decode('cp950') # 台灣常用 RTF 編碼通常是 CP950
            except:
                return ""

        # 搜尋像 \'b4\'fa 的連續編碼
        processed_hex = re.sub(r"(\\\'([0-9a-fA-F]{2}))+", hex_to_char, content)

        # 2. 移除 RTF 控制碼，但保留剛才解碼出來的中文
        text_only = re.sub(r'\\([a-z]{1,32})(-?\d{1,10})?[ ]?|\\\{|\\\}|\\', '', processed_hex)
        
        # 3. 處理行對齊 (與 V1 邏輯相同)
        full_text = " ".join([l.strip() for l in text_only.strip().split('\n') if l.strip()])
        rows = re.split(r'(?=\d{8},\d{1,2},)', full_text)
        
        final_rows = [r.strip() for r in rows if r.strip() and re.match(r'\d{8},', r.strip())]
        
        # 4. 寫入 CSV
        header = "日期,小時,供應商名稱,網站,網站名稱,版位編號,版位名稱,antifroud,知名媒體,子聯播網,Total Tracked Ads,Reduced Value Inventory (RVI) Ads,Incentivized Browsing (RVI) Ads,Proxy Server (RVI) Ads,seeThrough Ads,Invisible URL Ads,Total Eligible Ads for Site Quality,% Reduced Value Inventory (RVI) Ads,% seeThrough Ads,Invisible URL rate,% Incentivized Browsing (RVI) Ads,% Proxy Server (RVI) Ads"
        
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(header + "\n")
            for row in final_rows:
                f.write(row + "\n")
                
        print(f"📊 處理完成！擷取到 {len(final_rows)} 筆數據")
        if len(final_rows) > 0:
            print(f"👀 第一筆預覽: {final_rows[0][:100]}...")
        print(f"✅ CSV 已存至: {output_path}")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    rtf_file = "/Users/matt/IAS-Dashboard/data/03_網站品質整合報表_版位級別.rtf"
    csv_file = "/Users/matt/IAS-Dashboard/data/03_網站品質整合報表_版位級別.csv"
    convert_rtf_to_csv_v2(rtf_file, csv_file)
