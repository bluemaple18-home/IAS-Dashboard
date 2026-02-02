import pandas as pd
import numpy as np

def analyze_ivt_logic(file_path):
    print(f"🧐 正在分析 Invalid Traffic 邏輯: {file_path}")
    
    try:
        # 讀取資料
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

        # 1. 加總關係: IVT = GIVT + SIVT ?
        if all(c in active_data.columns for c in ['Invalid Traffic Ads', 'General Invalid Traffic (GIVT) Ads', 'Sophisticated Invalid Traffic (SIVT) Ads']):
            diff = (active_data['Invalid Traffic Ads'] - (active_data['General Invalid Traffic (GIVT) Ads'] + active_data['Sophisticated Invalid Traffic (SIVT) Ads'])).abs().sum()
            status = "✅ 吻合" if diff < 1 else "❌ 不吻合"
            results.append(f"【加總】Invalid Traffic Ads = GIVT + SIVT ({status})")

        # 2. 加總關係: SIVT = Bots + Domain Spoofing + Hidden ?
        sivt_sub = ['Bots (SIVT) Ads', 'Domain Spoofing (SIVT) Ads', 'Hidden Ads (SIVT) Ads']
        if 'Sophisticated Invalid Traffic (SIVT) Ads' in active_data.columns and all(c in active_data.columns for c in sivt_sub):
            calc_sivt = active_data[sivt_sub].sum(axis=1)
            diff = (active_data['Sophisticated Invalid Traffic (SIVT) Ads'] - calc_sivt).abs().sum()
            status = "✅ 吻合" if diff < 1 else f"❌ 不吻合 (差異 {diff})"
            results.append(f"【加總】SIVT = Bots + Domain Spoofing + Hidden ({status})")

        # 3. 比例關係分母探查
        # % Invalid Traffic Ads 的分母是誰?
        if '% Invalid Traffic Ads' in active_data.columns:
            # 候選分母: Eligible Ads, Total Tracked Ads
            for den_name in ['Eligible Ads for Invalid Traffic', 'Total Tracked Ads']:
                if den_name in active_data.columns:
                    temp_df = active_data[active_data[den_name] > 0]
                    if len(temp_df) > 0:
                        calc = (temp_df['Invalid Traffic Ads'] / temp_df[den_name]) * 100
                        diff = (temp_df['% Invalid Traffic Ads'] - calc).abs().mean()
                        if diff < 0.1:
                            results.append(f"【比例】% Invalid Traffic Ads = (Invalid Traffic Ads / {den_name}) * 100 (✅ 吻合)")
                            break
                        else:
                            print(f"DEBUG: % IVT vs {den_name} 誤差: {diff:.4f}%")

        # 4. % General Invalid Traffic (GIVT) Ads
        if '% General Invalid Traffic (GIVT) Ads' in active_data.columns:
            # 候選分母: Eligible Ads, Total Tracked Ads
            for den_name in ['Eligible Ads for Invalid Traffic', 'Total Tracked Ads']:
                 if den_name in active_data.columns:
                     temp_df = active_data[active_data[den_name] > 0]
                     if len(temp_df) > 0:
                         calc = (temp_df['General Invalid Traffic (GIVT) Ads'] / temp_df[den_name]) * 100
                         diff = (temp_df['% General Invalid Traffic (GIVT) Ads'] - calc).abs().mean()
                         if diff < 0.1:
                             results.append(f"【比例】% GIVT = (GIVT / {den_name}) * 100 (✅ 吻合)")
                             break

        print("\n--- 邏輯分析結果 ---")
        for r in results:
            print(r)
            
    except Exception as e:
        print(f"❌ 分析失敗: {e}")

if __name__ == "__main__":
    analyze_ivt_logic('/Users/matt/Downloads/sample--Invalid-Traffic_20260125-20260126.xlsx')
