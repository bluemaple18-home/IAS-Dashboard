import os
import re

def process_00_total_report(input_path, output_path):
    print(f"🚀 正在處理「全媒體整合總表」檔案: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            full_text = f.read()

        single_line = " ".join([l.strip() for l in full_text.split('\n') if l.strip()])
        
        # 搜尋 2026 開頭的數據列 
        rows = re.split(r'(?=\d{8},\d{1,2},)', single_line)
        final_rows = [r.strip() for r in rows if r.strip() and re.match(r'\d{8},', r.strip())]
        
        # 00 號總表：集結所有關鍵指標的超長欄位
        header = "日期,小時,供應商名稱,網站,網站名稱,版位編號,版位名稱,antifroud,知名媒體,子聯播網,Total Tracked Ads (Viewability),Measured Ads (Viewability),Viewable Impressions (Viewability),% Viewability,Average Time In View (Sec),Invalid Traffic Ads (IVT),Eligible Ads for Invalid Traffic (IVT),% IVT,General Invalid Traffic (GIVT) Ads (IVT),% GIVT,Sophisticated Invalid Traffic (SIVT) Ads (IVT),% SIVT,Reduced Value Inventory (RVI) Ads (SiteQuality),Total Eligible Ads for Site Quality (SiteQuality),% RVI,seeThrough Ads (SiteQuality),% seeThrough Ads,Brand Suitability Passed Ads (BrandSuitability),Total Eligible Ads for Brand Suitability (BrandSuitability),% Brand Safety Passed,Quality Ads (QualImpressions),Eligible ads for quality Impressions (QualImpressions),% Quality Ads"
        
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(header + "\n")
            for row in final_rows:
                f.write(row + "\n")
                
        print(f"📊 整合總表處理完成！共擷取到 {len(final_rows)} 筆數據")
        if len(final_rows) > 0:
             print(f"👀 總表對齊檢查 (前150字): {final_rows[0][:150]}...")
        print(f"✅ 核心 CSV 已存至: {output_path}")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    txt_file = "/Users/matt/IAS-Dashboard/data/temp_00.txt"
    csv_file = "/Users/matt/IAS-Dashboard/data/00_全媒體整合報表_版位級別.csv"
    process_00_total_report(txt_file, csv_file)
