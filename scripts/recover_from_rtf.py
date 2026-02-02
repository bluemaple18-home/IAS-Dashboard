import os
import re

def convert_rtf_to_csv(input_path, output_path):
    print(f"🚀 正在處理 RTF 檔案: {input_path}")
    try:
        with open(input_path, 'r', encoding='ascii', errors='ignore') as f:
            content = f.read()

        # RTF 檔案內容通常包含大量的 \{\} 控制碼，我們只保留文本部分
        # 簡單的方法是移除所有 \開頭的控制指令
        text_only = re.sub(r'\\([a-z]{1,32})(-?\d{1,10})?[ ]?|\\\'([0-9a-f]{2})|\\\{|\\\}|\\', '', content)
        
        # 移除前後空白，並嘗試尋找 20260126 這種日期格式來識別行
        lines = text_only.strip().split('\n')
        
        # 過濾空行並清洗
        processed_lines = []
        for line in lines:
            line = line.strip()
            if line:
                processed_lines.append(line)

        # 重新拼接並根據日期模式切割，確保一行就是一份資料
        full_text = " ".join(processed_lines)
        
        # 關鍵在於：日期,小時,供應商... 這種格式
        # 我們搜尋 "2026" (年份) 作為每一列的開頭特徵
        # 這裡用正則表達式切分，日期通常是 8 位數字開頭
        rows = re.split(r'(?=\d{8},\d{1,2},)', full_text)
        
        # 提取真正的數據列
        final_rows = [r.strip() for r in rows if r.strip() and re.match(r'\d{8},', r.strip())]
        
        # 寫入 CSV
        header = "日期,小時,供應商名稱,網站,網站名稱,版位編號,版位名稱,antifroud,知名媒體,子聯播網,Total Tracked Ads,Reduced Value Inventory (RVI) Ads,Incentivized Browsing (RVI) Ads,Proxy Server (RVI) Ads,seeThrough Ads,Invisible URL Ads,Total Eligible Ads for Site Quality,% Reduced Value Inventory (RVI) Ads,% seeThrough Ads,Invisible URL rate,% Incentivized Browsing (RVI) Ads,% Proxy Server (RVI) Ads"
        
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(header + "\n")
            for row in final_rows:
                f.write(row + "\n")
                
        print(f"📊 處理完成！從 RTF 中擷取到 {len(final_rows)} 筆數據")
        print(f"✅ CSV 已存至: {output_path}")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    rtf_file = "/Users/matt/IAS-Dashboard/data/03_網站品質整合報表_版位級別.rtf"
    csv_file = "/Users/matt/IAS-Dashboard/data/03_網站品質整合報表_版位級別.csv"
    convert_rtf_to_csv(rtf_file, csv_file)
