import pandas as pd
import numpy as np
import os

def aggregate_to_website(input_path):
    print(f"🚀 開始聚合至網站層級: {input_path}")
    output_csv = input_path.replace("_final_integrated.xlsx", "_website_level.csv")
    
    try:
        # Read Excel
        df = pd.read_excel(input_path, dtype=str)
        
        # Define Group Columns
        group_cols = ['日期', '小時', '供應商名稱', '網站', '網站名稱', '知名媒體']
        
        # 1. Identify Report Type based on columns
        report_type = "UNKNOWN"
        if 'Viewable Impressions' in df.columns:
            report_type = "VIEWABILITY"
        elif 'Brand Suitability Passed Ads' in df.columns:
            report_type = "BS"
        elif 'Invalid Traffic Ads' in df.columns:
            report_type = "IVT"
        elif 'Reduced Value Inventory (RVI) Ads' in df.columns:
            report_type = "SQ"
        elif 'Quality Ads' in df.columns:
            report_type = "QI"
            
        print(f"📋 偵測到報表類型: {report_type}")

        # 2. Prepare Numeric Columns for Summation
        # Exclude known non-numeric dimensions
        exclude_cols = group_cols + ['版位編號', '版位名稱', 'antifroud', 'Placement Id']
        # Also exclude calculated rate columns (contains % or rate)
        numeric_cols = []
        for c in df.columns:
            c_str = str(c)
            if c_str in exclude_cols: continue
            if '%' in c_str: continue
            if 'rate' in c_str.lower(): continue
            if 'Average' in c_str: continue # Handled separately
            numeric_cols.append(c_str)
            
        # Special handling for Viewability Average Time Weighting
        if report_type == "VIEWABILITY" and 'Average Time In View (Sec)' in df.columns:
            # We need to recreate 'Total Time' = Average * Measured
            df['Metric_Total_Time'] = pd.to_numeric(df['Average Time In View (Sec)'], errors='coerce').fillna(0) * \
                                      pd.to_numeric(df['Measured Ads'], errors='coerce').fillna(0)
            numeric_cols.append('Metric_Total_Time')

        # Convert numeric cols to float
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3. Aggregation Logic
        print("📊 執行聚合 (Group By Site)...")
        
        def antifraud_agg(x):
            if x.astype(str).str.contains('antifroud', case=False, na=False).any():
                return 'antifroud'
            return None

        agg_dict = {c: 'sum' for c in numeric_cols}
        if 'antifroud' in df.columns:
            agg_dict['antifroud'] = antifraud_agg
            
        # Fill None in grouping columns
        for g in group_cols:
            if g in df.columns:
                df[g] = df[g].fillna('')
            else:
                df[g] = ''

        df_agg = df.groupby(group_cols, as_index=False).agg(agg_dict)
        
        # 4. Recalculate Logic
        print("🧮 重新計算百分比/平均值公式...")
        
        # Helper
        def calc_rate(num, den, target):
            if num in df_agg.columns and den in df_agg.columns:
                df_agg[target] = (df_agg[num] / df_agg[den]).replace([np.inf, -np.inf], 0).fillna(0)

        if report_type == "VIEWABILITY":
            # % Measured = Measured / Eligible
            calc_rate('Measured Ads', 'Eligible Ads for Viewability', '% Measured Ads')
            # % Viewable = Viewable / Measured
            calc_rate('Viewable Impressions', 'Measured Ads', '% Viewable Impressions')
            # % Non-Viewable = Non-Viewable / Measured
            calc_rate('Non-Viewable Ads', 'Measured Ads', '% Non-Viewable Ads')
            # Average Time = Total Time / Measured
            if 'Metric_Total_Time' in df_agg.columns:
                df_agg['Average Time In View (Sec)'] = (df_agg['Metric_Total_Time'] / df_agg['Measured Ads']).replace([np.inf, -np.inf], 0).fillna(0)
                df_agg = df_agg.drop(columns=['Metric_Total_Time'])

        elif report_type == "BS":
            den = 'Total Eligible Ads for Brand Suitability'
            # % Passed, % Failed, MFA rate, Clutter rate
            calc_rate('Brand Suitability Passed Ads', den, '% Brand Suitability Passed Ads')
            calc_rate('Brand Suitability Failed Ads', den, '% Brand Suitability Failed Ads')
            calc_rate('MFA Ads', den, 'MFA rate')
            calc_rate('AD Clutter Ads', den, 'AD Clutter rate')

        elif report_type == "IVT":
             den = 'Eligible Ads for Invalid Traffic'
             calc_rate(den, 'Total Tracked Ads', '% Eligible for Invalid Traffic')
             calc_rate('Invalid Traffic Ads', den, '% Invalid Traffic Ads')
             calc_rate('General Invalid Traffic (GIVT) Ads', den, '% General Invalid Traffic (GIVT) Ads')
             calc_rate('Sophisticated Invalid Traffic (SIVT) Ads', den, '% Sophisticated Invalid Traffic (SIVT) Ads')
             # Subs usually calc against Den as well
             calc_rate('Bots (SIVT) Ads', den, '% Bots (SIVT) Ads')
             calc_rate('Domain Spoofing (SIVT) Ads', den, '% Domain Spoofing (SIVT) Ads')
             calc_rate('Hidden Ads (SIVT) Ads', den, '% Hidden Ads (SIVT) Ads')

        elif report_type == "SQ":
            den = 'Total Eligible Ads for Site Quality'
            calc_rate('Reduced Value Inventory (RVI) Ads', den, '% Reduced Value Inventory (RVI) Ads')
            calc_rate('seeThrough Ads', den, '% seeThrough Ads')
            calc_rate('Invisible URL Ads', den, 'Invisible URL rate')
            # Subs
            calc_rate('Incentivized Browsing (RVI) Ads', den, '% Incentivized Browsing (RVI) Ads')
            calc_rate('Proxy Server (RVI) Ads', den, '% Proxy Server (RVI) Ads')

        elif report_type == "QI":
             den = 'Eligible ads for quality Impressions'
             calc_rate('Quality Ads', den, 'Quality Ads rate')
             calc_rate('Non-quality Ads', den, 'Non-quality Ads rate')

        # 5. Formatting
        print("🎨 套用格式 (百分比 & 千分位)...")
        for col in df_agg.columns:
            if col in group_cols or col == 'antifroud':
                continue
                
            is_percent = '%' in col or 'rate' in col.lower()
            is_average = 'Average' in col or '(Sec)' in col
            
            if is_percent:
                df_agg[col] = df_agg[col].apply(lambda x: f"{float(x)*100:.2f}%" if pd.notnull(pd.to_numeric(x, errors='coerce')) else x)
            elif is_average:
                # 2 decimals
                df_agg[col] = df_agg[col].apply(lambda x: f"{float(x):,.2f}" if pd.notnull(pd.to_numeric(x, errors='coerce')) else x)
            else:
                # Integer format for counts
                df_agg[col] = df_agg[col].apply(lambda x: f"{float(x):,.0f}" if pd.notnull(pd.to_numeric(x, errors='coerce')) else x)

        print(f"📤 儲存網站級別報表至: {output_csv}")
        df_agg.to_csv(output_csv, index=False, encoding='utf-8-sig')
        print("✅ 完成！")
        return output_csv
        
    except Exception as e:
        print(f"❌ 聚合失敗: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test
    pass
