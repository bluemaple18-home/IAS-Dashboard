import pandas as pd

def verify_results(file_path):
    print(f"🧐 正在驗證產出檔案: {file_path}")
    try:
        # 讀取前 10 行進行驗證，特別檢查文字格式
        df = pd.read_excel(file_path, nrows=10, dtype=str)
        print("\n--- 抽樣驗證結果 (前 10 筆) ---")
        cols_to_show = ['日期', '小時', '分秒', '版位編號']
        print(df[cols_to_show])
        
        # 檢查是否有欄位長度異常（例如分秒是否維持 4 位）
        print("\n--- 格式檢查 ---")
        print(f"分秒欄位示例: {df['分秒'].iloc[0]} (長度: {len(df['分秒'].iloc[0])})")
        if len(df['分秒'].iloc[0]) == 4:
            print("✅ 格式驗證成功：分秒保留了 4 位（包含前導零）。")
        else:
            print("⚠️ 警告：分秒欄位長度異常。")
            
    except Exception as e:
        print(f"❌ 驗證時發生錯誤: {e}")

if __name__ == "__main__":
    path = "/Users/mattkuo/Downloads/sample-Viewability_20260125-20260126_processed.xlsx"
    verify_results(path)
