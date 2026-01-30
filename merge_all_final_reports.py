import pandas as pd
import numpy as np
import os
import functools
import glob

def merge_all_reports():
    source_dir = "/Users/mattkuo/Downloads"
    # Find raw files (disguised as .csv or .xlsx)
    # We will look for sample*_final_integrated.* and prefer the latest ones
    
    file_map = {
        'Viewability': 'Viewability', 
        'IVT': 'Invalid-Traffic',
        'SiteQuality': 'Site-Quality',
        'BrandSuitability': 'Brand-Suitability',
        'QualImpressions': 'Quality-Impressions'
    }
    
    dfs = []
    
    print("🚀 開始合併並重新計算 5 份報表...")
    
    # 1. Load Raw Data
    for key, pattern_keyword in file_map.items():
        # Find file
        pattern = f"sample-*{pattern_keyword}*_final_integrated.*"
        files = glob.glob(os.path.join(source_dir, pattern))
        
        # Filter temp files
        files = [f for f in files if not os.path.basename(f).startswith('~$')]
        
        if not files:
            print(f"⚠️ 找不到 {key} 的對應 raw 檔案")
            continue
            
        # Sort by modification time to get latest
        files.sort(key=os.path.getmtime, reverse=True)
        file_path = files[0]
        
        print(f"   📖 讀取 ({key}): {os.path.basename(file_path)}")
        try:
            # Force read as excel (even if .csv extension, based on prior investigation)
            # But handle fallback just in case
            try:
                df = pd.read_excel(file_path, dtype={'日期': str, '小時': str, '版位編號': str}, engine='openpyxl')
            except:
                 df = pd.read_csv(file_path, dtype={'日期': str, '小時': str, '版位編號': str})

            # Clean column names
            df.columns = [str(c).strip() for c in df.columns]

            # Identify keys and dims
            keys = ['日期', '小時', '版位編號']
            dims = ['供應商名稱', '網站', '網站名稱', '版位名稱', 'antifroud', '知名媒體', '子聯播網']
            
            # Identify numeric columns (metrics)
            metrics = [c for c in df.columns if c not in keys + dims]
            
            # Convert metrics to numeric (force clean)
            for m in metrics:
                # Remove % and , if present (just in case)
                df[m] = pd.to_numeric(df[m].astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)
            
            # Rename metrics with prefix
            rename_map = {m: f"{m} ({key})" for m in metrics}
            # Rename dims with suffix
            rename_map.update({d: f"{d}_{key}" for d in dims})
            
            df_renamed = df.rename(columns=rename_map)
            dfs.append(df_renamed)
            
        except Exception as e:
            print(f"❌ 讀取失敗 {file_path}: {e}")
            return

    if not dfs:
        print("❌ 沒有可合併的資料")
        return

    # 2. Merge (Full Outer Join)
    print("🤝 正在執行 Full Outer Join...")
    
    df_final = functools.reduce(
        lambda left, right: pd.merge(left, right, on=['日期', '小時', '版位編號'], how='outer'),
        dfs
    )
    
    print(f"   合併完成！總資料筆數: {len(df_final)}")
    
    # 3. Coalesce Dimensions
    print("🧹 正在整理維度欄位 (Coalesce)...")
    common_dims = ['供應商名稱', '網站', '網站名稱', '版位名稱', 'antifroud', '知名媒體', '子聯播網']
    
    # Order of priority for dimensional data: Viewability > IVT > SQ > BS > QI
    priority_order = ['Viewability', 'IVT', 'SiteQuality', 'BrandSuitability', 'QualImpressions']
    
    for dim in common_dims:
        # Create final column
        df_final[dim] = None
        
        # Sequentially coalesce
        for key in priority_order:
            col_name = f"{dim}_{key}"
            if col_name in df_final.columns:
                df_final[dim] = df_final[dim].combine_first(df_final[col_name])
        
        # Drop temp columns
        cols_to_drop = [c for c in df_final.columns if c.startswith(f"{dim}_")]
        df_final.drop(columns=cols_to_drop, inplace=True)

    # 4. RECALCULATE Percentages (Using verified formulas)
    print("🧮 正在重新計算所有百分比指標...")
    
    def safe_div(num, den):
        return (num / den).replace([np.inf, -np.inf], 0).fillna(0) * 100

    # (A) Viewability
    # Denom: Eligible Ads for Viewability (Viewability)
    # Measured: Measured Ads (Viewability)
    den_view = df_final.get('Eligible Ads for Viewability (Viewability)', 0)
    measured_view = df_final.get('Measured Ads (Viewability)', 0)
    
    if isinstance(den_view, pd.Series):
        if 'Measured Ads (Viewability)' in df_final.columns:
             df_final['% Measured Ads (Viewability)'] = safe_div(measured_view, den_view)
             
        if 'Viewable Impressions (Viewability)' in df_final.columns:
             df_final['% Viewable Impressions (Viewability)'] = safe_div(df_final['Viewable Impressions (Viewability)'], measured_view)
             
        if 'Non-Viewable Ads (Viewability)' in df_final.columns:
             df_final['% Non-Viewable Ads (Viewability)'] = safe_div(df_final['Non-Viewable Ads (Viewability)'], measured_view)

    # (B) IVT
    # Denom: Eligible Ads for Invalid Traffic (IVT)
    den_ivt = df_final.get('Eligible Ads for Invalid Traffic (IVT)', 0)
    if isinstance(den_ivt, pd.Series):
        ivt_metrics = [
            'Invalid Traffic Ads', 'General Invalid Traffic (GIVT) Ads', 
            'Sophisticated Invalid Traffic (SIVT) Ads', 'Bots (SIVT) Ads', 
            'Domain Spoofing (SIVT) Ads', 'Hidden Ads (SIVT) Ads'
        ]
        if 'Total Tracked Ads (IVT)' in df_final.columns:
             df_final['% Eligible for Invalid Traffic (IVT)'] = safe_div(den_ivt, df_final['Total Tracked Ads (IVT)'])
             
        for m in ivt_metrics:
            col = f"{m} (IVT)"
            if col in df_final.columns:
                df_final[f"% {m} (IVT)"] = safe_div(df_final[col], den_ivt)

    # (C) Site Quality
    # Denom: Total Eligible Ads for Site Quality (SiteQuality)
    den_sq = df_final.get('Total Eligible Ads for Site Quality (SiteQuality)', 0)
    if isinstance(den_sq, pd.Series):
        sq_metrics = [
            ('Reduced Value Inventory (RVI) Ads', '% Reduced Value Inventory (RVI) Ads'),
            ('seeThrough Ads', '% seeThrough Ads'),
            ('Invisible URL Ads', 'Invisible URL rate'),
            ('Incentivized Browsing (RVI) Ads', '% Incentivized Browsing (RVI) Ads'),
            ('Proxy Server (RVI) Ads', '% Proxy Server (RVI) Ads')
        ]
        for m, name in sq_metrics:
            col = f"{m} (SiteQuality)"
            if col in df_final.columns:
                df_final[f"{name} (SiteQuality)"] = safe_div(df_final[col], den_sq)

    # (D) Brand Suitability
    # Denom: Total Eligible Ads for Brand Suitability (BrandSuitability)
    den_bs = df_final.get('Total Eligible Ads for Brand Suitability (BrandSuitability)', 0)
    if isinstance(den_bs, pd.Series):
        bs_metrics = [
            ('Brand Suitability Passed Ads', '% Brand Suitability Passed Ads'),
            ('Brand Suitability Failed Ads', '% Brand Suitability Failed Ads'),
            ('MFA Ads', 'MFA rate'),
            ('AD Clutter Ads', 'AD Clutter rate')
        ]
        for m, name in bs_metrics:
            col = f"{m} (BrandSuitability)"
            if col in df_final.columns:
                df_final[f"{name} (BrandSuitability)"] = safe_div(df_final[col], den_bs)

    # (E) Quality Impressions
    # Denom: Eligible ads for quality Impressions (QualImpressions)
    den_qi = df_final.get('Eligible ads for quality Impressions (QualImpressions)', 0)
    if isinstance(den_qi, pd.Series):
        qi_metrics = [
            ('Quality Ads', 'Quality Ads rate'), 
            ('Non-quality Ads', 'Non-quality Ads rate')
        ]
        for m, name in qi_metrics:
            col = f"{m} (QualImpressions)"
            if col in df_final.columns:
                df_final[f"{name} (QualImpressions)"] = safe_div(df_final[col], den_qi)

    # 5. Format Output
    print("🎨 正在套用格式 (百分比/千分位)...")
    for col in df_final.columns:
        col_str = str(col)
        # Skip Keys and Dims
        if col in keys + common_dims:
            continue
            
        # Detect type
        is_percent = '%' in col_str or 'rate' in col_str.lower()
        is_average = 'Average' in col_str or 'Avg' in col_str or '(Sec)' in col_str
        
        if is_percent:
            df_final[col] = df_final[col].apply(lambda x: f"{float(x):.2f}%" if pd.notnull(x) else "")
        elif is_average:
            df_final[col] = df_final[col].apply(lambda x: f"{float(x):,.2f}" if pd.notnull(x) else "")
        else:
            # Integer with commas
            df_final[col] = df_final[col].apply(lambda x: f"{float(x):,.0f}" if pd.notnull(x) else "")

    # 6. Reorder and Save
    print("✨ 正在重新排列欄位並存檔...")
    # Keys + Dims + Metrics
    final_cols = keys + common_dims + [c for c in df_final.columns if c not in keys + common_dims]
    df_final = df_final[final_cols]
    
    output_filename = "00_全媒體整合報表_版位級別.csv"
    output_path = os.path.join(source_dir, output_filename)
    
    # Save with UTF-8 BOM
    df_final.to_csv(output_path, index=False, encoding='utf-8-sig')
    print("✅ 全流程完成！百分比已修正。")

if __name__ == "__main__":
    merge_all_reports()
