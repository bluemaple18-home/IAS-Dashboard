import pandas as pd
import os

def merge_reports(hourly_path, ssp_path, antifraud_path=None, famous_path=None, subnetwork_path=None):
    print(f"🔗 正在開始整合報表...")
    print(f"📂 時報檔案: {hourly_path}")
    print(f"📂 媒體清單: {ssp_path}")
    if antifraud_path: print(f"📂 違規名單: {antifraud_path}")
    if famous_path: print(f"📂 知名媒體: {famous_path}")
    if subnetwork_path: print(f"📂 子聯播網: {subnetwork_path}")
    
    output_path = hourly_path.replace("_hourly_report.xlsx", "_final_integrated.xlsx")
    
    try:
        # 1. 讀取時報 (主表)
        df_hourly = pd.read_excel(hourly_path, dtype=str)
        
        # 自動偵測 SSP 檔案類型 (Raw vs Processed)
        # 先讀取前幾行來判斷
        df_temp = pd.read_excel(ssp_path, header=0, nrows=5)
        
        is_processed = '日期' in df_temp.columns and '小時' in df_temp.columns
        
        if is_processed:
            print("ℹ️ 偵測到已處理過的 SSP 檔案 (Header at row 0)")
            df_ssp_raw = pd.read_excel(ssp_path, header=0, dtype=str)
        else:
            print("ℹ️ 偵測到原始 SSP 檔案 (Header at row 1)")
            df_ssp_raw = pd.read_excel(ssp_path, header=1, dtype=str)
        
        # 清理欄位名稱中的空格或換行
        df_ssp_raw.columns = [str(c).strip() for c in df_ssp_raw.columns]
        print(f"SSP 檢測到的欄位: {df_ssp_raw.columns.tolist()}")
        
        # 尋找關鍵欄位 (模糊匹配或精確匹配)
        ssp_id_col = '版位'
        if ssp_id_col not in df_ssp_raw.columns:
            matches = [c for c in df_ssp_raw.columns if '版位' in c]
            if matches: ssp_id_col = matches[0]

        # 整理 SSP 資訊以供比對
        print(f"🛠️ 正在使用 '{ssp_id_col}' 作為關聯鍵進行預處理...")
        
        # 如果是原始檔案，需要拆解時間
        if '日期' not in df_ssp_raw.columns:
            time_split = df_ssp_raw['時間'].str.split(' ', expand=True)
            df_ssp_raw['日期'] = time_split[0].str.replace('-', '', regex=False)
            df_ssp_raw['小時'] = time_split[1].str.split(':', expand=True)[0]
        
        # 重新命名關聯欄位以匹配時報
        df_ssp_raw = df_ssp_raw.rename(columns={ssp_id_col: '版位編號'})
        
        # 僅保留比對需要的欄位 (動態偵測存在的欄位)
        available_cols = df_ssp_raw.columns.tolist()
        keep_cols = ['日期', '小時', '版位編號']
        for c in ['供應商名稱', '網站', '網站名稱', '版位名稱']:
            if c in available_cols: keep_cols.append(c)
            
        df_ssp_clean = df_ssp_raw[keep_cols].drop_duplicates(['日期', '小時', '版位編號'])
        
        # 3. 執行 Left Join (以時報為主)
        print("🤝 正在執行數據比對 (三維度: 日期+小時+版位)...")
        final_df = pd.merge(
            df_hourly, 
            df_ssp_clean, 
            on=['日期', '小時', '版位編號'], 
            how='left'
        )
        
        
        # --- 新增維度邏輯 ---
        
        # 建立版位編號與網站的對應表 (用於 antifraud 擴散邏輯)
        # 確保 '網站' 欄位存在
        site_col = '網站'
        if site_col not in final_df.columns:
             # Try finding site column
             site_matches = [c for c in final_df.columns if '網站' in c and '名稱' not in c]
             if site_matches: 
                 site_col = site_matches[0]
                 print(f"ℹ️ 使用 '{site_col}' 作為網站ID欄位")
             else:
                 print("⚠️ 警告: 找不到網站ID欄位，antifraud 擴散邏輯可能無法正常運作")

        # A. Antifraud (違規名單) - 單純比對版位 (暫不連坐)
        if antifraud_path:
            print("🕵️ 正在處理 antifroud 邏輯 (單純比對版位)...")
            try:
                # 讀取違規名單
                df_af = pd.read_excel(antifraud_path, sheet_name='違規名單', dtype=str)
                # 清洗 zone_id
                if 'zone_id' in df_af.columns:
                     bad_zones = set(df_af['zone_id'].astype(str).str.strip())
                     print(f"   違規名單中有 {len(bad_zones)} 個違規版位 ID")
                     
                     # 直接比對版位
                     final_df['antifroud'] = final_df['版位編號'].apply(lambda x: 'antifroud' if str(x).strip() in bad_zones else None)
                     
                     hit_count = final_df['antifroud'].notna().sum()
                     print(f"   比對結果: 共 {hit_count} 筆資料被標記為 antifroud")
                     
                else:
                    print("⚠️ 警告: 違規名單沒有 'zone_id' 欄位")
            except Exception as e:
                print(f"⚠️ Antifraud 處理失敗: {e}")

        # B. 知名媒體
        if famous_path and site_col in final_df.columns:
            print("🌟 正在處理 知名媒體 邏輯...")
            try:
                # 讀取知名媒體清單 (Header at row 1 usually for SSP raw)
                # Check header first roughly (read first few rows)
                df_fam_temp = pd.read_excel(famous_path, header=0, nrows=5)
                
                fam_header = 0
                # Default to 0. If '網站' is found in the first row of data (index 0 of df), it means header is actually at row 1 (Excel row 2)
                if '網站' not in df_fam_temp.columns:
                     # Check first row values
                     first_row_vals = df_fam_temp.iloc[0].astype(str).values
                     if '網站' in first_row_vals:
                         fam_header = 1
                         print("ℹ️ 偵測到知名媒體檔案 Header 在第 2 行 (Row 1)")
                
                df_fam = pd.read_excel(famous_path, header=fam_header, dtype=str)
                df_fam.columns = [str(c).strip() for c in df_fam.columns]
                
                target_fam_col = '網站'
                # Find correct col
                if target_fam_col not in df_fam.columns:
                     matches = [c for c in df_fam.columns if '網站' in c and '名稱' not in c]
                     if matches: target_fam_col = matches[0]
                
                if target_fam_col in df_fam.columns:
                    famous_sites = set(df_fam[target_fam_col].astype(str).str.strip())
                    print(f"   共有 {len(famous_sites)} 個知名媒體網站")
                    
                    final_df['知名媒體'] = final_df[site_col].apply(lambda x: '知名媒體' if str(x).strip() in famous_sites else None)
                else:
                    print("⚠️ 警告: 知名媒體檔案找不到 '網站' 欄位")
                    
            except Exception as e:
                print(f"⚠️ 知名媒體處理失敗: {e}")
                
        # C. 子聯播網 (Sub-network)
        if subnetwork_path:
            print("🕸️ 正在處理 子聯播網 邏輯...")
            try:
                # Header logic (assume same as others, row 1 based on inspection)
                # Step 1167 showed header at row 1 (index 1)
                df_sub_temp = pd.read_excel(subnetwork_path, header=0, nrows=5)
                sub_header = 1 # Force based on observation or detect?
                # Observation: Row 0 is Title, Row 1 is Header.
                # Let's detect to be safe or just use 1 since we saw it. 
                # Using detection similar to Fam (check if '版位' in row 0 val)
                first_row_vals = df_sub_temp.iloc[0].astype(str).values
                if '版位' in first_row_vals:
                    sub_header = 1
                    print("ℹ️ 偵測到子聯播網檔案 Header 在第 2 行 (Row 1)")
                else: 
                     # Fallback check
                     if '版位' in df_sub_temp.columns:
                         sub_header = 0
                
                df_sub = pd.read_excel(subnetwork_path, header=sub_header, dtype=str)
                df_sub.columns = [str(c).strip() for c in df_sub.columns]
                
                # Target col: '版位' (Placement ID)
                target_sub_col = '版位'
                if target_sub_col not in df_sub.columns:
                     print(f"⚠️ 警告: 子聯播網檔案找不到 '版位' 欄位. Available: {df_sub.columns}")
                else:
                    sub_placements = set(df_sub[target_sub_col].astype(str).str.strip())
                    print(f"   共有 {len(sub_placements)} 個子聯播網版位 ID")
                    
                    # Match against '版位編號' in final_df
                    final_df['子聯播網'] = final_df['版位編號'].apply(lambda x: '子聯播網' if str(x).strip() in sub_placements else None)
                    
                    hit_count = final_df['子聯播網'].notna().sum()
                    print(f"   比對結果: 共 {hit_count} 筆資料被標記為 子聯播網")
                    
            except Exception as e:
                print(f"⚠️ 子聯播網處理失敗: {e}")
        
        # 4. 重新調整欄位順序，將供應商/網站放在較醒目的位置
        cols = final_df.columns.tolist()
        # 重新排列順序
        order = ['日期', '小時', '供應商名稱', '網站', '網站名稱', '版位編號', '版位名稱', 'antifroud', '知名媒體', '子聯播網']
        # 僅保留實際存在的欄位
        order = [c for c in order if c in cols]
        remaining = [c for c in cols if c not in order]
        final_df = final_df[order + remaining]
        
        # 5. 儲存結果
        print(f"📤 正在儲存最終整合報表至: {output_path}")
        final_df.to_excel(output_path, index=False)
        
        # 統計成功比對率
        match_count = final_df['供應商名稱'].notna().sum()
        total_count = len(final_df)
        print(f"✅ 整合完成！")
        print(f"📊 統計: 時報共 {total_count} 筆，成功對應到供應商資訊: {match_count} 筆 (比對率: {match_count/total_count:.1%})")
        
        return output_path

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    hourly = "/Users/mattkuo/Downloads/sample-Viewability_20260125-20260126_hourly_report.xlsx"
    ssp = "/Users/mattkuo/Downloads/SSP_2026-01-26_2026-01-27_(一般媒體).xlsx"
    merge_reports(hourly, ssp)
