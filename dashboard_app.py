import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# Set page config
# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="IAS 廣告成效儀表板 v1.1.1")

__version__ = "v1.1.1"

# --- GLOBAL UTILS (Moved from sidebar) --- SECURITY CHECK ---
def check_password():
    """Returns `True` if the user had the correct password."""
    # 1. Smart Auth: Check Headers
    try:
        headers = st.context.headers
        if headers:
            cf_ip = headers.get("Cf-Connecting-Ip") or headers.get("cf-connecting-ip")
            cf_ray = headers.get("Cf-Ray") or headers.get("cf-ray")
            forwarded = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for")
            host = headers.get("Host") or headers.get("host")
            is_external = (cf_ip is not None) or (cf_ray is not None) or (forwarded is not None) or ("trycloudflare.com" in str(host))
            if not is_external:
                return True
    except Exception as e:
        print(f"Header Check Error: {e}")
        pass
        
    if 'password_correct' not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct:
        return True

    st.markdown("### 🔒 請輸入密碼以存取儀表板 (External Access)")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if password == "24450379":
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ 密碼錯誤 (Password incorrect)")
    return False

if not check_password():
    st.stop()

# --- APP BEGINS ---

# Custom CSS
st.markdown("""
<style>
    .metric-container {
        background-color: #f9f9f9;
        border: 1px solid #ddd;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .metric-label { font-size: 0.9rem; color: #555; }
    .metric-value { font-size: 1.2rem; font-weight: bold; color: #000; }
    .stDataFrame { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- GLOBAL UTILS ---
def clean_col_name(c):
    return str(c).strip().replace('\n', '').replace('\r', '')

import re
def normalize_site_name(name):
    if not isinstance(name, str): return name
    clean_name = name
    
    # 0. 預處理：全形轉半形 (以防萬一)
    clean_name = clean_name.replace('（', '(').replace('）', ')')

    # 1. 移除年份 (2020-2029)
    clean_name = re.sub(r'202[0-9]', '', clean_name)
    
    # 2. 移除指定雜訊關鍵字 (不受大小寫影響)
    remove_keywords = [
        '-exchange', '_exchange', ' exchange', 
        '-openbidding', '_openbidding',
        '-adserver', '_adserver',
        ' - header bidding', '_header bidding',
        '(Direct)', ' Direct',
        '(特開流量)', 'new', '_twmanga'
    ]
    
    for k in remove_keywords:
        clean_name = re.sub(re.escape(k), '', clean_name, flags=re.IGNORECASE)

    # 3. 移除結尾的純數字 (例如 "石頭小說3" -> "石頭小說")
    clean_name = re.sub(r'\d+$', '', clean_name)

    # 4. 移除純數字或亂數結尾的前導符號 (例如 "_123" -> "")
    clean_name = re.sub(r'[_-]\d+$', '', clean_name)
    
    return clean_name.strip(' _-')

def find_col_robust(cols, keyword, preferred_type='count'):
    """
    intelligent column finder.
    preferred_type: 'count' (no % in name) or 'rate' (has % in name)
    """
    keyword = keyword.lower()
    # 1. 優先找完全包含關鍵字且符合類型的
    for c in cols:
        c_low = c.lower()
        if keyword in c_low:
            if preferred_type == 'count' and '%' not in c and 'rate' not in c_low:
                return c
            if preferred_type == 'rate' and ('%' in c or 'rate' in c_low):
                return c
    
    # 2. 次選：只要包含關鍵字就好
    for c in cols:
        if keyword in c.lower():
            return c
    return None

@st.cache_data
def load_data(file_path):
    try:
        # 智慧路徑探測：如果存在「...拷貝.csv」版，優先讀取新版 (Mini 檔案)
        copy_path = file_path.replace(".csv", "拷貝.csv")
        actual_path = copy_path if os.path.exists(copy_path) else file_path
        
        if not os.path.exists(actual_path):
            return pd.DataFrame()
            
        # 使用 low_memory=False 處理混合型別
        df = pd.read_csv(actual_path, dtype=object, on_bad_lines='skip')
        
        # 清洗欄位名稱
        df.columns = [clean_col_name(c) for c in df.columns]
        
        # 優化：將歸戶邏輯移至此處 (Cached)，避免每次 UI 交互都重跑
        if '網站名稱' in df.columns:
            df['網站名稱'] = df['網站名稱'].apply(normalize_site_name)
        
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'], format='%Y%m%d', errors='coerce')
        
        # 數值轉換
        dim_keywords = ['日期', '小時', '版位', '供應商', '網站', 'antifroud', '媒體', '聯播網']
        for col in df.columns:
            is_dim = any(k in col for k in dim_keywords)
            if is_dim:
                continue
            
            # 數值清洗逻辑
            vals = df[col].astype(str).str.replace(',', '').replace(['nan', 'None', '', ' '], '0')
            # 處理原始數據中的百分比。如果有 %，拿掉它。
            # 注意：IAS 01 報表中的百分比是 100x 放大（如 547.95% 代表 5.47%），
            # 但我們這裡先直接取數值，後面 robust_calc 會用 raw count 重新算
            vals = vals.str.replace('%', '')
            df[col] = pd.to_numeric(vals, errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        return pd.DataFrame()

main_file = "/Users/matt/IAS-Dashboard/data/00_全媒體整合報表_版位級別.csv"
df = load_data(main_file)
if df.empty:
    st.stop()

# --- PRE-CALCULATE SORTS ---
supplier_col = '供應商名稱'
tracked_ads_col = 'Total Tracked Ads (Viewability)'
if tracked_ads_col not in df.columns:
    tracked_ads_col = 'Total Tracked Ads' # Fallback

supplier_stats = df.groupby(supplier_col)[tracked_ads_col].sum().sort_values(ascending=False)
sorted_suppliers = supplier_stats.index.tolist()

site_stats = df.groupby('網站名稱')[tracked_ads_col].sum().sort_values(ascending=False)
sorted_sites = site_stats.index.tolist()

import re
import io

# ... (Existing imports) ...

# --- SIDEBAR ---
with st.sidebar:
    if st.button("Logout"):
        st.session_state.password_correct = False
        st.rerun()
    # Sidebar Styling
    st.sidebar.title(f"IAS Dashboard {__version__}")
    st.sidebar.markdown("---")
    
    st.sidebar.header("📂 資料載入 (Data Loading)")
with st.sidebar.expander("詳細篩選 (Filters)", expanded=True):
    # 供應商篩選
    c1, c2 = st.columns([4, 1.5])
    with c1:
        suppliers = st.multiselect("供應商名稱", options=sorted_suppliers, help="留空代表全選 (All)")
    with c2:
        st.write("") # Spacer
        st.write("")
        supp_exclude = st.checkbox("排除", key="supp_exc", help="勾選後變為「排除模式」：顯示除了選中項目以外的所有供應商")
    
    # 小時篩選
    c_h1, c_h2 = st.columns([4, 1.5])
    with c_h1:
        hours = st.multiselect("小時 (Hour)", options=sorted(df['小時'].unique(), key=lambda x: int(x) if str(x).isdigit() else 99), help="留空代表全選 (All)")
    with c_h2:
        st.write("") 
        st.write("")
        hour_exclude = st.checkbox("排除", key="hour_exc", help="勾選後變為「排除模式」：顯示除了選中時段以外的所有資料")
    
    # 網站篩選
    c3, c4 = st.columns([4, 1.5])
    with c3:
        sites = st.multiselect("網站名稱", options=sorted_sites, help="留空代表全選 (All)")
    with c4:
        st.write("") 
        st.write("")
        site_exclude = st.checkbox("排除", key="site_exc", help="勾選後變為「排除模式」：顯示除了選中項目以外的所有網站")

    subnetwork_opts = st.multiselect("子聯播網", options=['子聯播網', '非子聯播網'])
    antifraud_opts = st.multiselect("Antifroud (違規檢查)", options=['Antifraud (違規)', 'Clean (正常)'])
    famous_opts = st.multiselect("知名媒體篩選", options=['知名媒體', '非知名媒體'])

# --- 網站歸戶預覽工具 (Normalization Preview) ---
st.sidebar.markdown("---")
st.sidebar.header("🛠 網站歸戶工具")
with st.sidebar.expander("歸戶預覽 (Normalization)", expanded=False):
    # normalize_site_name 已移至全域函數

    if st.button("產生歸戶對照表 (Excel)"):
        with st.spinner("正在處理網站歸戶..."):
            # 取得所有不重複網站
            all_sites = df['網站名稱'].dropna().unique()
            res_data = []
            for s in all_sites:
                norm = normalize_site_name(s)
                res_data.append({'原始名稱': s, '歸戶後名稱': norm})
            
            df_norm = pd.DataFrame(res_data)
            # 標記是否有變更
            df_norm['是否變更'] = df_norm['原始名稱'] != df_norm['歸戶後名稱']
            # 排序：有變更的在前
            df_norm = df_norm.sort_values(by=['是否變更', '原始名稱'], ascending=[False, True])
            
            # --- 匯出 Excel ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_norm.to_excel(writer, index=False, sheet_name='歸戶對照表')
            output.seek(0)
            
            st.download_button(
                label="⬇️ 下載 Excel 對照表",
                data=output,
                file_name="site_normalization_preview.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success(f"完成！共 {len(df_norm)} 筆網站數據")

# Filter Logic (Update for Exclude Mode)
mask = pd.Series([True] * len(df))

# 供應商邏輯
if suppliers: 
    if supp_exclude:
        mask &= ~df['供應商名稱'].isin(suppliers)
    else:
        mask &= df['供應商名稱'].isin(suppliers)

# 小時邏輯
if hours: 
    target_hours = [str(h) for h in hours]
    if hour_exclude:
        mask &= ~df['小時'].astype(str).isin(target_hours)
    else:
        mask &= df['小時'].astype(str).isin(target_hours)

# 網站邏輯
if sites:
    if site_exclude:
        mask &= ~df['網站名稱'].isin(sites)
    else:
        mask &= df['網站名稱'].isin(sites)

if subnetwork_opts:
    is_sn = (df['子聯播網'] == '子聯播網')
    if '子聯播網' in subnetwork_opts and '非子聯播網' in subnetwork_opts: pass 
    elif '子聯播網' in subnetwork_opts: mask &= is_sn
    elif '非子聯播網' in subnetwork_opts: mask &= ~is_sn

if antifraud_opts:
    is_af = (df['antifroud'] == 'antifroud')
    if 'Antifraud (違規)' in antifraud_opts and 'Clean (正常)' in antifraud_opts: pass
    elif 'Antifraud (違規)' in antifraud_opts: mask &= is_af
    elif 'Clean (正常)' in antifraud_opts: mask &= ~is_af

if famous_opts:
    is_fm = (df['知名媒體'] == '知名媒體')
    if '知名媒體' in famous_opts and '非知名媒體' in famous_opts: pass
    elif '知名媒體' in famous_opts: mask &= is_fm
    elif '非知名媒體' in famous_opts: mask &= ~is_fm

filtered_df = df[mask]

# --- METRIC HELPER ---
def calculate_metrics(data_df):
    def get_sum(keyword):
        # 尋找包含關鍵字但不帶 % 的欄位
        possible_cols = [c for c in data_df.columns if keyword in c and '%' not in c]
        if not possible_cols:
            possible_cols = [c for c in data_df.columns if keyword in c]
        
        if possible_cols:
            # 確保內容是數值型態
            return pd.to_numeric(data_df[possible_cols[0]], errors='coerce').sum()
        return 0

    # 01 Viewability
    viewable = get_sum('Viewable Impressions')
    measured_v = get_sum('Measured Ads')
    rate_view = (viewable / measured_v * 100) if measured_v > 0 else 0
    
    # 02 IVT
    ivt = get_sum('Invalid Traffic Ads')
    eligible_ivt = get_sum('Eligible Ads for Invalid Traffic')
    rate_ivt = (ivt / eligible_ivt * 100) if eligible_ivt > 0 else 0
    
    # IVT Subtotals
    givt = get_sum('General Invalid Traffic (GIVT)')
    rate_givt = (givt / eligible_ivt * 100) if eligible_ivt > 0 else 0
    
    sivt = get_sum('Sophisticated Invalid Traffic (SIVT)')
    rate_sivt = (sivt / eligible_ivt * 100) if eligible_ivt > 0 else 0
    
    # 03 RVI / Site Quality
    rvi = get_sum('Reduced Value Inventory')
    eligible_sq = get_sum('Total Eligible Ads for Site Quality')
    rate_rvi = (rvi / eligible_sq * 100) if eligible_sq > 0 else 0
    
    seethrough = get_sum('seeThrough Ads')
    rate_seethrough = (seethrough / eligible_sq * 100) if eligible_sq > 0 else 0
    
    # 04 Brand Safety
    bs_passed = get_sum('Brand Suitability Passed Ads')
    eligible_bs = get_sum('Total Eligible Ads for Brand Suitability')
    rate_bs = (bs_passed / eligible_bs * 100) if eligible_bs > 0 else 0
    
    # 05 Quality
    qual = get_sum('Quality Ads')
    eligible_qi = get_sum('Eligible ads for quality Impressions')
    rate_qi = (qual / eligible_qi * 100) if eligible_qi > 0 else 0
    
    # Total Tracked Ads fallback
    tracked_ads = get_sum('Total Tracked Ads')
    
    return {
        'Total Tracked Ads': tracked_ads,
        '% Quality Ads': rate_qi,
        '% Brand Safety Passed': rate_bs,
        '% IVT': rate_ivt,
        '% SIVT': rate_sivt,
        '% GIVT': rate_givt,
        '% Viewability': rate_view,
        '% seeThrough Ads': rate_seethrough,
        '% RVI': rate_rvi
    }

all_metrics_list = ['% Quality Ads','% Brand Safety Passed','% IVT','% SIVT','% GIVT','% Viewability','% seeThrough Ads','% RVI']
high_metrics_def = ['% Viewability', '% Brand Safety Passed', '% Quality Ads']
thresholds = {}

# --- STYLE HELPERS ---
def highlight_total_row(styler):
    def bold_total(row):
        return ['font-weight: bold; color: black; background-color: #e0e0e0'] * len(row) if row.name == 'Total' else [''] * len(row)
    return styler.apply(bold_total, axis=1)

def highlight_alerts(styler):
    def color_threshold(val, metric_name):
        try: v = float(val)
        except: return ''
        limit = thresholds.get(metric_name)
        if limit is None: return ''
        if metric_name in ['% Quality Ads', '% Brand Safety Passed', '% Viewability']:
            return 'color: red; font-weight: bold;' if v < limit else ''
        if metric_name in ['% IVT', '% SIVT', '% GIVT', '% RVI', '% seeThrough Ads']:
            return 'color: red; font-weight: bold;' if v > limit else ''
        return ''
    for col in all_metrics_list:
        if col in styler.columns:
            styler = styler.map(lambda x: color_threshold(x, col), subset=[col])
    return styler

# --- SUB-REPORT HELPER ---
# --- SUB-REPORT HELPER (BI Dynamic Multi-Dimension) ---
def show_sub_report(file_path, title_prefix):
    try:
        # 重要修正：基礎資料應該使用全域篩選後的 filtered_df
        # 但因為每份分表的對應 CSV 可能不同，我們需要載入 CSV 後再套用與側邊欄相同的 mask
        df_full = load_data(file_path)
        if not df_full.empty:
            
            # --- 套用側邊欄全域篩選條件 ---
            g_mask = pd.Series([True] * len(df_full))
            
            # 供應商
            if 'suppliers' in globals() and suppliers: 
                if 'supp_exclude' in globals() and supp_exclude:
                    g_mask &= ~df_full['供應商名稱'].isin(suppliers)
                else:
                    g_mask &= df_full['供應商名稱'].isin(suppliers)
            
            # 小時
            if 'hours' in globals() and hours: 
                target_hours = [str(h) for h in hours]
                if 'hour_exclude' in globals() and hour_exclude:
                    g_mask &= ~df_full['小時'].astype(str).isin(target_hours)
                else:
                    g_mask &= df_full['小時'].astype(str).isin(target_hours)
            
            # 網站
            if 'sites' in globals() and sites: 
                if 'site_exclude' in globals() and site_exclude:
                    g_mask &= ~df_full['網站名稱'].isin(sites)
                else:
                    g_mask &= df_full['網站名稱'].isin(sites)
            
            # 套用進階標籤篩選 (如果該報表有這些欄位)
            if 'subnetwork_opts' in globals() and subnetwork_opts and '子聯播網' in df_full.columns:
                is_sn = (df_full['子聯播網'] == '子聯播網')
                if not ('子聯播網' in subnetwork_opts and '非子聯播網' in subnetwork_opts):
                    if '子聯播網' in subnetwork_opts: g_mask &= is_sn
                    elif '非子聯播網' in subnetwork_opts: g_mask &= ~is_sn

            if 'antifraud_opts' in globals() and antifraud_opts and 'antifroud' in df_full.columns:
                is_af = (df_full['antifroud'] == 'antifroud')
                if not ('Antifraud (違規)' in antifraud_opts and 'Clean (正常)' in antifraud_opts):
                    if 'Antifraud (違規)' in antifraud_opts: g_mask &= is_af
                    elif 'Clean (正常)' in antifraud_opts: g_mask &= ~is_af

            if 'famous_opts' in globals() and famous_opts and '知名媒體' in df_full.columns:
                is_fm = (df_full['知名媒體'] == '知名媒體')
                if not ('知名媒體' in famous_opts and '非知名媒體' in famous_opts):
                    if '知名媒體' in famous_opts: g_mask &= is_fm
                    elif '非知名媒體' in famous_opts: g_mask &= ~is_fm
            
            df = df_full[g_mask].copy()
            
            if df.empty:
                st.warning("側邊欄篩選後無資料")
                return

            # --- 核心修改：套用網站名稱歸戶 (Normalization) ---
            # 必須在篩選後、聚合前執行，這樣才能正確合併數據
            if '網站名稱' in df.columns:
                df['網站名稱'] = df['網站名稱'].apply(normalize_site_name)

            # --- 數據探測 (識別指標欄位) ---
            dim_cols = ['供應商名稱', '網站名稱', '網站', '版位編號', '版位名稱']
            # 只保留原始計數欄位用於加總，排除掉原始 CSV 的百分比欄位以免誤加
            all_raw_metrics = []
            for col in df.columns:
                if col not in (dim_cols + ['日期', '小時', 'antifroud', '知名媒體', '子聯播網']):
                    if '%' not in col and 'rate' not in col.lower():
                        all_raw_metrics.append(col)

            def robust_calc(target_df):
                c = target_df.columns
                # 05 Quality
                q_num = find_col_robust(c, "Quality Ads", 'count')
                q_den = find_col_robust(c, "Eligible ads for quality", 'count')
                if q_num and q_den:
                    target_df['% Quality Ads'] = (target_df[q_num] / target_df[q_den] * 100).replace([np.inf, -np.inf], 0).fillna(0)
                
                # 01 Viewability
                v_num = find_col_robust(c, "Viewable Impressions", 'count')
                v_den = find_col_robust(c, "Measured Ads", 'count')
                if v_num and v_den:
                    target_df['% Viewability'] = (target_df[v_num] / target_df[v_den] * 100).replace([np.inf, -np.inf], 0).fillna(0)
                
                # 02 IVT
                i_num = find_col_robust(c, "Invalid Traffic Ads", 'count')
                i_den = find_col_robust(c, "Eligible Ads for Invalid Traffic", 'count')
                
                # SIVT / GIVT
                # 嘗試放寬關鍵字 (移除 Ads) 以匹配更多變體
                sivt_num = find_col_robust(c, "Sophisticated Invalid Traffic", 'count')
                givt_num = find_col_robust(c, "General Invalid Traffic", 'count')
                
                if i_den:
                    den_v = target_df[i_den]
                    if i_num:
                        target_df['% IIVT'] = (target_df[i_num] / den_v * 100).replace([np.inf, -np.inf], 0).fillna(0)
                        # Rename to standard
                        target_df['% Invalid Traffic'] = target_df['% IIVT']
                        
                    if sivt_num:
                        target_df['% Sophisticated Invalid Traffic (SIVT)'] = (target_df[sivt_num] / den_v * 100).replace([np.inf, -np.inf], 0).fillna(0)
                    
                    if givt_num:
                        target_df['% General Invalid Traffic (GIVT)'] = (target_df[givt_num] / den_v * 100).replace([np.inf, -np.inf], 0).fillna(0)
                
                # 04 Brand Safety
                b_num = find_col_robust(c, "Brand Suitability Passed Ads", 'count')
                b_den = find_col_robust(c, "Total Eligible Ads for Brand Suitability", 'count')
                if b_num and b_den:
                    target_df['% Brand Safety Passed'] = (target_df[b_num] / target_df[b_den] * 100).replace([np.inf, -np.inf], 0).fillna(0)
                
                # 03 RVI
                r_num = find_col_robust(c, "Reduced Value Inventory", 'count')
                r_den = find_col_robust(c, "Total Eligible Ads for Site Quality", 'count')
                if r_num and r_den:
                    target_df['% RVI'] = (target_df[r_num] / target_df[r_den] * 100).replace([np.inf, -np.inf], 0).fillna(0)
                
                return target_df

            def calc_rates(target_df):
                return robust_calc(target_df)

            # --- 指定關鍵關鍵字 (用於自動探測與排序) ---
            soul_key = ""
            if "05" in title_prefix: soul_key = "Quality"
            elif "01" in title_prefix: soul_key = "Viewability"
            elif "02" in title_prefix: soul_key = "IVT"
            elif "03" in title_prefix: soul_key = "RVI"
            elif "04" in title_prefix: soul_key = "Brand Safety"

            # --- 互動控制區 ---
            row1_c1, row1_c2, row1_c3 = st.columns([1.5, 3, 1.2])
            with row1_c1:
                view_level = st.radio(f"🔍 檢視維度", ["供應商", "網站", "版位"], horizontal=True, key=f"v_lvl_{title_prefix}")
            with row1_c2:
                s_cols = st.columns(2)
                selected_supps = s_cols[0].multiselect("🏢 供應商", options=sorted(df['供應商名稱'].unique()), key=f"ms_s_{title_prefix}", placeholder="全部")
                temp_df = df[df['供應商名稱'].isin(selected_supps)] if selected_supps else df
                selected_sites = s_cols[1].multiselect("🌐 網站", options=sorted(temp_df['網站名稱'].unique()), key=f"ms_site_{title_prefix}", placeholder="全部")

            # [FIX] Define min_eligible to prevent NameError
            # --- 進階設定 (Advanced Settings) ---
            with st.sidebar.expander("⚙️ 進階設定 (Advanced)", expanded=True):
                min_eligible = st.number_input("📉 最小樣本數過濾 (Min Eligible)", min_value=0, value=100, step=10, help="隱藏分母 (Eligible) 小於此數值的項目")
            
            # 應用篩選
            final_df = temp_df
            if selected_sites:
                final_df = final_df[final_df['網站名稱'].isin(selected_sites)]
            
            if final_df.empty:
                st.warning("篩選後無資料")
                return

            # --- 數據聚合 ---
            if view_level == "供應商":
                agg_df = final_df.groupby('供應商名稱')[all_raw_metrics].sum().reset_index()
                display_cols = ['供應商名稱'] + all_raw_metrics
            elif view_level == "網站":
                agg_df = final_df.groupby(['供應商名稱', '網站名稱'])[all_raw_metrics].sum().reset_index()
                display_cols = ['供應商名稱', '網站名稱'] + all_raw_metrics
            else:
                # 執行聚合計算
                id_keys = ['供應商名稱', '版位編號']
                name_keys = ['網站名稱', '版位名稱']
                agg_numeric = final_df.groupby(id_keys)[all_raw_metrics].sum()
                agg_names = final_df.groupby(id_keys)[name_keys].first()
                agg_df = pd.concat([agg_names, agg_numeric], axis=1).reset_index()
                display_cols = ['供應商名稱', '網站名稱', '版位名稱'] + all_raw_metrics

            # 重新計算百分比指標
            agg_df = robust_calc(agg_df)
            
            # --- 動態鎖定最終排序指標 ---
            actual_soul_metric = find_col_robust(agg_df.columns, soul_key, 'rate')
            if not actual_soul_metric:
                # Fallback mapping
                if soul_key == "Quality": actual_soul_metric = "% Quality Ads"
                elif soul_key == "Viewability": actual_soul_metric = "% Viewability"
                elif soul_key == "IVT": actual_soul_metric = "% Invalid Traffic" # Default
                elif soul_key == "RVI": actual_soul_metric = "% RVI"
                elif soul_key == "Brand Safety": actual_soul_metric = "% Brand Safety Passed"
            
            # 當 Soul Key 為 IVT 時，SIVT 為最優先
            if soul_key == "IVT" and '% Sophisticated Invalid Traffic' in agg_df.columns:
                actual_soul_metric = '% Sophisticated Invalid Traffic'

            # 定義顯示欄位清單 (重排序：維度 -> 關鍵指標 -> 其他指標 -> 原始數據)
            calculated_perc_cols = ['% Quality Ads', '% Brand Safety Passed', '% Invalid Traffic', '% Sophisticated Invalid Traffic (SIVT)', '% General Invalid Traffic (GIVT)', '% Viewability', '% RVI']
            
            # 特別處理：若為 IVT 報表，優先顯示 IVT 相關指標
            key_metric_group = []
            if soul_key == "IVT":
                # User Request: Order should be IVT -> SIVT -> GIVT
                # Note: Threshold/Sorting is still based on SIVT (actual_soul_metric)
                key_metric_group = ['% Invalid Traffic', '% Sophisticated Invalid Traffic (SIVT)', '% General Invalid Traffic (GIVT)']
                # 移除已加入的指標以免重複
                calculated_perc_cols = [c for c in calculated_perc_cols if c not in key_metric_group]
            
            # 準備維度欄位
            if view_level == "供應商":
                dim_cols_final = ['供應商名稱']
            elif view_level == "網站":
                dim_cols_final = ['供應商名稱', '網站名稱']
            else:
                dim_cols_final = ['供應商名稱', '網站名稱', '版位名稱']

            # 建構最終顯示順序
            # 1. 維度
            display_cols = dim_cols_final[:]
            # 2. 關鍵指標群 (針對特定報表客製化)
            if key_metric_group:
                for km in key_metric_group:
                    if km in agg_df.columns:
                        display_cols.append(km)
            else:
                # 通用：只放 Single Soul Metric
                if actual_soul_metric and actual_soul_metric in agg_df.columns:
                    display_cols.append(actual_soul_metric)
            
            # 3. 其他百分比指標
            for c in calculated_perc_cols:
                if c in agg_df.columns and c not in display_cols:
                    display_cols.append(c)
            # 4. 原始數據 (Raw Counts) - 放在最後
            display_cols.extend(all_raw_metrics)

            # --- 📉 低流量過濾邏輯 (Low Volume Filter) ---
            if min_eligible > 0:
                # 定義分母對照表
                DENOM_KEYWORDS = {
                    "Viewability": "Measured Ads",
                    "IVT": "Eligible Ads for Invalid Traffic",
                    "RVI": "Total Eligible Ads for Site Quality",
                    "Brand Safety": "Total Eligible Ads for Brand Suitability",
                    "Quality": "Eligible ads for quality"
                }
                denom_kw = DENOM_KEYWORDS.get(soul_key)
                if denom_kw:
                    denom_col = find_col_robust(agg_df.columns, denom_kw, 'count')
                    if denom_col:
                        agg_df = agg_df[agg_df[denom_col] >= min_eligible]
            
            agg_df = robust_calc(agg_df) # Filter 後再次確保計算 (其實不用，但安全起見)

            # (Sort logic uses actual_soul_metric which is already defined above)


            # --- 警示標準 UI ---
            with row1_c3:
                curr_t = {}
                if actual_soul_metric and actual_soul_metric in agg_df.columns:
                    def_val = 5.0 if any(x in actual_soul_metric for x in ["IVT", "RVI"]) else 50.0
                    if "Brand Safety" in actual_soul_metric: def_val = 90.0
                    st.markdown(f"**🎯 警示標準**")
                    curr_t[actual_soul_metric] = st.number_input(f"{actual_soul_metric}", min_value=0.0, max_value=100.0, value=def_val, step=1.0, key=f"soul_t_{title_prefix}")
                
            # --- 圓餅圖：不合格網站佔比 (Compliance Pie Charts) ---
            if actual_soul_metric and actual_soul_metric in agg_df.columns:
                limit = curr_t.get(actual_soul_metric, def_val)
                # 判斷標準：是否為「越低越好」的風險指標
                is_risk_metric = any(x in actual_soul_metric for x in ["IVT", "RVI", "seeThrough"])
                
                # 1. 準備網站級別數據 (必須回到網站層級聚合以正確計算網站數)
                # 需從 final_df 重新聚合，因為 agg_df 可能是供應商或版位層級
                site_keys = ['網站名稱', '知名媒體', 'antifroud']
                # 確保這些欄位存在於 final_df
                valid_site_keys = [k for k in site_keys if k in final_df.columns]
                
                # 若無網站名稱，無法計算
                if '網站名稱' in valid_site_keys:
                    # 修正：GroupBy 預設會排除 NaN 的 Key，導致資料遺失。需先填充 NaN。
                    final_df_filled = final_df.copy()
                    for k in valid_site_keys:
                        final_df_filled[k] = final_df_filled[k].fillna('')
                        
                    # 修正：只依據「網站名稱」聚合，避免因為同一網站屬性不一致（如有的有知名媒體有的沒）而被拆成多筆
                    # 屬性欄位取 first，數值欄位取 sum
                    attr_cols = [k for k in valid_site_keys if k != '網站名稱']
                    
                    agg_site = final_df_filled.groupby('網站名稱').agg(
                        {**{col: 'sum' for col in all_raw_metrics},
                         **{col: 'first' for col in attr_cols}}
                    ).reset_index()
                    
                    agg_site = robust_calc(agg_site)
                    
                    # 2. 判定合格與否
                    if is_risk_metric:
                        agg_site['is_unqualified'] = agg_site[actual_soul_metric] > limit
                    else:
                        agg_site['is_unqualified'] = agg_site[actual_soul_metric] < limit
                    
                    # 3. 定義繪圖函數
                    import plotly.graph_objects as go
                    
                    def plot_pie(df_source, title_text):
                        total_count = len(df_source)
                        if total_count == 0:
                            return go.Figure().update_layout(title=f"{title_text}<br>(無數據)")
                        
                        unqualified_count = df_source['is_unqualified'].sum()
                        qualified_count = total_count - unqualified_count
                        
                        unqualified_rate = (unqualified_count / total_count) * 100
                        
                        # 顯示內容：不合格數 / 總數
                        # 顏色：未達標(紅), 達標(灰)
                        fig = go.Figure(data=[go.Pie(
                            labels=['不符合', '符合'],
                            values=[unqualified_count, qualified_count],
                            hole=.4,
                            marker_colors=['#ff4b4b', '#f0f2f6'],
                            textinfo='none', # 不顯示圖上文字，改用中間顯示
                            sort=False
                        )])
                        
                        fig.update_layout(
                            title_text=title_text,
                            title_x=0.5,
                            annotations=[dict(text=f'{unqualified_rate:.1f}%<br>不符', x=0.5, y=0.5, font_size=20, showarrow=False)],
                            margin=dict(t=30, b=0, l=0, r=0),
                            height=200,
                            showlegend=False
                        )
                        return fig

                    # 4. 繪製三個圖表
                    p_col1, p_col2, p_col3 = st.columns(3)
                    
                    # Chart 1: 全部網站
                    with p_col1:
                        st.plotly_chart(plot_pie(agg_site, "整體不符合佔比"), use_container_width=True)
                        st.caption(f"不符合: {agg_site['is_unqualified'].sum()} / 總網站: {len(agg_site)}")

                    # Chart 2: 知名媒體
                    with p_col2:
                        if '知名媒體' in agg_site.columns:
                            # 篩選知名媒體
                            df_famous = agg_site[agg_site['知名媒體'] == '知名媒體']
                            st.plotly_chart(plot_pie(df_famous, "知名媒體不符合佔比"), use_container_width=True)
                            st.caption(f"不符合: {df_famous['is_unqualified'].sum()} / 知名: {len(df_famous)}")
                        else:
                            st.info("無知名媒體欄位")

                    # Chart 3: Antifraud
                    with p_col3:
                        if 'antifroud' in agg_site.columns:
                            # 篩選 Antifraud (假設 antfraud 欄位值為 'antifroud' 代表有標記)
                            # 先前代碼邏輯是: is_af = (df_full['antifroud'] == 'antifroud')
                            df_af = agg_site[agg_site['antifroud'] == 'antifroud']
                            st.plotly_chart(plot_pie(df_af, "Antifraud 不符合佔比"), use_container_width=True)
                            st.caption(f"不符合: {df_af['is_unqualified'].sum()} / Antifraud: {len(df_af)}")
                        else:
                            st.info("無 Antifraud 欄位")

            # --- 地雷優先排序 ---
            if actual_soul_metric and actual_soul_metric in agg_df.columns:
                is_risk = any(x in actual_soul_metric for x in ["IVT", "RVI", "seeThrough"])
                agg_df = agg_df.sort_values(by=actual_soul_metric, ascending=not is_risk)

            # --- 樣式設定函數 (局部套用) ---
            def apply_sub_style(styler, thresholds_map):
                df_source = styler.data
                
                def color_logic(val, m_name):
                    try: v = float(val)
                    except: return ''
                    limit = thresholds_map.get(m_name)
                    if limit is None: return ''
                    
                    # 判斷方向性：部分指標越高越好，部分越低越好
                    # 預設：越高越好 (Quality, Viewability, Brand Safety) -> 低於門檻紅
                    # 風險：越低越好 (IVT, RVI) -> 高於門檻紅
                    is_risk = any(x in m_name for x in ["IVT", "RVI", "seeThrough", "Invalid"])
                    
                    if is_risk:
                        return 'color: #ff4b4b; font-weight: bold' if v > limit else 'color: #28a745'
                    else:
                        return 'color: #ff4b4b; font-weight: bold' if v < limit else 'color: #28a745'
                
                # apply map
                for c in df_source.columns: 
                    if c in thresholds_map:
                        styler.map(lambda v: color_logic(v, c), subset=[c])

                # Formatting: 自動對所有名稱含 % 的欄位套用百分比格式
                perc_cols = [c for c in df_source.columns if '%' in c or 'Rate' in c or 'rate' in c]
                fmt_dict = {col: "{:.2f}%" for col in perc_cols}
                styler.format(fmt_dict)
                
                return styler

            # --- 顯示總計列 ---
            # 只加總原始數值欄位
            total_sum = agg_df[all_raw_metrics].sum().to_frame().T
            total_sum = calc_rates(total_sum)
            st.markdown("**📊 總計 (Total)**")
            
            # 確保總計列的欄位順序與主報表一致 (排除維度欄位)
            # display_cols 包含了維度 + 指標，我們只取總計列中存在的指標部分
            metrics_order = [c for c in display_cols if c in total_sum.columns]
            total_sum = total_sum[metrics_order]
            
            # 定義格式化字典
            numeric_cols_for_fmt = all_raw_metrics + [c for c in calculated_perc_cols if c in agg_df.columns]
            fmt = {c: "{:,.2f}%" for c in numeric_cols_for_fmt if '%' in c}
            for c in numeric_cols_for_fmt: 
                if '%' not in c: fmt[c] = "{:,.0f}"

            styler_total = apply_sub_style(total_sum.style.format(fmt), curr_t)
            st.dataframe(styler_total, use_container_width=True, hide_index=True)

            # --- 顯示主要報表 ---
            st.markdown(f"**📋 數據報表內容**")
            styler_main = apply_sub_style(agg_df[display_cols].style.format(fmt), curr_t)
            st.dataframe(styler_main, use_container_width=True, height=600, hide_index=True)

        else:
            st.warning(f"找不到檔案: {file_path}")
    except Exception as e:
        st.error(f"透視報表處理錯誤: {e}")

# --- TABS ---
tab1, tab2 = st.tabs(["🕒 時報 (Hourly Report)", "📊 總表 (Total Report)"])

# === TAB 1: HOURLY ===
with tab1:
    st.markdown("### 📈 時報趨勢分析")
    if filtered_df.empty:
        st.warning("無資料")
    else:
        hourly_groups = filtered_df.groupby('小時')
        hourly_rows = []
        for hour, group in hourly_groups:
            metrics = calculate_metrics(group)
            metrics['Hour'] = int(hour) if str(hour).isdigit() else 99
            hourly_rows.append(metrics)
        hourly_res = pd.DataFrame(hourly_rows).sort_values('Hour')
        
        col_ctrl1, col_ctrl2 = st.columns([3, 1])
        with col_ctrl1:
            selected_metrics = st.multiselect("📍 選擇顯示指標", options=all_metrics_list, default=all_metrics_list, key="h_m")
        with col_ctrl2:
            use_log_scale = st.checkbox("🔍 開啟對數刻度", value=True, key="h_log")

        fig = go.Figure()
        for m in selected_metrics:
            if m in high_metrics_def:
                fig.add_trace(go.Scatter(x=hourly_res['Hour'], y=hourly_res[m], name=m, mode='lines+markers', yaxis='y1', hovertemplate='%{y:.2f}%'))
            else:
                fig.add_trace(go.Scatter(x=hourly_res['Hour'], y=hourly_res[m], name=m, mode='lines+markers', line=dict(dash='dot'), yaxis='y2', hovertemplate='%{y:.2f}%'))

        yaxis2_config = dict(title="Low Range (%)", overlaying='y', side='right', tickformat=".2f")
        if use_log_scale: yaxis2_config['type'] = 'log'

        fig.update_layout(
            title="8大關鍵指標趨勢圖", 
            xaxis=dict(title="Hour", tickmode='linear', dtick=1),
            yaxis=dict(title="High Range (%)", tickformat=".2f"), 
            yaxis2=yaxis2_config,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5), height=500, hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📋 詳細數據報表")
        cols_to_show = ['Total Tracked Ads'] + selected_metrics
        total_row = calculate_metrics(filtered_df)
        total_row['Hour'] = 'Total'
        total_df = pd.DataFrame([total_row]).set_index('Hour')[cols_to_show]
        total_df = total_df.loc[:, ~total_df.columns.duplicated()]
        
        format_dict = {c: "{:.2f}%" for c in cols_to_show if '%' in c}
        format_dict['Total Tracked Ads'] = "{:,.0f}"

        st.markdown("**總計 (Total)**")
        styler_total = total_df.style.format(format_dict)
        styler_total = highlight_total_row(styler_total)
        st.dataframe(styler_total, use_container_width=True, hide_index=False)
        
        st.markdown("**詳細資料 (Details)**")
        table_df_styled = hourly_res.copy().set_index('Hour')[cols_to_show]
        table_df_styled = table_df_styled.reset_index().drop_duplicates(subset=['Hour']).set_index('Hour')
        st.dataframe(table_df_styled.style.format(format_dict), use_container_width=True, height=500)

# === TAB 2: TOTAL ===
with tab2:
    st.header("總表分析")
    if filtered_df.empty:
        st.warning("無資料")
    else:
        total_metrics = calculate_metrics(filtered_df)
        cols = st.columns(4)
        keys = [k for k in all_metrics_list if k in total_metrics]
        for i, key in enumerate(keys):
            with cols[i % 4]:
                st.metric(label=key, value=f"{total_metrics[key]:.2f}%")
        
        st.markdown("---")
        
        # --- 新增報表切換器 (Selectbox) ---
        report_choice = st.selectbox(
            "📋 切換報表檢視 (Select View)",
            options=[
                "📊 供應商表現排行 (Master)",
                "💎 05 優質曝光明細",
                "🏗️ 03 網站品質明細",
                "🚫 02 無效流量明細",
                "👁️ 01 可視性明細",
                "🛡️ 04 品牌安全性明細"
            ],
            index=0
        )
        
        if report_choice == "📊 供應商表現排行 (Master)":
            st.subheader("供應商表現列表")
            supp_groups = filtered_df.groupby('供應商名稱')
            supp_rows = []
            for supp, group in supp_groups:
                 m = calculate_metrics(group)
                 # 確保這裡抓到的是中文名稱
                 m['Supplier'] = str(supp)
                 supp_rows.append(m)
            
            # 使用 calculate_metrics 裡面回傳的欄位名稱
            supp_res = pd.DataFrame(supp_rows)
            # 找尋正確的流量排序欄位
            sort_col = 'Total Tracked Ads'
            if sort_col in supp_res.columns:
                supp_res = supp_res.sort_values(sort_col, ascending=False)
            
            supp_detail_res = supp_res.set_index('Supplier')
            
            format_dict_supp = {c: "{:.2f}%" for c in supp_detail_res.columns if '%' in c}
            if sort_col in format_dict_supp: # 流量欄位不應該是百分比
                del format_dict_supp[sort_col]
            format_dict_supp[sort_col] = "{:,.0f}"
            
            st.dataframe(supp_detail_res.style.format(format_dict_supp), use_container_width=True, height=600)
            
        elif report_choice == "💎 05 優質曝光明細":
            show_sub_report("/Users/matt/IAS-Dashboard/data/05_優質曝光整合報表_版位級別.csv", "05 優質曝光")
        elif report_choice == "🏗️ 03 網站品質明細":
            show_sub_report("/Users/matt/IAS-Dashboard/data/03_網站品質整合報表_版位級別.csv", "03 網站品質")
        elif report_choice == "🚫 02 無效流量明細":
            show_sub_report("/Users/matt/IAS-Dashboard/data/02_無效流量整合報表_版位級別.csv", "02 無效流量")
        elif report_choice == "👁️ 01 可視性明細":
            show_sub_report("/Users/matt/IAS-Dashboard/data/01_可視性廣告整合報表_版位級別.csv", "01 可視性")
        elif report_choice == "🛡️ 04 品牌安全性明細":
            show_sub_report("/Users/matt/IAS-Dashboard/data/04_品牌安全性整合報表_版位級別.csv", "04 品牌安全性")
