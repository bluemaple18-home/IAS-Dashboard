import pandas as pd
import numpy as np

def analyze_bs_logic(file_path):
    print(f"🧐 正在分析 Brand Suitability 邏輯: {file_path}")
    
    try:
        df_raw = pd.read_excel(file_path, skiprows=1)
        headers = df_raw.iloc[0].values
        df = df_raw.iloc[1:].copy()
        df.columns = headers
        
        # 數值化
        for col in df.columns:
            if col != 'Placement Id':
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        active_data = df[df['Total Tracked Ads'] > 0].copy()
        print(f"分析樣本數: {len(active_data)}")

        results = []

        # 1. 加總關係: Total Eligible = Passed + Failed ?
        if all(c in active_data.columns for c in ['Total Eligible Ads for Brand Suitability', 'Brand Suitability Passed Ads', 'Brand Suitability Failed Ads']):
            diff = (active_data['Total Eligible Ads for Brand Suitability'] - (active_data['Brand Suitability Passed Ads'] + active_data['Brand Suitability Failed Ads'])).abs().sum()
            status = "✅ 吻合" if diff < 1 else f"❌ 不吻合 (差異 {diff})"
            results.append(f"【加總】Total Eligible = Passed + Failed ({status})")

        # 2. 比例分母探查
        den_candidates = ['Total Eligible Ads for Brand Suitability', 'Total Tracked Ads']
        
        # % Brand Suitability Passed Ads
        if '% Brand Suitability Passed Ads' in active_data.columns:
            for den_name in den_candidates:
                if den_name in active_data.columns:
                    temp_df = active_data[active_data[den_name] > 0]
                    if len(temp_df) > 0:
                        calc = (temp_df['Brand Suitability Passed Ads'] / temp_df[den_name]) * 100
                        diff = (temp_df['% Brand Suitability Passed Ads'] - calc).abs().mean()
                        if diff < 0.1:
                            results.append(f"【比例】% Passed Ads = (Passed / {den_name}) * 100 (✅ 吻合)")
                            break

        # MFA rate
        if 'MFA rate' in active_data.columns:
             for den_name in den_candidates:
                 if den_name in active_data.columns:
                     temp_df = active_data[active_data[den_name] > 0]
                     if len(temp_df) > 0:
                         calc = (temp_df['MFA Ads'] / temp_df[den_name]) * 100
                         diff = (temp_df['MFA rate'] - calc).abs().mean()
                         if diff < 0.1:
                             results.append(f"【比例】MFA rate = (MFA Ads / {den_name}) * 100 (✅ 吻合)")
                             break

        # AD Clutter rate
        if 'AD Clutter rate' in active_data.columns:
             for den_name in den_candidates:
                 if den_name in active_data.columns:
                     temp_df = active_data[active_data[den_name] > 0]
                     if len(temp_df) > 0:
                         calc = (temp_df['AD Clutter Ads'] / temp_df[den_name]) * 100
                         diff = (temp_df['AD Clutter rate'] - calc).abs().mean()
                         if diff < 0.1:
                             results.append(f"【比例】AD Clutter rate = (AD Clutter Ads / {den_name}) * 100 (✅ 吻合)")
                             break

        print("\n--- 邏輯分析結果 ---")
        for r in results:
            print(r)
            
    except Exception as e:
        print(f"❌ 分析失敗: {e}")

if __name__ == "__main__":
    analyze_bs_logic('/Users/matt/Downloads/sample-Brand-Suitability_20260125-20260126.xlsx')
