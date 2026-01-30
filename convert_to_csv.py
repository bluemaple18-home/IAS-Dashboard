import pandas as pd
import os
import glob

def convert_to_csv():
    # Find all *_final_integrated.* files
    source_dir = "/Users/mattkuo/Downloads"
    # Target specific integrated files (both xlsx and csv)
    patterns = ["*_final_integrated.xlsx", "*_final_integrated.csv"]
    
    files_to_process = []
    for p in patterns:
        files_to_process.extend(glob.glob(os.path.join(source_dir, p)))
        
    print(f"📦 準備轉換 {len(files_to_process)} 個檔案為 CSV...")
    
    for file_path in files_to_process:
        convert_file_to_csv(file_path)

def get_chinese_name(filename):
    mapping = {
        'Viewability': '01_可視性廣告整合報表_版位級別',
        'Invalid-Traffic': '02_無效流量整合報表_版位級別',
        'Site-Quality': '03_網站品質整合報表_版位級別',
        'Brand-Suitability': '04_品牌安全性整合報表_版位級別',
        'Quality-Impressions': '05_優質曝光整合報表_版位級別'
    }
    
    for key, name in mapping.items():
        if key in filename:
            return name + ".csv"
            
    # Fallback
    return os.path.splitext(filename)[0] + ".csv"

def convert_file_to_csv(file_path):
    try:
        filename = os.path.basename(file_path)
        # Skip if it's a temporary file opening
        if filename.startswith('~$'):
            return
            
        print(f"\n🔄 轉換中: {filename}")
        
        # KEY CHANGE: Start with read_excel because we know they are Excel files disguised as CSV
        # If it fails, we fall back to read_csv (unlikely for this specific task)
        try:
            df = pd.read_excel(file_path, dtype=object) 
        except Exception:
             # Fallback if genuinely not excel
             df = pd.read_csv(file_path, dtype=object)

        # Formatter function
        for col in df.columns:
            col_str = str(col)
            
            is_percent = '%' in col_str or 'rate' in col_str.lower()
            is_average = 'Average' in col_str or 'Avg' in col_str or '(Sec)' in col_str
            # Skip ID columns from formatting
            is_id = any(x in col_str for x in ['Date', '日期', 'Hour', '小時', 'Id', '編號', 'Code', 'Name', '名稱', 'Site', '網站', 'Supplier', '供應商', 'Dimensions', 'Most Used', '時間', '版位'])
            
            if is_id:
                continue

            if is_percent:
                df[col] = df[col].apply(lambda x: f"{float(x):.2%}" if pd.notnull(pd.to_numeric(x, errors='coerce')) else x)
                
            elif is_average:
                df[col] = df[col].apply(lambda x: f"{float(x):,.2f}" if pd.notnull(pd.to_numeric(x, errors='coerce')) else x)
                
            else:
                df[col] = df[col].apply(lambda x: f"{float(x):,.0f}" if pd.notnull(pd.to_numeric(x, errors='coerce')) else x)
        
        # Determine output filename
        csv_filename = get_chinese_name(filename)
        csv_path = os.path.join(os.path.dirname(file_path), csv_filename)
        
        # UTF-8 with BOM for Excel compatibility in Chinese environment
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"   ✅ 已儲存: {csv_filename}")
            
    except Exception as e:
        print(f"❌ 轉換失敗 {file_path}: {e}")

if __name__ == "__main__":
    convert_to_csv()
