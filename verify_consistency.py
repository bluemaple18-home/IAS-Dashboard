import pandas as pd
import os

def verify_consistency():
    source_dir = "/Users/matt/Downloads"
    files = {
        'Viewability': '01_可視性廣告整合報表_版位級別.csv',
        'IVT': '02_無效流量整合報表_版位級別.csv',
        'SiteQuality': '03_網站品質整合報表_版位級別.csv',
        'BrandSuitability': '04_品牌安全性整合報表_版位級別.csv',
        'QualImpressions': '05_優質曝光整合報表_版位級別.csv'
    }
    
    dfs = {}
    print("📥 正在讀取 5 份報表 (強制使用 Excel 引擎讀取)...")
    
    for name, filename in files.items():
        path = os.path.join(source_dir, filename)
        try:
            # We know they are CSV files now based on 'file' command output
            # Using dtype=str for keys
            df = pd.read_csv(path, dtype={'日期': str, '小時': str, '版位編號': str})
            
            # Clean numeric column
            if 'Total Tracked Ads' in df.columns:
                df['Total Tracked Ads'] = pd.to_numeric(df['Total Tracked Ads'].astype(str).str.replace(',',''), errors='coerce').fillna(0)
            
            # Create a unique key for easier lookup
            df['key'] = df['日期'] + '_' + df['小時'] + '_' + df['版位編號']
            
            # Keep only key and metric
            dfs[name] = df[['key', 'Total Tracked Ads']].set_index('key')
            print(f"   ✅ {name}: {len(df)} 筆資料")
            
        except Exception as e:
            print(f"   ❌ 讀取失敗 {name}: {e}")
            return

    # Base DF (Viewability usually covers most)
    print("\n🔍 開始比對 'Total Tracked Ads'...")
    
    # Concatenate all keys to find intersection
    all_keys = set()
    for df in dfs.values():
        all_keys.update(df.index.tolist())
        
    print(f"   總共發現 {len(all_keys)} 個唯一 Key (日期+小時+版位)")
    
    # Create a master comparison DF
    comp_df = pd.DataFrame(index=list(all_keys))
    
    for name, df in dfs.items():
        comp_df[name] = df['Total Tracked Ads']
        
    # Check consistency
    # Filter rows where at least 2 columns are not NaN (to compare)
    comp_df['not_na_count'] = comp_df.notna().sum(axis=1)
    valid_rows = comp_df[comp_df['not_na_count'] >= 2].copy()
    
    print(f"   共有 {len(valid_rows)} 筆資料在至少兩份報表中同時存在")
    
    # Check if max == min for each row (ignoring NaNs)
    # This checks if all available values are identical
    valid_rows['min'] = valid_rows[list(files.keys())].min(axis=1)
    valid_rows['max'] = valid_rows[list(files.keys())].max(axis=1)
    valid_rows['diff'] = valid_rows['max'] - valid_rows['min']
    
    inconsistent = valid_rows[valid_rows['diff'] > 0]
    
    if len(inconsistent) == 0:
        print("\n✅ 指標一致性驗證通過！")
        print("所有重疊的版位資料，其 'Total Tracked Ads' 數值完全相同。")
    else:
        print(f"\n⚠️ 發現 {len(inconsistent)} 筆資料數值不一致！")
        print("   範例差異 (前 5 筆):")
        print(inconsistent[list(files.keys())].head(5))
        
        print("\n   最大差異值:", inconsistent['diff'].max())
        
    # Show a sample successful match
    print("\n✅ 成功匹配範例 (前 1 筆):")
    print(valid_rows[list(files.keys())].head(1))

if __name__ == "__main__":
    verify_consistency()
