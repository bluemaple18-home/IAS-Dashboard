import math
import pandas as pd
import numpy as np
import os
import glob
from format_reports import format_excel

def split_and_format():
    # Find all 5 integrated reports
    source_dir = "/Users/matt/Downloads"
    patterns = ["01_*.xlsx", "02_*.xlsx", "03_*.xlsx", "04_*.xlsx", "05_*.xlsx"]
    
    files_to_process = []
    for p in patterns:
        files_to_process.extend(glob.glob(os.path.join(source_dir, p)))
    
    # Filter out files that already look like parts (contain '_part')
    files_to_process = [f for f in files_to_process if "_part" not in f]
    
    if not files_to_process:
        print("❌ 未找到目標檔案 (01~05_*.xlsx)")
        return

    print(f"📦 準備拆分 {len(files_to_process)} 份報表...")
    
    for file_path in files_to_process:
        try:
            filename = os.path.basename(file_path)
            print(f"\n📄 處理中: {filename}")
            
            # Read file
            df = pd.read_excel(file_path)
            total_rows = len(df)
            print(f"   總筆數: {total_rows}")
            
            # Split into 4 parts using slicing
            chunk_size = math.ceil(total_rows / 4)
            parts = []
            for i in range(4):
                start_idx = i * chunk_size
                if start_idx >= total_rows:
                    break
                end_idx = min((i + 1) * chunk_size, total_rows)
                parts.append(df.iloc[start_idx:end_idx])
            
            base_name = os.path.splitext(filename)[0]
            
            for i, part_df in enumerate(parts):
                part_num = i + 1
                new_filename = f"{base_name}_part{part_num}.xlsx"
                new_path = os.path.join(source_dir, new_filename)
                
                print(f"   -> 儲存分卷 {part_num}/4: {new_filename} ({len(part_df)} 筆)")
                part_df.to_excel(new_path, index=False)
                
                # Apply format
                print(f"      🎨 套用格式...")
                format_excel(new_path)
                
        except Exception as e:
            print(f"❌ 處理失敗 {file_path}: {e}")

if __name__ == "__main__":
    split_and_format()
