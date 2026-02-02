import pandas as pd

def inspect_ssp(file_path):
    print(f"🧐 檢查 SSP 檔案: {file_path}")
    try:
        # 先檢查是否有表頭偏移
        df = pd.read_excel(file_path, nrows=5)
        print("\n--- 預設讀取欄位 ---")
        print(df.columns.tolist())
        print("\n--- 資料預覽 ---")
        print(df.head())
    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    path = "/Users/matt/Downloads/SSP_2026-01-26_2026-01-27_(一般媒體).xlsx"
    inspect_ssp(path)
