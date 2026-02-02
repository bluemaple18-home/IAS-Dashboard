import os
import glob
from process_qi import process_qi_hourly
from process_bs import process_bs_hourly
from process_sq import process_sq_hourly
from aggregate_hourly import aggregate_hourly # Process Viewability
from merge_reports import merge_reports
from aggregate_to_website import aggregate_to_website

def run_pipeline():
    # Configuration
    ssp_path = '/Users/matt/Downloads/SSP_2026-01-26_2026-01-27_(一般媒體)_processed.xlsx'
    antifraud_path = '/Users/matt/Downloads/abnormal_weekly_processed_v12.xlsx'
    famous_path = '/Users/matt/Downloads/SSP_2025-12-01_2026-01-28_(一般媒體).xlsx'
    subnetwork_path = '/Users/matt/Downloads/SSP_2025-12-01_2026-01-29_(一般媒體).xlsx'
    
    # Target files mapping (Keyword -> Processor)
    # Added Invalid-Traffic back to list as user said "Output 5 files"
    from process_ivt import process_ivt_hourly
    targets = {
        'Quality-Impressions': process_qi_hourly,
        'Brand-Suitability': process_bs_hourly,
        'Site-Quality': process_sq_hourly,
        'Viewability': aggregate_hourly,
        'Invalid-Traffic': process_ivt_hourly
    }
    
    source_dir = "/Users/matt/Downloads"
    
    for key, processor in targets.items():
        print(f"\nExample Pattern: *{key}*_20260125-20260128.xlsx")
        # Find file
        patterns = glob.glob(os.path.join(source_dir, f"*{key}*_20260125-20260128.xlsx"))
        # Filter out ~temp files and already processed files
        files = [f for f in patterns if not os.path.basename(f).startswith('~$') and '_hourly' not in f and '_final' not in f]
        
        if not files:
            print(f"⚠️ 找不到 {key} 的對應原始檔案")
            continue
            
        file_path = files[0] # Take the first match
        print(f"🎯 處理目標: {file_path}")
        
        try:
            # Step 1: Hourly Aggregation
            print(f"   [1/3] 執行小時聚合 ({processor.__name__})...")
            hourly_path = processor(file_path)
            
            if not hourly_path:
                print(f"   ❌ 小時聚合物件產出失敗")
                continue
                
            # Step 2: Merge Dimensions (Added subnetwork_path)
            print(f"   [2/3] 執行維度整合 (Merge)...")
            integrated_path = merge_reports(hourly_path, ssp_path, antifraud_path, famous_path, subnetwork_path)
            
            if not integrated_path:
                print(f"   ❌ 維度整合失敗")
                continue
                
            # Step 3: Website Aggregation (SKIPPED per user request)
            print(f"   [3/3] 暫緩執行網站層級聚合 (User Request: Output placement level first)...")
            print(f"✅ {key} 維度整合完成! 產出: {os.path.basename(integrated_path)}")
                
        except Exception as e:
            print(f"❌ 發生未預期錯誤: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_pipeline()
