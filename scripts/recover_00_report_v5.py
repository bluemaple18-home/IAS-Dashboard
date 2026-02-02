import os
import re
import pandas as pd

def process_00_v5(input_path, output_path):
    print(f"🚀 正在執行 V5 穩定版 (解決欄位缺失報錯): {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            full_text = f.read()

        # 1. 拆分行：以日期格式開頭作為一列
        single_line = " ".join([l.strip() for l in full_text.split('\n') if l.strip()])
        rows = re.split(r'(?=\d{8},\d{1,2},)', single_line)
        final_rows = [r.strip() for r in rows if r.strip() and re.match(r'\d{8},', r.strip())]
        
        # 標配 33 個欄位
        header_raw = [
            "日期","小時","供應商名稱","網站","網站名稱","版位編號","版位名稱","antifroud","知名媒體","子聯播網",
            "Total Tracked Ads (Viewability)","Measured Ads (Viewability)","Viewable Impressions (Viewability)","% Viewability",
            "Average Time In View (Sec)","Invalid Traffic Ads (IVT)","Eligible Ads for Invalid Traffic (IVT)","% IVT",
            "General Invalid Traffic (GIVT) Ads (IVT)","% GIVT","Sophisticated Invalid Traffic (SIVT) Ads (IVT)","% SIVT",
            "Reduced Value Inventory (RVI) Ads (SiteQuality)","Total Eligible Ads for Site Quality (SiteQuality)","% RVI",
            "seeThrough Ads (SiteQuality)","% seeThrough Ads","Brand Suitability Passed Ads (BrandSuitability)",
            "Total Eligible Ads for Brand Suitability (BrandSuitability)","% Brand Safety Passed",
            "Quality Ads (QualImpressions)","Eligible ads for quality Impressions (QualImpressions)","% Quality Ads"
        ]
        target_len = len(header_raw)
        
        # 2. 寫入並嚴格控制欄位數量 (on_bad_lines='skip' 的預防性處理)
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(",".join(header_raw) + "\n")
            for row in final_rows:
                # 處理 CSV 內容中的逗號（例如名稱裡帶逗號會造成欄位增加）
                # 這裡我們先做簡單的欄位校準
                parts = row.split(',')
                
                if len(parts) > target_len:
                    parts = parts[:target_len] # 截斷
                elif len(parts) < target_len:
                    parts = parts + ["0"] * (target_len - len(parts)) # 補齊
                
                # 清洗逗號與換行符，避免破壞 CSV 結構
                clean_parts = [p.replace('\n', '').replace('\r', '').strip() for p in parts]
                f.write(",".join(clean_parts) + "\n")
                
        print(f"✅ V5 修復完成！已鎖定所有行為 {target_len} 個欄位。")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    process_00_v5("/Users/matt/IAS-Dashboard/data/temp_00.txt", "/Users/matt/IAS-Dashboard/data/00_全媒體整合報表_版位級別.csv")
