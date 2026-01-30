import pandas as pd
import numpy as np

def analyze_qi_logic(file_path):
    print(f"🧐 正在分析 Quality Impressions 邏輯: {file_path}")
    
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

        # 1. 加總關係: Total Tracked = Quality + Non-quality ? (或者 Eligible)
        # 通常是 Quality + Non-quality = Eligible
        if all(c in active_data.columns for c in ['Eligible ads for quality Impressions', 'Quality Ads', 'Non-quality Ads']):
            diff = (active_data['Eligible ads for quality Impressions'] - (active_data['Quality Ads'] + active_data['Non-quality Ads'])).abs().sum()
            status = "✅ 吻合" if diff < 1 else f"❌ 不吻合 (差異 {diff})"
            results.append(f"【加總】Eligible = Quality + Non-quality ({status})")

        # 2. 比例分母探查
        den_candidates = ['Eligible ads for quality Impressions', 'Total Tracked Ads']
        
        # Quality Ads rate
        if 'Quality Ads rate' in active_data.columns:
            for den_name in den_candidates:
                if den_name in active_data.columns:
                    temp_df = active_data[active_data[den_name] > 0]
                    if len(temp_df) > 0:
                        calc = (temp_df['Quality Ads'] / temp_df[den_name]) * 100
                        diff = (temp_df['Quality Ads rate'] - calc).abs().mean()
                        if diff < 0.1:
                            results.append(f"【比例】Quality Ads rate = (Quality Ads / {den_name}) * 100 (✅ 吻合)")
                            break

        print("\n--- 邏輯分析結果 ---")
        for r in results:
            print(r)
            
    except Exception as e:
        print(f"❌ 分析失敗: {e}")

if __name__ == "__main__":
    analyze_qi_logic('/Users/mattkuo/Downloads/sample--Quality-Impressions_20260125-20260126.xlsx')
