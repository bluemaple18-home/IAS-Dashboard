import pandas as pd
import numpy as np

def analyze_logic(file_path):
    print(f"🧐 深度分析數值因果關係: {file_path}")
    try:
        # 讀取樣本，這次讀取多一點確保有非零數據
        df = pd.read_excel(file_path, skiprows=1, nrows=1000)
        
        # 真正資料的欄位名稱在 df 的第一列 (index 0)
        real_headers = df.iloc[0].values
        data = df.iloc[1:].copy()
        data.columns = real_headers
        
        # 數值轉換
        for col in data.columns:
            if col != 'Placement Id':
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        
        # 過濾出有數據的列進行分析
        active_data = data[data['Total Tracked Ads'] > 0].copy()
        print(f"\n--- 樣本分析 (有效數據共 {len(active_data)} 筆) ---")
        
        if len(active_data) == 0:
            print("⚠️ 警告：樣本中皆為零，無法推導邏輯。")
            return

        results = []

        # 1. 加總關係: Measured Ads = Viewable Impressions + Non-Viewable Ads ?
        if 'Measured Ads' in active_data.columns and 'Viewable Impressions' in active_data.columns and 'Non-Viewable Ads' in active_data.columns:
            sum_val = active_data['Viewable Impressions'] + active_data['Non-Viewable Ads']
            diff = (active_data['Measured Ads'] - sum_val).abs().sum()
            status = "✅ 吻合" if diff < 1 else "❌ 不吻合"
            results.append(f"【加總關係】Measured Ads = Viewable Impressions + Non-Viewable Ads ({status})")
            
        # 2. 比例關係: % Measured Ads = Measured Ads / Total Tracked Ads ?
        if '% Measured Ads' in active_data.columns and 'Total Tracked Ads' in active_data.columns:
            calc = (active_data['Measured Ads'] / active_data['Total Tracked Ads']).fillna(0) * 100
            diff = (active_data['% Measured Ads'] - calc).abs().mean()
            print(f">>> [% Measured = Measured / Total]: 平均誤差 {diff:.4f}%")

        # 2b. 比例關係: % Measured Ads = Measured Ads / Eligible Ads for Viewability ?
        if '% Measured Ads' in active_data.columns and 'Eligible Ads for Viewability' in active_data.columns:
            e_data = active_data[active_data['Eligible Ads for Viewability'] > 0]
            if len(e_data) > 0:
                calc = (e_data['Measured Ads'] / e_data['Eligible Ads for Viewability']).fillna(0) * 100
                diff = (e_data['% Measured Ads'] - calc).abs().mean()
                status = "✅ 吻合" if diff < 0.1 else "❌ 不吻合"
                print(f">>> [% Measured = Measured / Eligible]: 平均誤差 {diff:.4f}% -> {status}")

        # 3. 比例關係: % Viewable Impressions = Viewable Impressions / Measured Ads ?
        if '% Viewable Impressions' in active_data.columns and 'Measured Ads' in active_data.columns:
            m_data = active_data[active_data['Measured Ads'] > 0]
            if len(m_data) > 0:
                calc = (m_data['Viewable Impressions'] / m_data['Measured Ads']).fillna(0) * 100
                diff = (m_data['% Viewable Impressions'] - calc).abs().mean()
                status = "✅ 吻合" if diff < 0.1 else "❌ 不吻合"
                results.append(f"【比例關係】% Viewable Impressions = (Viewable Impressions / Measured Ads) * 100 ({status}, 平均誤差 {diff:.4f}%)")

        # 4. 比例關係: % Non-Viewable Ads = Non-Viewable Ads / Measured Ads ?
        if '% Non-Viewable Ads' in active_data.columns and 'Measured Ads' in active_data.columns:
            m_data = active_data[active_data['Measured Ads'] > 0]
            if len(m_data) > 0:
                calc = (m_data['Non-Viewable Ads'] / m_data['Measured Ads']).fillna(0) * 100
                diff = (m_data['% Non-Viewable Ads'] - calc).abs().mean()
                status = "✅ 吻合" if diff < 0.1 else "❌ 不吻合"
                results.append(f"【比例關係】% Non-Viewable Ads = (Non-Viewable Ads / Measured Ads) * 100 ({status}, 平均誤差 {diff:.4f}%)")

        print("\n" + "\n".join(results))

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    path = "/Users/mattkuo/Downloads/sample-Viewability_20260125-20260126.xlsx"
    analyze_logic(path)
