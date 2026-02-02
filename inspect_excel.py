import pandas as pd
import sys

def inspect_excel(file_path):
    print(f"正在檢查檔案: {file_path}")
    try:
        # 根據初步分析，實際資料表頭似乎在第 2 行 (索引 1)
        # 我們嘗試從第 2 行開始讀取
        df = pd.read_excel(file_path, skiprows=1, nrows=5)
        print("\n--- 修正後的欄位清單 ---")
        print(df.columns.tolist())
        print("\n--- 資料預覽 (前 5 行) ---")
        print(df.head())
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    path = "/Users/matt/Downloads/sample-Viewability_20260125-20260126.xlsx"
    inspect_excel(path)
