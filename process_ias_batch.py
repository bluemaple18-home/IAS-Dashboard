import pandas as pd
import os
import glob
from merge_reports import merge_reports

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def process_single_file(input_path):
    print(f"\n🚀 Processing: {os.path.basename(input_path)}")
    
    # Target directory
    output_dir = DATA_DIR
    os.makedirs(output_dir, exist_ok=True)
    hourly_name = os.path.basename(input_path).replace(".xlsx", "_hourly_report.xlsx")
    hourly_path = os.path.join(output_dir, hourly_name)
    
    try:
        # 1. Smart Header Detection
        df_scan = pd.read_excel(input_path, nrows=5)
        header_row_idx = 0
        for i, row in df_scan.iterrows():
            row_str = " ".join(row.astype(str).tolist())
            if "Total Tracked Ads" in row_str or "Measured Ads" in row_str or "Placement Id" in row_str:
                header_row_idx = i + 1
                break
        
        df = pd.read_excel(input_path, skiprows=header_row_idx)
        
        # 2. DIMENSIONS Extraction
        id_col = 'DIMENSIONS' if 'DIMENSIONS' in df.columns else df.columns[0]
        df['DIM'] = df[id_col].astype(str).str.strip()
        
        def extract_date(x):
            if '_' not in str(x): return '20260413'
            time_part = str(x).split('_')[0]
            if len(time_part) == 14 and time_part.startswith('202'):
                return time_part[:8]
            elif len(time_part) == 13 and time_part.isdigit():
                try:
                    return pd.to_datetime(int(time_part), unit='ms').strftime('%Y%m%d')
                except: return '20260413'
            return '20260413'

        def extract_hour(x):
            if '_' not in str(x): return '00'
            time_part = str(x).split('_')[0]
            if len(time_part) == 14 and time_part.startswith('202'):
                return time_part[8:10]
            elif len(time_part) == 13 and time_part.isdigit():
                try:
                    return pd.to_datetime(int(time_part), unit='ms').strftime('%H')
                except: return '00'
            return '00'
            
        def extract_id(x):
            if '_' in str(x): return str(x).split('_', 1)[1]
            return str(x)
            
        df['日期'] = df['DIM'].apply(extract_date)
        df['小時'] = df['DIM'].apply(extract_hour)
        df['版位編號'] = df['DIM'].apply(extract_id)
        
        # 3. Numeric Conversion & Aggregation
        # Find numeric columns (all except fixed ones)
        fixed_cols = ['日期', '小時', '版位編號', 'DIM', id_col]
        numeric_cols = [c for c in df.columns if c not in fixed_cols and 'Unnamed' not in str(c)]
        
        agg_ops = {}
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if 'rate' in col.lower() or 'Average' in col or '%' in col:
                agg_ops[col] = 'mean'
            else:
                agg_ops[col] = 'sum'
                
        print(f"🔄 Grouping {len(df)} rows...")
        hourly_df = df.groupby(['日期', '小時', '版位編號'], as_index=False).agg(agg_ops)
        hourly_df.to_excel(hourly_path, index=False)
        print(f"✅ Hourly report created: {hourly_name}")
        
        return hourly_path

    except Exception as e:
        print(f"❌ Error processing {input_path}: {e}")
        return None

def run_batch():
    source_dir = "/Users/mattkuo/Downloads"
    ssp_path = "/Users/mattkuo/Downloads/SSP_2026-04-01_2026-04-14_(一般媒體).xlsx"
    files = glob.glob(os.path.join(source_dir, "sample-*20260315-20260413.xlsx"))
    
    results = []
    missed_ids = set()
    
    for f in files:
        hourly_path = process_single_file(f)
        if hourly_path:
            integrated_path = merge_reports(hourly_path, ssp_path)
            if integrated_path:
                print(f"✨ Integrated report: {os.path.basename(integrated_path)}")
                
                # Collect missed IDs for analysis later
                df_res = pd.read_excel(integrated_path)
                if '供應商名稱' in df_res.columns:
                    blank_ids = df_res[df_res['供應商名稱'].isna()]['版位編號'].unique().tolist()
                    missed_ids.update(blank_ids)
    
    # Final step: Save missed IDs for PM
    if missed_ids:
        missed_df = pd.DataFrame({'Missed_Placement_ID': sorted(list(missed_ids))})
        missed_path = os.path.join(DATA_DIR, "MISSED_PLACEMENTS_FOR_PM.xlsx")
        missed_df.to_excel(missed_path, index=False)
        print(f"\n📂 Missed IDs list saved to: {missed_path}")

if __name__ == "__main__":
    run_batch()
