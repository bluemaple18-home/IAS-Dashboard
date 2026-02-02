import os
import re
import pandas as pd

def process_00_v4(input_path, output_path):
    print(f"🚀 正在執行 V4 強力修復版: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            full_text = f.read()

        single_line = " ".join([l.strip() for l in full_text.split('\n') if l.strip()])
        rows = re.split(r'(?=\d{8},\d{1,2},)', single_line)
        final_rows = [r.strip() for r in rows if r.strip() and re.match(r'\d{8},', r.strip())]
        
        # 00 號總表欄位 (對齊 IAS 整合大表)
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
        
        # 寫入檔案，並確保數據列的長度與表頭一致
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(",".join(header_raw) + "\n")
            for row in final_rows:
                parts = row.split(',')
                # 如果這行數據太長或太短，我們強行切斷或補齊，防止 pandas 讀取時 index 混亂
                if len(parts) > len(header_raw):
                    parts = parts[:len(header_raw)]
                elif len(parts) < len(header_raw):
                    parts = parts + ["0"] * (len(header_raw) - len(parts))
                f.write(",".join(parts) + "\n")
                
        print(f"✅ V4 修正完成！共處理 {len(final_rows)} 筆。小時欄位已嘗試對齊。")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    process_00_v4("/Users/matt/IAS-Dashboard/data/temp_00.txt", "/Users/matt/IAS-Dashboard/data/00_全媒體整合報表_版位級別.csv")
