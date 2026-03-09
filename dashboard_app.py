import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# Set page config
# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="IAS 廣告成效儀表板 v1.1.2")

__version__ = "v1.1.2"

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

# --- ROBUST CALCULATION ENGINE ---
# --- ROBUST CALCULATION ENGINE ---
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
    sivt_num = find_col_robust(c, "Sophisticated Invalid Traffic", 'count')
    givt_num = find_col_robust(c, "General Invalid Traffic", 'count')
    
    if i_den:
        den_v = target_df[i_den]
        if i_num:
            target_df['% IVT'] = (target_df[i_num] / den_v * 100).replace([np.inf, -np.inf], 0).fillna(0)
            
        if sivt_num:
            target_df['% SIVT'] = (target_df[sivt_num] / den_v * 100).replace([np.inf, -np.inf], 0).fillna(0)
        
        if givt_num:
            target_df['% GIVT'] = (target_df[givt_num] / den_v * 100).replace([np.inf, -np.inf], 0).fillna(0)
    
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

def to_excel_download(df, file_name):
    """
    將 DataFrame 轉換為具有百分比格式的 Excel 檔案供下載
    """
    output = io.BytesIO()
    # 建立副本以進行格式化處理
    export_df = df.copy()
    
    # 識別百分比欄位 (包含 % 或 peak_value)
    perc_cols = [c for c in export_df.columns if '%' in str(c) or 'peak_value' in str(c)]
    
    # 將百分比欄位除以 100，以便 Excel 套用百分比格式
    for col in perc_cols:
        export_df[col] = export_df[col] / 100.0

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        # 設定百分比格式 (0.00%)
        # openpyxl column index is 1-based
        for idx, col in enumerate(export_df.columns):
            if col in perc_cols:
                cell_col = idx + 1
                for row_idx in range(2, len(export_df) + 2):
                    worksheet.cell(row=row_idx, column=cell_col).number_format = '0.00%'
                    
    output.seek(0)
    return output

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
        
        # 標準化「子聯播網」欄位：空白值 -> '非子聯播網'
        if '子聯播網' in df.columns:
            df['子聯播網'] = df['子聯播網'].fillna('').astype(str).str.strip()
            df['子聯播網'] = df['子聯播網'].replace('', '非子聯播網')
            # 確保只有兩種值：'子聯播網' 或 '非子聯播網'
            df.loc[df['子聯播網'] != '子聯播網', '子聯播網'] = '非子聯播網'
        
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
main_file = os.path.join(BASE_DIR, "data", "00_全媒體整合報表_版位級別.csv")
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
    
    # 預設使用日間模式 (由 .streamlit/config.toml 控制)
    # 若需手動切換，請點擊右上角 Settings -> Theme
    plotly_template = "plotly_white" 

    st.sidebar.header("📂 資料載入 (Data Loading)")
    
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

    st.markdown("---")
    st.markdown("**🎯 表現過濾 (Performance Filter)**")
    eligible_threshold = st.number_input("曝光量門檻 (Eligible Volume >= X)", min_value=0, value=0, step=100, help="隱藏 Eligible Ads 低於此數值的項目 (供應商/網站/版位)")

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

# --- UNIFIED FILTERING FUNCTION ---
def apply_global_filters(target_df):
    """
    統一套用側邊欄篩選器至任何 DataFrame
    """
    if target_df.empty:
        return target_df
        
    m = pd.Series([True] * len(target_df))
    
    # 供應商
    if 'suppliers' in globals() and suppliers:
        if 'supp_exclude' in globals() and supp_exclude:
            m &= ~target_df['供應商名稱'].isin(suppliers)
        else:
            m &= target_df['供應商名稱'].isin(suppliers)
            
    # 小時
    if 'hours' in globals() and hours:
        h_strs = [str(h) for h in hours]
        if 'hour_exclude' in globals() and hour_exclude:
            m &= ~target_df['小時'].astype(str).isin(h_strs)
        else:
            m &= target_df['小時'].astype(str).isin(h_strs)
            
    # 網站
    if 'sites' in globals() and sites:
        if 'site_exclude' in globals() and site_exclude:
            m &= ~target_df['網站名稱'].isin(sites)
        else:
            m &= target_df['網站名稱'].isin(sites)
            
    # 子聯播網
    if 'subnetwork_opts' in globals() and subnetwork_opts and '子聯播網' in target_df.columns:
        is_sn = (target_df['子聯播網'] == '子聯播網')
        if not ('子聯播網' in subnetwork_opts and '非子聯播網' in subnetwork_opts):
            if '子聯播網' in subnetwork_opts: m &= is_sn
            elif '非子聯播網' in subnetwork_opts: m &= ~is_sn
            
    # Antifraud
    if 'antifraud_opts' in globals() and antifraud_opts and 'antifroud' in target_df.columns:
        is_af = (target_df['antifroud'] == 'antifroud')
        if not ('Antifraud (違規)' in antifraud_opts and 'Clean (正常)' in antifraud_opts):
            if 'Antifraud (違規)' in antifraud_opts: m &= is_af
            elif 'Clean (正常)' in antifraud_opts: m &= ~is_af
            
    # 知名媒體
    if 'famous_opts' in globals() and famous_opts and '知名媒體' in target_df.columns:
        is_fm = (target_df['知名媒體'] == '知名媒體')
        if not ('知名媒體' in famous_opts and '非知名媒體' in famous_opts):
            if '知名媒體' in famous_opts: m &= is_fm
            elif '非知名媒體' in famous_opts: m &= ~is_fm
            
    # --- 曝光量閥值過濾 (New) ---
    # 注意：此過濾器通常套用於聚合後的結果，但在基礎過濾時我們暫不套用
    # 以免誤刪了還沒被加總的原始資料列
            
    return target_df[m].copy()


# --- METRIC HELPER ---
def calculate_metrics(data_df):
    def get_sum(keyword):
        # 尋找包含關鍵字但不帶 % 的欄位
        possible_cols = [c for c in data_df.columns if keyword in c and '%' not in c]
        if not possible_cols:
            possible_cols = [c for c in data_df.columns if keyword in c]
        
        if possible_cols:
            # 確保內容是數值型態 (移除逗號)
            series_clean = data_df[possible_cols[0]].astype(str).str.replace(',', '', regex=False)
            return pd.to_numeric(series_clean, errors='coerce').sum()
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
        '% RVI': rate_rvi,
        # 新增 Eligible Counts 以支援報表上的流量顯示
        'Eligible Ads for Invalid Traffic': eligible_ivt,
        'Measured Ads': measured_v,
        'Eligible ads for quality': eligible_qi,
        'Total Eligible Ads for Site Quality': eligible_sq,
        'Total Eligible Ads for Brand Suitability': eligible_bs
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
            # --- 套用統一全域篩選器 ---
            df = apply_global_filters(df_full)
            
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
    
            # --- 曝光量閥值 (New Global Link) ---
            # 如果側邊欄有設定閥值，則優先使用。如果沒有，則使用本地設定。
            min_eligible = globals().get('eligible_threshold', 0)

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
                display_cols = ['供應商名稱', '網站名稱', '版位名稱', '版位編號'] + all_raw_metrics

            # 重新計算百分比指標
            agg_df = robust_calc(agg_df)
            
            # --- 動態鎖定最終排序指標 ---
            actual_soul_metric = find_col_robust(agg_df.columns, soul_key, 'rate')
            if not actual_soul_metric:
                # Fallback mapping
                if soul_key == "Quality": actual_soul_metric = "% Quality Ads"
                elif soul_key == "Viewability": actual_soul_metric = "% Viewability"
                elif soul_key == "IVT": actual_soul_metric = '% IVT' # Default
                elif soul_key == "RVI": actual_soul_metric = "% RVI"
                elif soul_key == "Brand Safety": actual_soul_metric = "% Brand Safety Passed"
            
            # 當 Soul Key 為 IVT 時，SIVT 為最優先
            if soul_key == "IVT" and '% SIVT' in agg_df.columns:
                actual_soul_metric = '% SIVT'

            # 定義顯示欄位清單 (重排序：維度 -> 關鍵指標 -> 其他指標 -> 原始數據)
            calculated_perc_cols = ['% Quality Ads', '% Brand Safety Passed', '% IVT', '% SIVT', '% GIVT', '% Viewability', '% RVI']
            
            # 特別處理：若為 IVT 報表，優先顯示 IVT 相關指標
            key_metric_group = []
            if soul_key == "IVT":
                # User Request: Order should be IVT -> SIVT -> GIVT
                # Note: Threshold/Sorting is still based on SIVT (actual_soul_metric)
                key_metric_group = ['% IVT', '% SIVT', '% GIVT']
                # 移除已加入的指標以免重複
                calculated_perc_cols = [c for c in calculated_perc_cols if c not in key_metric_group]
            
            # 準備維度欄位
            if view_level == "供應商":
                dim_cols_final = ['供應商名稱']
            elif view_level == "網站":
                dim_cols_final = ['供應商名稱', '網站名稱']
            else:
                dim_cols_final = ['供應商名稱', '網站名稱', '版位名稱', '版位編號']

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


            # --- 警示標準與打包器 UI 整併 ---
            # override actual_soul_metric for IVT to use SIVT as requested by user
            if soul_key == "IVT" and '% SIVT' in agg_df.columns:
                actual_soul_metric = '% SIVT'

            # --- 專屬達標打包器 UI ---
            st.markdown("---")
            pack_col1, pack_col2 = st.columns([1, 1])
            with pack_col1:
                def_t = 5.0 if any(x in str(actual_soul_metric) for x in ["IVT", "RVI"]) else 70.0
                if actual_soul_metric and "Brand Safety" in actual_soul_metric: def_t = 95.0
                
                is_risk_metric = False
                if actual_soul_metric:
                    is_risk_metric = any(x in actual_soul_metric for x in ["IVT", "RVI", "seeThrough"])
                    
                if is_risk_metric:
                    pack_th = st.number_input(f"🎯 達標/警示門檻: {actual_soul_metric} (≤ %)", value=def_t, min_value=0.0, max_value=100.0, step=0.1, key=f"pack_th_{title_prefix}")
                else:
                    pack_th = st.number_input(f"🎯 達標/警示門檻: {actual_soul_metric} (≥ %)", value=def_t, min_value=0.0, max_value=100.0, step=0.5, key=f"pack_th_{title_prefix}")
            with pack_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                apply_pack = st.checkbox("✅ 執行獨立打包優化 (自動剔除劣質清單使整體達標)", value=False, key=f"apply_pack_{title_prefix}")
                
            if apply_pack and actual_soul_metric and actual_soul_metric in agg_df.columns:
                # 準備貪婪剔除
                dim_col = '供應商名稱' if view_level == '供應商' else ('網站名稱' if view_level == '網站' else '版位編號')
                
                # 確保 agg_df 中包含 dim_col，若無法過濾則放棄
                if dim_col in agg_df.columns:
                    orig_items = agg_df[dim_col].tolist()
                    current_pool = orig_items.copy()
                    
                    max_iters = len(orig_items)
                    iters = 0
                    
                    with st.spinner(f"正在優化 {actual_soul_metric} 的組合..."):
                        while len(current_pool) > 0 and iters < max_iters:
                            iters += 1
                            pool_raw_df = final_df[final_df[dim_col].isin(current_pool)]
                            if pool_raw_df.empty: break
                            
                            pool_total = calculate_metrics(pool_raw_df)
                            
                            # 檢查該單一指標是否達標
                            if actual_soul_metric not in pool_total: break 
                                
                            current_val = pool_total[actual_soul_metric]
                            
                            is_passed = (current_val <= pack_th) if is_risk_metric else (current_val >= pack_th)
                                
                            if is_passed: break # 達標！跳出迴圈
                                
                            # 未達標，剃除當前池子中最差的一個
                            pool_agg = agg_df[agg_df[dim_col].isin(current_pool)]
                            worst_item = pool_agg.loc[pool_agg[actual_soul_metric].idxmax() if is_risk_metric else pool_agg[actual_soul_metric].idxmin(), dim_col]
                                
                            current_pool.remove(worst_item)
                    
                    if len(current_pool) == 0:
                        st.error("⚠️ 條件過於嚴格，即使剔除所有項目也無法使整體達標。")
                        agg_df = agg_df.iloc[0:0] # 清空
                    else:
                        agg_df = agg_df[agg_df[dim_col].isin(current_pool)]
                        st.success(f"✅ 已成功打包！共剔除 {len(orig_items) - len(current_pool)} 筆，保留 {len(current_pool)} 筆，使其整體總結算符合標準。")


            # --- 圓餅圖：不合格網站佔比 (Compliance Pie Charts) ---
            if actual_soul_metric and actual_soul_metric in agg_df.columns:
                limit = pack_th
                
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
                    
                    # 3. 準備表格產生函數
                    # 先計算 "最大表" (Global) 的總流量與總網站數
                    # 用於固定顯示 "總流量" 與 "總網站"
                    
                    # 決定流量指標 (分母) keyword (全域共用)
                    target_denom_kw = "Total Tracked Ads"
                    if "Quality" in actual_soul_metric: target_denom_kw = "Eligible ads for quality"
                    elif "Viewability" in actual_soul_metric: target_denom_kw = "Measured Ads"
                    elif "Invalid" in actual_soul_metric or "IVT" in actual_soul_metric: target_denom_kw = "Eligible Ads for Invalid Traffic"
                    elif "RVI" in actual_soul_metric: target_denom_kw = "Total Eligible Ads for Site Quality"
                    elif "Brand" in actual_soul_metric: target_denom_kw = "Total Eligible Ads for Brand Suitability"
                    
                    # 計算 Global Traffic (需從 df_full - UNFILTERED 計算)
                    # 計算 Global Totals (Filtered)
                    # 這裡需要計算的是「當前篩選條件下的全網流量」作為分母
                    # 因為 make_summary_table 是針對不同子集 (如知名媒體)，分母應統一為 filtered_df 的總流量
                    
                    # 1. 取得當前指標對應的流量欄位名稱
                    global_traffic_col = find_col_robust(final_df.columns, target_denom_kw, 'count')
                    if not global_traffic_col:
                        global_traffic_col = find_col_robust(final_df.columns, "Total Tracked Ads", 'count')
                    if not global_traffic_col and all_raw_metrics: global_traffic_col = all_raw_metrics[0]

                    # 計算 Global Totals
                    # 1. 全網總流量 (Grand Total - Unfiltered) - 用於計算「全網佔比」
                    if global_traffic_col and global_traffic_col in df_full.columns:
                        # 需注意 df_full 的數值可能包含逗號
                        grand_total_traffic = df_full[global_traffic_col].replace(',','', regex=True).astype(float).sum()
                    else:
                        grand_total_traffic = 0

                    # 2. 篩選後總流量 (Grand Total - Filtered) - 用於計算「符合流量佔比 / 不符合流量佔比」 (動態分母)
                    grand_total_traffic_filtered = final_df[global_traffic_col].sum() if global_traffic_col else 0

                    def make_summary_table(df_source, title_text):
                        total_sites_subset = len(df_source)
                        if total_sites_subset == 0:
                            st.caption(f"{title_text} (無數據)")
                            return
                        
                        unqualified_count = df_source['is_unqualified'].sum()
                        qualified_count = total_sites_subset - unqualified_count
                        
                        # 流量計算 (Subset)
                        subset_traffic = df_source[global_traffic_col].sum() if global_traffic_col else 0
                        # 該群體中的不合格流量
                        unq_traffic = df_source[df_source['is_unqualified']][global_traffic_col].sum() if global_traffic_col else 0
                        # 該群體中的合格流量
                        qual_traffic = subset_traffic - unq_traffic
                        
                        # --- 佔比計算 ---
                        # A. 基於全網 (Global)
                        traffic_share_global = (subset_traffic / grand_total_traffic * 100) if grand_total_traffic > 0 else 0
                        qual_share_global = (qual_traffic / grand_total_traffic * 100) if grand_total_traffic > 0 else 0
                        unq_share_global = (unq_traffic / grand_total_traffic * 100) if grand_total_traffic > 0 else 0
                        
                        # B. 基於篩選後 (Filtered) - [NEW] 用戶新增需求
                        # traffic_share_filtered = (subset_traffic / grand_total_traffic_filtered * 100) if grand_total_traffic_filtered > 0 else 0
                        qual_share_filtered = (qual_traffic / grand_total_traffic_filtered * 100) if grand_total_traffic_filtered > 0 else 0
                        unq_share_filtered = (unq_traffic / grand_total_traffic_filtered * 100) if grand_total_traffic_filtered > 0 else 0

                        # 內部合規率 (Quality Rate)
                        qual_rate_internal = (qualified_count / total_sites_subset * 100) if total_sites_subset > 0 else 0
                        unq_rate_internal = (unqualified_count / total_sites_subset * 100) if total_sites_subset > 0 else 0

                        # 建構表格 DataFrame
                        # 用戶指定新增欄位: "符合流量佔比", "不符合流量佔比" (使用篩選後分母)
                        # 保留欄位: "符合流量佔比 (全網)", "不符合流量佔比 (全網)" (使用全網分母)
                        data = {
                            "項目": [
                                "總流量 (Eligible)", 
                                "流量佔比 (全網)", 
                                "符合網站數", 
                                "符合佔比 (Rate)", 
                                "符合流量佔比 (全網)", # Original
                                "符合流量佔比",       # New (Filtered)
                                "不符合網站數", 
                                "不符合佔比 (Rate)", 
                                "不符合流量佔比 (全網)", # Original
                                "不符合流量佔比"        # New (Filtered)
                            ],
                            "數值": [
                                f"{subset_traffic:,.2f}",
                                f"{traffic_share_global:,.2f}%", 
                                f"{qualified_count:,.2f}", 
                                f"{qual_rate_internal:,.2f}%", 
                                f"{qual_share_global:,.2f}%",
                                f"{qual_share_filtered:,.2f}%",
                                f"{unqualified_count:,.2f}", 
                                f"{unq_rate_internal:,.2f}%", 
                                f"{unq_share_global:,.2f}%",
                                f"{unq_share_filtered:,.2f}%"
                            ]
                        }
                        
                        # 轉置表格以呈現橫向 (用戶指定要橫式)
                        st.markdown(f"**{title_text}**")
                        st.dataframe(pd.DataFrame(data).set_index("項目").T, hide_index=False, use_container_width=True)

                    # 4. 顯示三個表格
                    st.markdown("---")
                    
                    # Table 1: 全部網站
                    make_summary_table(agg_site, "📊 整體網站遵循度概況")
                    # 對於整體網站:
                    # 流量佔比應為 100%
                    # 符合佔比 + 不符合佔比 = 100%

                    # Table 2 & 3 Side by Side
                    t_col1, t_col2 = st.columns(2)
                    
                    with t_col1:
                        if '知名媒體' in agg_site.columns:
                            df_famous = agg_site[agg_site['知名媒體'] == '知名媒體']
                            make_summary_table(df_famous, "🌟 知名媒體遵循度")
                        else:
                            st.info("無知名媒體數據")

                    with t_col2:
                        if 'antifroud' in agg_site.columns:
                            df_af = agg_site[agg_site['antifroud'] == 'antifroud']
                            make_summary_table(df_af, "🛡️ Antifraud 遵循度")
                        else:
                            st.info("無 Antifraud 數據")
                    
                    st.markdown("---")

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

                # Formatting: 自動對所有名稱含 %、Rate 的欄位套用百分比格式
                perc_cols = [c for c in df_source.columns if '%' in c or 'Rate' in c or 'rate' in c]
                fmt_dict = {col: "{:.2f}%" for col in perc_cols}
                # 其他數值欄位：加上千分位與小數兩位
                other_cols = [c for c in df_source.columns if c not in perc_cols and pd.api.types.is_numeric_dtype(df_source[c])]
                for col in other_cols:
                    fmt_dict[col] = "{:,.2f}"
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
            
            # 定義格式化字典 (供 style.format 呼叫)
            numeric_cols_for_fmt = all_raw_metrics + [c for c in calculated_perc_cols if c in agg_df.columns]
            fmt = {c: "{:,.2f}%" for c in numeric_cols_for_fmt if '%' in c or 'Rate' in c or 'rate' in c}
            for c in numeric_cols_for_fmt: 
                if c not in fmt: fmt[c] = "{:,.2f}"
            
            pack_t_map = {actual_soul_metric: pack_th} if actual_soul_metric else {}
            styler_total = apply_sub_style(total_sum.style.format(fmt), pack_t_map)
            st.dataframe(styler_total, use_container_width=True, hide_index=True)

            # --- 顯示主要報表 ---
            st.markdown(f"**📋 數據報表內容**")
            styler_main = apply_sub_style(agg_df[display_cols].style.format(fmt), pack_t_map)
            st.dataframe(styler_main, use_container_width=True, height=600, hide_index=True)

        else:
            st.warning(f"找不到檔案: {file_path}")
    except Exception as e:
        st.error(f"透視報表處理錯誤: {e}")
def show_sub_report_tier(file_path, title_prefix):
    """
    通用梯隊報表顯示函數 (專用於總表 2)
    支援雙閾值、梯隊統計、以及整列背景著色
    """
    try:
        df_full = load_data(file_path)
        if df_full.empty:
            st.warning(f"找不到檔案或資料為空: {file_path}")
            return

        # --- 套用統一全域篩選器 ---
        df = apply_global_filters(df_full)
        
        if df.empty:
            st.warning("側邊欄篩選後無資料")
            return

        # 網站名稱歸戶
        if '網站名稱' in df.columns:
            df['網站名稱'] = df['網站名稱'].apply(normalize_site_name)

        # 數據探測
        dim_cols = ['供應商名稱', '網站名稱', '網站', '版位編號', '版位名稱']
        all_raw_metrics = [c for c in df.columns if c not in (dim_cols + ['日期', '小時', 'antifroud', '知名媒體', '子聯播網']) and '%' not in c and 'rate' not in c.lower()]

        # 決定指標類型與靈魂指標
        soul_key = ""
        if "05" in title_prefix: soul_key = "Quality"
        elif "01" in title_prefix: soul_key = "Viewability"
        elif "02" in title_prefix: soul_key = "IVT"
        elif "03" in title_prefix: soul_key = "RVI"
        elif "04" in title_prefix: soul_key = "Brand Safety"

        # --- [NEW] 核心邏輯：決定最終分類指標 (Tier Metric) ---
        # 為了穩定性，先做一次聚合前的計算探測
        temp_agg = df.groupby('供應商名稱')[all_raw_metrics].sum().reset_index()
        temp_agg = robust_calc(temp_agg)
        
        actual_soul_metric = find_col_robust(temp_agg.columns, soul_key, 'rate')
        if not actual_soul_metric:
            fallback = {"Quality": "% Quality Ads", "Viewability": "% Viewability", "IVT": '% IVT', "RVI": "% RVI", "Brand Safety": "% Brand Safety Passed"}
            actual_soul_metric = fallback.get(soul_key, "")

        # 針對 IVT 報表，優先使用 SIVT
        if soul_key == "IVT" and '% SIVT' in temp_agg.columns:
            actual_soul_metric = '% SIVT'

        # --- 第一層 UI: 維度與雙閾值 ---
        ui_col1, ui_col2 = st.columns([2, 3])
        with ui_col1:
            view_level = st.radio(f"🔍 檢視維度 ({title_prefix})", ["供應商", "網站", "版位"], horizontal=True, key=f"tier_v_{title_prefix}")
        
        with ui_col2:
            st.markdown(f"**🎯 梯隊閾值設定 ({actual_soul_metric})**")
            t_col1, t_col2 = st.columns(2)
            # 根據指標性質決定預設值 (排除 SIVT/IVT 以外的 RVI 也算 Risk)
            is_risk_metric = any(x in actual_soul_metric for x in ["IVT", "SIVT", "RVI", "Reduced Value"])
            
            def_t1 = 0.5 if "IVT" in actual_soul_metric or "SIVT" in actual_soul_metric or "RVI" in actual_soul_metric else 70.0
            def_t2 = 10.0 if "IVT" in actual_soul_metric or "SIVT" in actual_soul_metric or "RVI" in actual_soul_metric else 40.0
            if "Brand Safety" in actual_soul_metric:
                def_t1, def_t2 = 90.0, 70.0

            with t_col1:
                t1 = st.number_input(f"第一閾值 (優秀) - {actual_soul_metric}", value=def_t1, step=0.1 if is_risk_metric else 1.0, key=f"t1_{title_prefix}")
            with t_col2:
                t2 = st.number_input(f"第二閾值 (警戒) - {actual_soul_metric}", value=def_t2, step=0.1 if is_risk_metric else 1.0, key=f"t2_{title_prefix}")

        # --- 數據聚合 ---
        if view_level == "供應商":
            agg_df = df.groupby('供應商名稱')[all_raw_metrics].sum().reset_index()
        elif view_level == "網站":
            agg_df = df.groupby(['供應商名稱', '網站名稱'])[all_raw_metrics].sum().reset_index()
        else:
            id_keys = ['供應商名稱', '版位編號']
            agg_numeric = df.groupby(id_keys)[all_raw_metrics].sum()
            other_dims = [c for c in ['網站名稱', '版位名稱'] if c in df.columns]
            if other_dims:
                agg_names = df.groupby(id_keys)[other_dims].first()
                agg_df = pd.concat([agg_names, agg_numeric], axis=1).reset_index()
            else:
                agg_df = agg_numeric.reset_index()

        agg_df = robust_calc(agg_df)

        # 決定流量指標 (分母)
        denom_map = {
            "Quality": "Eligible ads for quality",
            "Viewability": "Measured Ads",
            "IVT": "Eligible Ads for Invalid Traffic",
            "RVI": "Total Eligible Ads for Site Quality",
            "Brand Safety": "Total Eligible Ads for Brand Suitability"
        }
        target_denom_kw = denom_map.get(soul_key, "Total Tracked Ads")
        traffic_col = find_col_robust(agg_df.columns, target_denom_kw, 'count')
        
        if not traffic_col:
            traffic_col = find_col_robust(agg_df.columns, "Total Tracked Ads", 'count')
            if not traffic_col and all_raw_metrics:
                traffic_col = all_raw_metrics[0]

        if not actual_soul_metric or actual_soul_metric not in agg_df.columns:
            st.error(f"找不到對應指標: {soul_key}")
            return



        if soul_key == "IVT" and '% SIVT' in agg_df.columns:
            actual_soul_metric = '% SIVT'


        # --- 時報敏感度：計算時段最差值 ---
        # 我們需要從原始資料 df (小時級別) 中，為每個聚合群組計算其「最差的小時值」
        if view_level == "供應商":
            merge_keys = ['供應商名稱']
        elif view_level == "網站":
            merge_keys = ['供應商名稱', '網站名稱']
        else:
            merge_keys = ['供應商名稱', '版位編號']
            
        # 1. 確保原始資料 df 有計算好的百分比指標 (用於尋找波峰)
        df_with_rates = robust_calc(df.copy())
        
        # 2. 找出每個群組的最差值 (考慮指標方向性)
        if is_risk_metric:
            # 風險指標 (IVT, RVI)：越高越差 -> 找 Max
            peak_series = df_with_rates.groupby(merge_keys)[actual_soul_metric].max().rename('peak_value')
        else:
            # 表現指標 (Quality, Viewability)：越低越差 -> 找 Min
            peak_series = df_with_rates.groupby(merge_keys)[actual_soul_metric].min().rename('peak_value')
            
        # 找出對應的小時 (作怪時段)
        df_merged_peak = df_with_rates.merge(peak_series.reset_index(), on=merge_keys)
        bad_rows = df_merged_peak[df_merged_peak[actual_soul_metric] == df_merged_peak['peak_value']]
        peak_hours_series = bad_rows.groupby(merge_keys)['小時'].apply(lambda x: ", ".join(sorted(x.unique().astype(str)))).rename('作怪時段')
        
        agg_df = agg_df.merge(peak_series, on=merge_keys, how='left')
        agg_df = agg_df.merge(peak_hours_series, on=merge_keys, how='left')

        # --- 梯隊分類邏輯 (考量平均值與小時最差值) ---
        def get_tier_info(row):
            avg_val = row[actual_soul_metric]
            peak_val = row['peak_value']
            
            # 原本僅看平均會得到的梯隊 (Original Tier)
            if is_risk_metric:
                if avg_val > t2: orig_tier = 1
                elif avg_val > t1: orig_tier = 2
                else: orig_tier = 3
                
                # 計算波峰梯隊 (Peak Tier)
                if peak_val > t2: peak_tier = 1
                elif peak_val > t1: peak_tier = 2
                else: peak_tier = 3
            else:
                if avg_val < t2: orig_tier = 1
                elif avg_val < t1: orig_tier = 2
                else: orig_tier = 3
                
                # 計算波峰梯隊 (Peak Tier) - 反向指標
                if peak_val < t2: peak_tier = 1
                elif peak_val < t1: peak_tier = 2
                else: peak_tier = 3
                
            # 修正判定邏輯：
            # 1. 若平均值本來就很差 (orig_tier 為 1 或 2)，則優先維持在該梯隊 (顯示紅/黃)
            # 2. 只有當平均值很好 (orig_tier 為 3)，但有波峰異常 (peak_tier < 3) 時，才降級為 Tier 4 (紫色)
            
            if orig_tier < 3:
                # 平均值已達罰值，維持原判，不顯示為「作怪」
                display_tier = orig_tier
                is_downgraded = False
            else:
                # 平均值優秀 (Tier 3)
                if peak_tier < 3:
                    # 但有波峰導致被拉低 -> Tier 4 (特定時段作怪)
                    display_tier = 4
                    is_downgraded = True
                else:
                    # 平均與波峰皆優秀
                    display_tier = 3
                    is_downgraded = False
            
            return pd.Series([display_tier, is_downgraded], index=['tier', 'is_downgraded'])
        
        agg_df[['tier', 'is_downgraded']] = agg_df.apply(get_tier_info, axis=1)

        # 計算 Global Total Traffic (用於計算佔比)
        if traffic_col in df_full.columns:
            grand_total_traffic = df_full[traffic_col].sum()
        else:
            grand_total_traffic = 0

        if traffic_col in agg_df.columns and grand_total_traffic > 0:
            agg_df['流量佔比 (%)'] = (agg_df[traffic_col] / grand_total_traffic * 100)
        else:
            agg_df['流量佔比 (%)'] = 0

        # --- 顯示梯隊摘要 (四表並列佈局) ---
        st.markdown(f"**📊 梯隊分析摘要 ({actual_soul_metric})**")
        st.caption("💡 判定邏輯：除平均值外，若任一時段(Hourly Peak)超過門檻亦會自動降級。")
        
        tier_names = {1: "🔴 第一梯隊 (需處理)", 2: "🟡 第二梯隊 (關注)", 3: "🟢 第三梯隊 (優秀)"}
        
        cols = st.columns(4)
        
        # 準備資料
        for i, tier_id in enumerate([1, 2, 3]):
            tier_df = agg_df[agg_df['tier'] == tier_id]
            count = len(tier_df)
            traffic = tier_df[traffic_col].sum() if traffic_col and traffic_col in tier_df.columns else 0
            
            # 分母：全網總流量
            share = (traffic / grand_total_traffic * 100) if grand_total_traffic > 0 else 0
            avg_val = tier_df[actual_soul_metric].mean() if count > 0 else 0
            
            # [NEW] 計算該梯隊內的符合/不符合流量佔比 (相對於全網)
            # 判斷標準：是否超過設定的罰值 (使用 tier_id 對應的罰值大致判斷，或直接用數據本身)
            # 這裡簡單定義：該梯隊的流量中，有多少比例是符合/不符合的 (相對於全網)
            # 但由於已經分梯隊了，Tier 1 幾乎都是不符合，Tier 3 幾乎都是符合
            # 用戶需求應該是想看這個梯隊佔全網的流量中，有多少是 Clean，有多少是 Dirty
            
            # 為了精確，我們重新計算該梯隊內的 Clean/Dirty 流量
            # 需回到原始細節數據判定? 這裡 agg_df 已經是聚合後的數據
            # 我們假設：agg_df 的每一列 (供應商/網站) 本身就有由 soul metric 決定的良率
            
            # 更好的做法：
            # 符合流量 = 該梯隊所有項目的 (流量 * (1 - 違規率))
            # 不符合流量 = 該梯隊所有項目的 (流量 * 違規率)
            # 注意：actual_soul_metric 若為風險指標 (% IVT/SIVT)，則值即為違規率
            
            if is_risk_metric:
                # 風險指標: 值越小越好。 違規量 = 流量 * 指標%
                # 需注意 % 是 0-100，計算時要除以 100
                unq_vol = (tier_df[traffic_col] * tier_df[actual_soul_metric] / 100).sum()
                qual_vol = traffic - unq_vol
            else:
                # 效益指標: 值越大越好 (Quality)。 違規量 = 流量 * (100 - 指標%)
                qual_vol = (tier_df[traffic_col] * tier_df[actual_soul_metric] / 100).sum()
                unq_vol = traffic - qual_vol

            qual_share_global = (qual_vol / grand_total_traffic * 100) if grand_total_traffic > 0 else 0
            unq_share_global = (unq_vol / grand_total_traffic * 100) if grand_total_traffic > 0 else 0

            with cols[i]:
                st.markdown(f"**{tier_names[tier_id]}**")
                summary_data = {
                    "項目": [f"{'供應商' if view_level=='供應商' else '網站'}數", "總流量 (Eligible)", "流量佔比 (%)", f"{actual_soul_metric}平均值", "符合流量佔比 (全網)", "不符合流量佔比 (全網)"],
                    "數值": [f"{count}", f"{traffic:,.0f}", f"{share:.2f}%", f"{avg_val:.2f}%", f"{qual_share_global:.2f}%", f"{unq_share_global:.2f}%"]
                }
                st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)

        # 第四個表：特定時段作怪 (第 4 梯隊)
        downgraded_df = agg_df[agg_df['tier'] == 4]
        dg_count = len(downgraded_df)
        dg_traffic = downgraded_df[traffic_col].sum() if traffic_col and traffic_col in downgraded_df.columns else 0
        dg_share = (dg_traffic / grand_total_traffic * 100) if grand_total_traffic > 0 else 0
        dg_avg = downgraded_df[actual_soul_metric].mean() if dg_count > 0 else 0
        
        # 計算 Tier 4 的合規/不合規
        if is_risk_metric:
            dg_unq_vol = (downgraded_df[traffic_col] * downgraded_df[actual_soul_metric] / 100).sum()
            dg_qual_vol = dg_traffic - dg_unq_vol
        else:
            dg_qual_vol = (downgraded_df[traffic_col] * downgraded_df[actual_soul_metric] / 100).sum()
            dg_unq_vol = dg_traffic - dg_qual_vol
            
        dg_qual_share = (dg_qual_vol / grand_total_traffic * 100) if grand_total_traffic > 0 else 0
        dg_unq_share = (dg_unq_vol / grand_total_traffic * 100) if grand_total_traffic > 0 else 0
        
        with cols[3]:
            st.markdown("**⚠️ 特定時段作怪**")
            dg_summary = {
                "項目": [f"{'供應商' if view_level=='供應商' else '網站'}數", "總流量 (Eligible)", "流量佔比 (%)", f"{actual_soul_metric}平均值", "符合流量佔比 (全網)", "不符合流量佔比 (全網)"],
                "數值": [f"{dg_count}", f"{dg_traffic:,.0f}", f"{dg_share:.2f}%", f"{dg_avg:.2f}%", f"{dg_qual_share:.2f}%", f"{dg_unq_share:.2f}%"]
            }
            st.dataframe(pd.DataFrame(dg_summary), hide_index=True, use_container_width=True)

        # --- 排序與著色顯示 ---
        # 為了讓用戶看清楚「為什麼被降級」，將 peak_value 加入顯示
        agg_df = agg_df.sort_values(by=actual_soul_metric, ascending=not is_risk_metric)
        
        st.markdown("**📋 詳細數據列表**")
        
        # --- 梯隊篩選器 (UI) ---
        tier_filter_options = {1: "🔴 1", 2: "🟡 2", 3: "🟢 3", 4: "🟣 4"}
        selected_tier_ids = st.multiselect(
            "過濾梯隊", 
            options=[1, 2, 3, 4], 
            default=[1, 2, 3, 4], 
            format_func=lambda x: tier_filter_options[x],
            key=f"tier_filter_{title_prefix}"
        )
        
        # 套用篩選
        display_df = agg_df[agg_df['tier'].isin(selected_tier_ids)].copy()
        
        # 更新顯示欄位
        dim_cols_final = ['供應商名稱', '網站名稱'] if view_level != "供應商" else ['供應商名稱']
        if view_level == "版位": 
            dim_cols_final.extend(['版位名稱', '版位編號'])
        
        perc_cols = ['% Quality Ads', '% Brand Safety Passed', '% IVT', '% SIVT', '% GIVT', '% Viewability', '% RVI']
        # 加入 '流量佔比 (%)', '作怪時段' 與 'peak_value'
        display_cols = dim_cols_final + [c for c in perc_cols if c in display_df.columns] + ['流量佔比 (%)', 'peak_value', '作怪時段'] + all_raw_metrics
        
        # 著色邏輯
        def style_tier(row):
            colors = {
                1: 'background-color: rgba(255, 50, 50, 0.1)',   # Red
                2: 'background-color: rgba(255, 193, 7, 0.1)',   # Yellow
                3: 'background-color: rgba(40, 167, 69, 0.1)',   # Green
                4: 'background-color: rgba(155, 89, 182, 0.1)'   # Purple
            }
            return [colors.get(row['tier'], '')] * len(row)

        format_dict = {c: "{:.2f}%" for c in display_cols if '%' in c or c == 'peak_value'}
        for c in all_raw_metrics: format_dict[c] = "{:,.0f}"

        st.dataframe(
            display_df[display_cols + ['tier']].style.apply(style_tier, axis=1).format(format_dict),
            use_container_width=True, height=600, hide_index=True
        )

        # --- Excel 下載按鈕 ---
        excel_data = to_excel_download(display_df[display_cols], f"TierReport_{title_prefix}.xlsx")
        st.download_button(
            label="📊 匯出此表為 Excel (完美比例格式) ⬇️",
            data=excel_data,
            file_name=f"IAS_TierReport_{title_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_btn_{title_prefix}"
        )

    except Exception as e:
        st.error(f"梯隊報表處理錯誤: {e}")

# --- TABS ---
def render_hourly_report(df, key_suffix):
    st.markdown("### 📈 時報趨勢分析")
    if df.empty:
        st.warning("無資料")
        return

    hourly_groups = df.groupby('小時')
    hourly_rows = []
    for hour, group in hourly_groups:
        metrics = calculate_metrics(group)
        metrics['Hour'] = int(hour) if str(hour).isdigit() else 99
        hourly_rows.append(metrics)
    hourly_res = pd.DataFrame(hourly_rows).sort_values('Hour')
    
    col_ctrl1, col_ctrl2 = st.columns([3, 1])
    with col_ctrl1:
        # 使用 key_suffix 確保元件 ID 唯一
        selected_metrics = st.multiselect("📍 選擇顯示指標", options=all_metrics_list, default=all_metrics_list, key=f"h_m_{key_suffix}")
    with col_ctrl2:
        use_log_scale = st.checkbox("🔍 開啟對數刻度", value=True, key=f"h_log_{key_suffix}")

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
        template=plotly_template,
        xaxis=dict(title="Hour", tickmode='linear', dtick=1),
        yaxis=dict(title="High Range (%)", tickformat=".2f"), 
        yaxis2=yaxis2_config,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5), height=500, hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key_suffix}")
    
    st.subheader("📋 詳細數據報表")
    cols_to_show = ['Total Tracked Ads'] + selected_metrics
    total_row = calculate_metrics(df)
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

# --- SUPPLIER HOURLY TREND REPORT (Hour 2) ---
def render_supplier_trend_report(df, selected_suppliers, key_suffix):
    st.markdown("### 🏢 供應商小時趨勢對照 (時報 2)")
    
    if df.empty:
        st.warning("無資料")
        return

    # 1. 供應商選擇邏輯
    is_default_mode = False
    if not selected_suppliers:
        is_default_mode = True
        # 尋早正確的曝光量欄位名稱 (避免 KeyError)
        tracked_ads_col = next((c for c in df.columns if 'Total Tracked Ads' in c and '%' not in c), None)
        if tracked_ads_col:
            top_suppliers = df.groupby('供應商名稱')[tracked_ads_col].sum().nlargest(4).index.tolist()
            st.info(f"💡 側邊欄尚未選擇供應商，預設顯示曝光量 Top 4 + 其他其於：{', '.join(top_suppliers)}")
            active_supps = top_suppliers
        else:
            # 備案：隨便取 4 個或是全部
            active_supps = df['供應商名稱'].unique()[:4].tolist()
    else:
        active_supps = selected_suppliers

    # 過濾資料
    # 本次畫圖包含主選中項
    plot_df = df[df['供應商名稱'].isin(active_supps)].copy()
    
    # --- [Special Request] 計算「其他 (不含前四大)」 ---
    other_df = pd.DataFrame()
    label_other = "其他 (不含前四大)"
    if is_default_mode:
        other_df = df[~df['供應商名稱'].isin(active_supps)].copy()
        # 強制將這些資料標記為「其他」維度，方便後續聚合
        other_df['供應商名稱'] = label_other

    # 合併 plot_df 與 other_df 用於繪圖與表格
    combined_plot_df = pd.concat([plot_df, other_df]) if not other_df.empty else plot_df
    
    # 過濾小時 0-23
    combined_plot_df = combined_plot_df[pd.to_numeric(combined_plot_df['小時'], errors='coerce').between(0, 23)]
    
    if combined_plot_df.empty:
        st.warning("選中的資料在該時段無數據")
        return

    # 2. 顏色映射 (確保顏色一致)
    colors = px.colors.qualitative.Plotly
    supp_color_map = {supp: colors[i % len(colors)] for i, supp in enumerate(sorted(active_supps))}
    if not other_df.empty:
        supp_color_map[label_other] = "#999999" # 灰色代表其他

    # 3. 數據聚合 (按供應商與小時)
    hourly_groups = combined_plot_df.groupby(['供應商名稱', '小時'])
    
    combined_data = []
    for (supp, hour), group in hourly_groups:
        m = calculate_metrics(group)
        m['Supplier'] = supp
        m['Hour'] = int(hour)
        combined_data.append(m)
    
    agg_res = pd.DataFrame(combined_data)
    
    # 3.5 介面控制：對數刻度
    use_log_scale = st.checkbox("🔍 開啟對數刻度 (時報 2)", value=True, key=f"h2_log_{key_suffix}")

    # 4. 循環渲染每個指標的圖表
    display_supps = active_supps + ([label_other] if not other_df.empty else [])
    for metric in all_metrics_list:
        with st.expander(f"📈 {metric} 趨勢對照", expanded=True):
            fig = go.Figure()
            
            for supp in display_supps:
                supp_df = agg_res[agg_res['Supplier'] == supp].sort_values('Hour')
                if not supp_df.empty:
                    fig.add_trace(go.Scatter(
                        x=supp_df['Hour'],
                        y=supp_df[metric],
                        name=supp,
                        mode='lines+markers',
                        line=dict(color=supp_color_map[supp]),
                        hovertemplate='Hour: %{x}<br>Value: %{y:.2f}%'
                    ))
            
            yaxis_config = dict(title="百分比 (%)", tickformat=".2f")
            if use_log_scale: yaxis_config['type'] = 'log'

            fig.update_layout(
                title=f"{metric} - 趨勢對照圖",
                template=plotly_template,
                xaxis=dict(title="小時 (Hour)", tickmode='linear', dtick=1, range=[-0.5, 23.5]),
                yaxis=yaxis_config,
                height=400,
                margin=dict(t=50, b=50, l=50, r=50),
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                hovermode="x"
            )
            st.plotly_chart(fig, use_container_width=True, key=f"supp_trend_{metric}_{key_suffix}")

    # 5. 彙總數據表 (Summary Table with Dimensional Breakdown)
    st.markdown("---")
    st.subheader("📋 表現彙總 (Performance Summary)")
    
    # --- 第一層 UI: 維度選擇 ---
    h2_view_level = st.radio("🔍 檢視維度 (時報 2)", ["供應商", "網站", "版位"], horizontal=True, key=f"h2_v_lvl_{key_suffix}")
    
    # 決定聚合鍵 (Aggregation Keys)
    if h2_view_level == "供應商":
        agg_keys = ['供應商名稱']
    elif h2_view_level == "網站":
        agg_keys = ['供應商名稱', '網站名稱']
    else:
        agg_keys = ['供應商名稱', '網站名稱', '版位編號', '版位名稱']

    # 準備聚合用的資料 (套用歸戶)
    # 表格資料也包含「其他」集合體，但僅在「供應商」維度下有意義
    # 如果檢視維度是供應商，可以直接顯示「其他」這一列
    # 如果是網站或版位，則不適合顯示「其他」這個大集合，因為層級不對
    table_df = combined_plot_df.copy()
    if h2_view_level != "供應商" and not other_df.empty:
        # 如果不是供應商維度，移除「其他」集合體，只顯示前四大明細
        table_df = table_df[table_df['供應商名稱'] != label_other]

    if '網站名稱' in table_df.columns:
        table_df['網站名稱'] = table_df['網站名稱'].apply(normalize_site_name)

    # 執行聚合與計量
    groups = table_df.groupby(agg_keys)
    summary_rows = []
    for name, group in groups:
        m = calculate_metrics(group)
        if isinstance(name, tuple):
            for k, v in zip(agg_keys, name): m[k] = v
        else:
            m[agg_keys[0]] = name
        summary_rows.append(m)
    
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows).set_index(agg_keys)
        
        # --- 套用曝光量閥值 (New) ---
        # 我們找出相關的 Eligible 欄位進行過濾
        # 基於 calculate_metrics 的邏輯，這裡檢查所有的 Eligible ads 欄位
        if 'eligible_threshold' in globals() and eligible_threshold > 0:
            # 優先檢查核心過濾欄位 (通常是所有指標的母體)
            vol_col = 'Total Tracked Ads'
            if vol_col in summary_df.columns:
                summary_df = summary_df[summary_df[vol_col] >= eligible_threshold]

        if summary_df.empty:
            st.info(f"無符合門檻 (>= {eligible_threshold}) 的數據")
            return

        # 顯示欄位：曝光量 + 8 大指標
        display_cols = ['Total Tracked Ads'] + all_metrics_list
        # 確保欄位存在 (排除 index 欄位以免重複顯示)
        actual_display_cols = [c for c in display_cols if c in summary_df.columns and c not in agg_keys]
        
        summary_final = summary_df[actual_display_cols]
        # 排序：曝光量由大到小
        if 'Total Tracked Ads' in summary_final.columns:
            summary_final = summary_final.sort_values('Total Tracked Ads', ascending=False)
        
        # 設定格式
        format_map = {c: "{:.2f}%" for c in all_metrics_list if c in summary_final.columns}
        # 針對非百分比的數值指標，加上千分位與小數第二位
        for c in summary_final.columns:
            if c not in format_map and pd.api.types.is_numeric_dtype(summary_final[c]):
                format_map[c] = "{:,.2f}"
            
        st.dataframe(summary_final.style.format(format_map), use_container_width=True, height=500)
    else:
        st.info("無彙總數據")

# 更新 Tab 定義：增加一個時報分頁
tab1, tab1_new, tab2, tab3, tab4 = st.tabs(["🕒 時報 1 (Hourly)", "🕒 時報 2 (Hourly)", "📊 總表 1", "📊 總表 2", "📈 圖表分析"])

# === TAB 1: HOURLY 1 ===
with tab1:
    render_hourly_report(filtered_df, "tab1")

# === TAB 1_NEW: HOURLY 2 ===
with tab1_new:
    st.info("💡 此分頁顯示各指標在不同供應商間的小時變動趨勢。線條代表側邊欄選中的供應商。")
    render_supplier_trend_report(filtered_df, suppliers, "tab2")

# === TAB 2: 總表 1 ===
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
        
        # --- 報表切換器 ---
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
            index=0,
            key="report_choice_tab1"
        )
        
        if report_choice == "📊 供應商表現排行 (Master)":
            st.subheader("供應商表現列表")
            
            # [NEW] 計算篩選後的全網總流量 (作為分母)
            # 必須使用 robust converting 因為原始數據可能有逗號
            def get_robust_sum(df, col):
                if col not in df.columns: return 0
                return pd.to_numeric(df[col].astype(str).str.replace(',', '', regex=False), errors='coerce').sum()
                
            grand_total_filtered = get_robust_sum(filtered_df, 'Total Tracked Ads')

            supp_groups = filtered_df.groupby('供應商名稱')
            supp_rows = []
            for supp, group in supp_groups:
                 m = calculate_metrics(group)
                 m['Supplier'] = str(supp)
                 
                 # [NEW] 計算符合/不符合流量
                 # 符合 (Compliant) = antifroud != 'antifroud'
                 # 不符合 (Non-Compliant) = antifroud == 'antifroud'
                 if 'antifroud' in group.columns:
                     compliant_group = group[group['antifroud'] != 'antifroud']
                     non_compliant_group = group[group['antifroud'] == 'antifroud']
                     
                     comp_vol = get_robust_sum(compliant_group, 'Total Tracked Ads')
                     non_comp_vol = get_robust_sum(non_compliant_group, 'Total Tracked Ads')
                 else:
                     comp_vol = get_robust_sum(group, 'Total Tracked Ads')
                     non_comp_vol = 0
                 
                 # 計算佔比 (分母為篩選後的總流量)
                 m['符合流量佔比 (%)'] = (comp_vol / grand_total_filtered * 100) if grand_total_filtered > 0 else 0
                 m['不符合流量佔比 (%)'] = (non_comp_vol / grand_total_filtered * 100) if grand_total_filtered > 0 else 0

                 supp_rows.append(m)
            
            supp_res = pd.DataFrame(supp_rows)
            
            # --- 套用曝光量閥值 (New) ---
            if 'eligible_threshold' in globals() and eligible_threshold > 0:
                vol_col = 'Total Tracked Ads'
                if vol_col in supp_res.columns:
                    supp_res = supp_res[supp_res[vol_col] >= eligible_threshold]

            if supp_res.empty:
                st.info(f"無符合門檻 (>= {eligible_threshold}) 的數據")
            else:
                sort_col = 'Total Tracked Ads'
                # 已將打包器移至各別 01~05 子表中，此處只作基本表現數據顯示
                supp_detail_res = supp_res.set_index('Supplier')
                
                # 移動新欄位到前面 (Supplier 之後)
                cols_order = list(supp_detail_res.columns)
                # 優先欄位
                priority = ['符合流量佔比 (%)', '不符合流量佔比 (%)']
                # 移除優先欄位如果存在
                rest = [c for c in cols_order if c not in priority]
                # 重組
                final_cols = priority + rest
                supp_detail_res = supp_detail_res[final_cols]
                
                format_dict_supp = {c: "{:.2f}%" for c in supp_detail_res.columns if '%' in c}
                if sort_col in format_dict_supp:
                    del format_dict_supp[sort_col]
                format_dict_supp[sort_col] = "{:,.0f}"
                
                st.dataframe(supp_detail_res.style.format(format_dict_supp), use_container_width=True, height=600)
            
        elif report_choice == "💎 05 優質曝光明細":
            show_sub_report("/Users/mattkuo/Projects/IAS-Dashboard/data/05_優質曝光整合報表_版位級別.csv", "05 優質曝光")
        elif report_choice == "🏗️ 03 網站品質明細":
            show_sub_report("/Users/mattkuo/Projects/IAS-Dashboard/data/03_網站品質整合報表_版位級別.csv", "03 網站品質")
        elif report_choice == "🚫 02 無效流量明細":
            show_sub_report("/Users/mattkuo/Projects/IAS-Dashboard/data/02_無效流量整合報表_版位級別.csv", "02 無效流量")
        elif report_choice == "👁️ 01 可視性明細":
            show_sub_report("/Users/mattkuo/Projects/IAS-Dashboard/data/01_可視性廣告整合報表_版位級別.csv", "01 可視性")
        elif report_choice == "🛡️ 04 品牌安全性明細":
            show_sub_report("/Users/mattkuo/Projects/IAS-Dashboard/data/04_品牌安全性整合報表_版位級別.csv", "04 品牌安全性")

# === TAB 3: 總表 2 (梯隊系統) ===
with tab3:
    st.header("總表分析（梯隊系統）")
    st.caption("🎯 使用雙閾值梯隊分類系統")
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
        
        # --- 報表切換器 ---
        report_choice2 = st.selectbox(
            "📋 切換報表檢視 (Select View)",
            options=[
                "📊 供應商表現排行 (Master)",
                "💎 05 優質曝光明細",
                "🏗️ 03 網站品質明細",
                "🚫 02 無效流量明細",
                "👁️ 01 可視性明細",
                "🛡️ 04 品牌安全性明細"
            ],
            index=0,
            key="report_choice_tab2"
        )
        
        # TODO: 為每個報表實作雙閾值梯隊系統
        st.info("⚠️ 總表2的雙閾值梯隊系統正在開發中...")
        
        if report_choice2 == "📊 供應商表現排行 (Master)":
            # --- 第一層 UI: 維度 ---
            ui_col1, ui_col2 = st.columns([2, 3])
            with ui_col1:
                master_view_level = st.radio("🔍 檢視維度 (Master)", ["供應商", "網站", "版位"], horizontal=True, key="master_view_level")
            
            # --- 聚合數據 (移到 UI 之前以取得可用指標) ---
            if master_view_level == "供應商":
                agg_keys = ['供應商名稱']
            elif master_view_level == "網站":
                agg_keys = ['供應商名稱', '網站名稱']
            else:
                agg_keys = ['供應商名稱', '網站名稱', '版位編號', '版位名稱']
            
            groups = filtered_df.groupby(agg_keys)
            agg_rows = []
            for name, group in groups:
                m = calculate_metrics(group)
                if isinstance(name, tuple):
                    for k, v in zip(agg_keys, name): m[k] = v
                else:
                    m[agg_keys[0]] = name
                agg_rows.append(m)
            supp_res = pd.DataFrame(agg_rows)
            
            # 靈魂指標判定
            tier_metric = '% SIVT'
            if tier_metric not in supp_res.columns: 
                tier_metric = '% IVT'

            with ui_col2:
                st.markdown(f"**🎯 梯隊閾值設定 ({tier_metric})**")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    threshold_1 = st.number_input(f"第一門檻 (優秀) - {tier_metric}", min_value=0.0, max_value=100.0, value=0.5, step=0.1, key="master_t1")
                with col_t2:
                    threshold_2 = st.number_input(f"第二門檻 (警戒) - {tier_metric}", min_value=0.0, max_value=100.0, value=10.0, step=0.1, key="master_t2")
            
            # supp_res 已在上方產生
            
            # --- 時報敏感度：計算時段最差值 ---
            df_with_rates = robust_calc(filtered_df.copy())
            peak_series = df_with_rates.groupby(agg_keys)[tier_metric].max().rename('peak_value') # IVT 類指標找 Max
            
            # 找出對應的小時 (作怪時段)
            df_merged_peak = df_with_rates.merge(peak_series.reset_index(), on=agg_keys)
            bad_rows = df_merged_peak[df_merged_peak[tier_metric] == df_merged_peak['peak_value']]
            peak_hours_series = bad_rows.groupby(agg_keys)['小時'].apply(lambda x: ", ".join(sorted(x.unique().astype(str)))).rename('作怪時段')

            supp_res = supp_res.merge(peak_series.reset_index(), on=agg_keys, how='left')
            supp_res = supp_res.merge(peak_hours_series.reset_index(), on=agg_keys, how='left')
            
            def classify_info(row):
                val = row[tier_metric]
                pk = row['peak_value']
                
                # 1. 原始梯隊 (平均值)
                if val > threshold_2: orig_tier = 1
                elif val > threshold_1: orig_tier = 2
                else: orig_tier = 3
                
                # 2. 波峰梯隊
                if pk > threshold_2: peak_tier = 1
                elif pk > threshold_1: peak_tier = 2
                else: peak_tier = 3
                
                # 3. 判定邏輯：平均優先 (Average Priority)
                if orig_tier < 3:
                    # 平均已達罰值 (Tier 1, 2) -> 維持原判
                    display_tier = orig_tier
                    is_down = False
                else:
                    # 平均優秀 (Tier 3) -> 檢查波峰
                    if peak_tier < 3:
                        display_tier = 4
                        is_down = True
                    else:
                        display_tier = 3
                        is_down = False
                    
                return pd.Series([display_tier, is_down], index=['tier', 'is_downgraded'])
            
            supp_res[['tier', 'is_downgraded']] = supp_res.apply(classify_info, axis=1)
            
            # --- 計算流量佔比 ---
            total_traffic_kw = 'Eligible Ads for Invalid Traffic' if 'Eligible Ads for Invalid Traffic' in supp_res.columns else 'Total Tracked Ads'
            grand_total_traffic_supp = supp_res[total_traffic_kw].sum()
            
            if grand_total_traffic_supp > 0:
                supp_res['流量佔比 (%)'] = (supp_res[total_traffic_kw] / grand_total_traffic_supp * 100)
            else:
                supp_res['流量佔比 (%)'] = 0
            
            # --- 顯示梯隊摘要 (四表並列佈局) ---
            st.markdown(f"**📊 梯隊分析摘要 ({tier_metric})**")
            st.caption("💡 判定邏輯：除平均值外，若任一時段(Hourly Peak)超過門檻亦會自動降級。")
            
            t_names = {1: "🔴 第一梯隊 (需處理)", 2: "🟡 第二梯隊 (關注)", 3: "🟢 第三梯隊 (優秀)"}
            
            cols = st.columns(4)
            for i, tid in enumerate([1, 2, 3]):
                t_df = supp_res[supp_res['tier'] == tid]
                t_count = len(t_df)
                t_traffic = t_df[total_traffic_kw].sum()
                t_share = (t_traffic / grand_total_traffic_supp * 100) if grand_total_traffic_supp > 0 else 0
                avg_v = t_df[tier_metric].mean() if t_count > 0 else 0
                
                with cols[i]:
                    st.markdown(f"**{t_names[tid]}**")
                    label_dim = "供應商" if master_view_level == "供應商" else "網站"
                    sum_data = {
                        "項目": [f"{label_dim}數", "總流量 (Eligible)", "流量佔比 (%)", f"{tier_metric}平均值"],
                        "數值": [f"{t_count}", f"{t_traffic:,.0f}", f"{t_share:.2f}%", f"{t_share:.2f}%" if False else f"{avg_v:.2f}%"] 
                    }
                    st.dataframe(pd.DataFrame(sum_data), hide_index=True, use_container_width=True)

            # 第四個表：特定時段作怪 (第 4 梯隊)
            dg_df = supp_res[supp_res['tier'] == 4]
            dg_cnt = len(dg_df)
            dg_trf = dg_df[total_traffic_kw].sum()
            dg_shr = (dg_trf / grand_total_traffic_supp * 100) if grand_total_traffic_supp > 0 else 0
            dg_avg = dg_df[tier_metric].mean() if dg_cnt > 0 else 0
            
            with cols[3]:
                st.markdown("**⚠️ 特定時段作怪**")
                label_dim = "供應商" if master_view_level == "供應商" else "網站"
                dg_sum = {
                    "項目": [f"{label_dim}數", "總流量 (Eligible)", "流量佔比 (%)", f"{tier_metric}平均值"],
                    "數值": [f"{dg_cnt}", f"{dg_trf:,.0f}", f"{dg_shr:.2f}%", f"{dg_avg:.2f}%"]
                }
                st.dataframe(pd.DataFrame(dg_sum), hide_index=True, use_container_width=True)



            # 著色表格
            supp_res = supp_res.sort_values(tier_metric, ascending=False)
            fmt_supp = {c: "{:.2f}%" for c in supp_res.columns if '%' in c}
            
            # 優先格式化 Eligible
            if 'Eligible Ads for Invalid Traffic' in supp_res.columns:
                 fmt_supp['Eligible Ads for Invalid Traffic'] = "{:,.0f}"
            fmt_supp['Total Tracked Ads'] = "{:,.0f}"
            
            def style_supp(row):
                # 使用 RGBA 增加透明度 (0.1)，並不強制文字顏色
                clrs = {
                    1: 'background-color: rgba(255, 50, 50, 0.1)',   # Red with 10% opacity
                    2: 'background-color: rgba(255, 193, 7, 0.1)',   # Yellow/Orange with 10% opacity
                    3: 'background-color: rgba(40, 167, 69, 0.1)',   # Green with 10% opacity
                    4: 'background-color: rgba(155, 89, 182, 0.1)'   # Purple with 10% opacity
                }
                return [clrs.get(row['tier'], '')] * len(row)

            fmt_supp['流量佔比 (%)'] = "{:.2f}%"
            fmt_supp['peak_value'] = "{:.2f}%"

            st.markdown("**📋 表現數據列表**")
            
            # --- 梯隊篩選器 (UI) ---
            m_tier_filter_options = {1: "🔴 1", 2: "🟡 2", 3: "🟢 3", 4: "🟣 4"}
            m_selected_tier_ids = st.multiselect(
                "過濾梯隊", 
                options=[1, 2, 3, 4], 
                default=[1, 2, 3, 4], 
                format_func=lambda x: m_tier_filter_options[x],
                key="master_tier_filter"
            )
            
            # 套用篩選
            m_display_res = supp_res[supp_res['tier'].isin(m_selected_tier_ids)].copy()

            # 確保維度欄位在最前面顯示
            m_perc_cols = ['% Quality Ads', '% Brand Safety Passed', '% IVT', '% SIVT', '% GIVT', '% Viewability', '% RVI']
            m_all_raw_metrics = [c for c in m_display_res.columns if '%' not in c and c not in agg_keys and c not in ['tier', 'is_downgraded', 'peak_value', '作怪時段', '流量佔比 (%)']]
            
            # 加入 '流量佔比 (%)' 到顯示清單
            display_cols = agg_keys + [c for c in m_perc_cols if c in m_display_res.columns] + ['流量佔比 (%)', 'peak_value', '作怪時段'] + m_all_raw_metrics
            
            st.dataframe(
                m_display_res[display_cols + ['tier']].style.apply(style_supp, axis=1).format(fmt_supp), 
                use_container_width=True, 
                height=600,
                hide_index=True
            )

            # --- Master Excel 下載按鈕 ---
            m_excel_data = to_excel_download(m_display_res[display_cols], "MasterReport.xlsx")
            st.download_button(
                label="📊 匯出 Master 報表為 Excel (完美比例格式) ⬇️",
                data=m_excel_data,
                file_name="IAS_MasterReport.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_btn_master"
            )
                
        elif report_choice2 == "💎 05 優質曝光明細":
            show_sub_report_tier("/Users/mattkuo/Projects/IAS-Dashboard/data/05_優質曝光整合報表_版位級別.csv", "05 優質曝光")
        elif report_choice2 == "🏗️ 03 網站品質明細":
            show_sub_report_tier("/Users/mattkuo/Projects/IAS-Dashboard/data/03_網站品質整合報表_版位級別.csv", "03 網站品質")
        elif report_choice2 == "🚫 02 無效流量明細":
            show_sub_report_tier("/Users/mattkuo/Projects/IAS-Dashboard/data/02_無效流量整合報表_版位級別.csv", "02 無效流量")
        elif report_choice2 == "👁️ 01 可視性明細":
            show_sub_report_tier("/Users/mattkuo/Projects/IAS-Dashboard/data/01_可視性廣告整合報表_版位級別.csv", "01 可視性")
        elif report_choice2 == "🛡️ 04 品牌安全性明細":
            show_sub_report_tier("/Users/mattkuo/Projects/IAS-Dashboard/data/04_品牌安全性整合報表_版位級別.csv", "04 品牌安全性")



# === TAB 4: 圖表分析 ===
with tab4:
    st.subheader("📈 每小時分段趨勢分析 (自動模式)")
    st.caption("此圖表根據左側篩選條件自動計算，並將流量拆解為「主」、「子」與「排除子」進行對照。")
    
    # 1. 選擇分析指標
    analysis_metric = st.selectbox("選擇分析指標", options=all_metrics_list, index=0, key="auto_analysis_metric")
    
    # 2. 數據處理
    if not filtered_df.empty:
        # 下載 Plotly 子圖需要的模組 (如果沒匯入)
        from plotly.subplots import make_subplots
        
        # 預防性轉換確保小時為整數，並過濾掉 -1 (不明數據)
        plot_df = filtered_df.copy()
        plot_df['小時'] = pd.to_numeric(plot_df['小時'], errors='coerce').fillna(-1).astype(int)
        plot_df = plot_df[(plot_df['小時'] >= 0) & (plot_df['小時'] <= 23)]
        
        # 定義聚合函數 (基於現有的 calculate_metrics)
        def get_hourly_metrics(target_sub_df):
            if target_sub_df.empty:
                return pd.DataFrame(columns=['小時', analysis_metric, 'Total Tracked Ads'])
            res = target_sub_df.groupby('小時').apply(calculate_metrics).apply(pd.Series).reset_index()
            # 確保欄位存在
            available_cols = ['小時', analysis_metric, 'Total Tracked Ads']
            return res[[c for c in available_cols if c in res.columns]]

        # 計算三條線
        # 1. 主聯播網 (排除子)
        hourly_main = get_hourly_metrics(plot_df[plot_df['子聯播網'] != '子聯播網'])
        # 2. 子聯播網
        hourly_sub = get_hourly_metrics(plot_df[plot_df['子聯播網'] == '子聯播網'])
        # 3. 主(排除子+A)
        hourly_main_ex_a = get_hourly_metrics(plot_df[(plot_df['子聯播網'] != '子聯播網') & (plot_df['antifroud'] != 'antifroud')])
        
        # 整合數據 (0-23 小時)
        all_hours = pd.DataFrame({'小時': range(24)})
        plot_final = all_hours.merge(hourly_main[['小時', analysis_metric, 'Total Tracked Ads']], on='小時', how='left') \
                              .merge(hourly_sub[['小時', analysis_metric]], on='小時', how='left', suffixes=('', '_子')) \
                              .merge(hourly_main_ex_a[['小時', analysis_metric]], on='小時', how='left', suffixes=('', '_排除子A'))
        
        plot_final = plot_final.fillna(0)
        
        # 3. 繪製圖表
        # 新增趨勢線篩選器
        trend_options = ["主聯播網(排除子)", "子聯播網", "主(排除子+A)"]
        selected_trends = st.multiselect("選擇顯示趨勢線", trend_options, default=trend_options)
        
        fig_auto = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.08, 
                                subplot_titles=(f"趨勢分析: {analysis_metric}", "曝光流量 (Total Tracked Ads)"),
                                row_heights=[0.7, 0.3])
        
        # 上半部：趨勢線
        # 第一條 主聯播網(排除子)
        if "主聯播網(排除子)" in selected_trends:
            fig_auto.add_trace(go.Scatter(x=plot_final['小時'], y=plot_final[analysis_metric], 
                                         name="主聯播網(排除子)", line=dict(color='#1f77b4', width=3),
                                         mode='lines+markers'), row=1, col=1)
        
        # 第二條 子聯播網
        if "子聯播網" in selected_trends:
            fig_auto.add_trace(go.Scatter(x=plot_final['小時'], y=plot_final[f"{analysis_metric}_子"], 
                                         name="子聯播網", line=dict(color='#ff7f0e', width=2, dash='dash'),
                                         mode='lines+markers'), row=1, col=1)
        
        # 第三條 主(排除子+A)
        if "主(排除子+A)" in selected_trends:
            fig_auto.add_trace(go.Scatter(x=plot_final['小時'], y=plot_final[f"{analysis_metric}_排除子A"], 
                                         name="主(排除子+A)", line=dict(color='#2ca02c', width=2, dash='dot'),
                                         mode='lines+markers'), row=1, col=1)
        
        # 下半部：曝光數
        fig_auto.add_trace(go.Bar(x=plot_final['小時'], y=plot_final['Total Tracked Ads'], 
                                 name="曝光數", marker_color='rgba(158, 158, 158, 0.5)'), row=2, col=1)
        
        # 配置佈局
        fig_auto.update_layout(height=700, hovermode="x unified", 
                              template=plotly_template,
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        
        fig_auto.update_xaxes(range=[-0.5, 23.5], tickmode='linear', tick0=0, dtick=1)
        fig_auto.update_xaxes(title_text="小時 (Hour)", row=2, col=1)
        fig_auto.update_yaxes(title_text="百分比 (%)", row=1, col=1)
        fig_auto.update_yaxes(title_text="曝光數", row=2, col=1)
        
        st.plotly_chart(fig_auto, use_container_width=True)
        
        # 顯示簡易數據表供查驗
        with st.expander("查看圖表原始數值"):
            st.dataframe(plot_final.rename(columns={
                analysis_metric: "主聯播網(排除子) (%)",
                f"{analysis_metric}_子": "子聯播網 (%)",
                f"{analysis_metric}_排除子A": "主(排除子+A) (%)"
            }), hide_index=True)

    st.markdown("---")
    
    # User Request: UI Text Enlargement
    st.markdown("""
    <style>
        /* Enlarge Headers */
        h1 { font-size: 2.5rem !important; }
        h2 { font-size: 2.1rem !important; }
        h3 { font-size: 1.8rem !important; }
        /* Enlarge labels and markdown text */
        .stMarkdown p, .stAlert p { font-size: 1.25rem !important; line-height: 1.6; }
        .stMetric label { font-size: 1.1rem !important; }
        .stNumberInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

    st.header("主/子聯播網比較分析 (手動模式)")
    st.info("請輸入數值直接產出圖表，不與原始資料連動。此處可產生多張圖表。")

    # User Request: Dynamic Chart Font Size Control
    c_font1, c_font2 = st.columns([1, 4])
    with c_font1:
        chart_font_size = st.slider("📊 手動圖表字體大小 (Font Size)", min_value=12, max_value=28, value=18, step=1, key="manual_chart_font_size")

    def render_manual_chart_block(idx, def_metric, def_bench, def_main, def_sub, font_size, def_label_main="主聯播網 (排除子)", def_label_sub="子聯播網"):
        st.markdown(f"### 圖表 {idx}")
        # Inputs Row 1: Metric and Benchmark
        c_in1, c_in2, c_in3, c_in4 = st.columns(4)
        with c_in1:
            chart_metric = st.text_input(f"指標名稱 ({idx})", value=def_metric, key=f"c_m_{idx}")
        with c_in2:
            benchmark_val = st.number_input(f"Benchmark % ({idx})", value=def_bench, step=0.5, key=f"c_b_{idx}")
        with c_in3:
            label_main = st.text_input(f"主聯播網標籤 ({idx})", value=def_label_main, key=f"c_lbl_main_{idx}")
        with c_in4:
            label_sub = st.text_input(f"子聯播網標籤 ({idx})", value=def_label_sub, key=f"c_lbl_sub_{idx}")
        
        # Inputs Row 2: Values
        c_val1, c_val2, c_val3, c_val4 = st.columns(4)
        with c_val1:
            st.write("") # Spacer
        with c_val2:
            st.write("") # Spacer
        with c_val3:
            val_main = st.number_input(f"主聯播網數值 ({idx})", value=def_main, step=0.01, key=f"c_main_{idx}")
        with c_val4:
            val_sub = st.number_input(f"子聯播網數值 ({idx})", value=def_sub, step=0.01, key=f"c_sub_{idx}")

        # Data Prep
        val_main_float = float(val_main)
        val_sub_float = float(val_sub)
        
        chart_data = {
            "Category": [label_main, label_sub],
            "Value": [val_main_float, val_sub_float],
        }
        df_chart = pd.DataFrame(chart_data)
        
        # Diff Annotations
        diff_main = val_main_float - benchmark_val
        txt_main = f"{val_main_float:.2f}%<br>({diff_main:+.2f}%)" 
        diff_sub = val_sub_float - benchmark_val
        txt_sub = f"{val_sub_float:.2f}%<br>({diff_sub:+.2f}%)"
        df_chart["Text"] = [txt_main, txt_sub]
        
        # Plotting (Width 50%)
        col_chart, col_empty = st.columns(2)
        with col_chart:
            color_map = {label_main: "#1f77b4", label_sub: "#ff7f0e"}
            
            # Using numeric X-axis for extreme spacing control
            x_main = 1.0
            x_sub = 1.05  # Distance between centers is 0.05
            bar_width = 0.045 # Each bar is 0.045 wide
            # Gap will be: distance (0.05) - width (0.045) = 0.005 (very close)

            fig = go.Figure()
            
            # Add Main Network Bar
            fig.add_trace(go.Bar(
                x=[x_main],
                y=[val_main_float],
                text=[txt_main],
                textposition='auto',
                name=label_main,
                marker_color=color_map[label_main],
                width=bar_width,
                textfont=dict(size=font_size)
            ))
            
            # Add Sub Network Bar
            fig.add_trace(go.Bar(
                x=[x_sub],
                y=[val_sub_float],
                text=[txt_sub],
                textposition='auto',
                name=label_sub,
                marker_color=color_map[label_sub],
                width=bar_width,
                textfont=dict(size=font_size)
            ))

            fig.update_layout(
                title=dict(
                    text=f"{chart_metric} - Networks vs Benchmark ({benchmark_val}%)",
                    font=dict(size=font_size + 4)
                ),
                yaxis_title=dict(text="Percent (%)", font=dict(size=font_size - 2)),
                showlegend=False,
                template=plotly_template, # Added template here
                # Numeric axis settings (Adjusted for left-alignment per user request)
                xaxis=dict(
                    tickvals=[x_main, x_sub],
                    ticktext=[label_main, label_sub],
                    tickfont=dict(size=font_size),
                    range=[x_main - 0.05, x_main + 0.35], # Lower bound close to x_main, upper bound far from x_sub
                    fixedrange=True
                ),
                yaxis=dict(tickfont=dict(size=font_size - 2)),
                font=dict(size=font_size - 2),
                hoverlabel=dict(font_size=font_size - 2),
                margin=dict(t=60, b=60, l=40, r=40),
                height=500,
                bargap=0 # Not relevant for numeric axis but safe to set
            )
            
            fig.add_hline(y=benchmark_val, line_dash="dash", line_color="red", 
                          annotation_text=f"Benchmark: {benchmark_val}%", 
                          annotation_position="top left",
                          annotation_font_size=font_size - 2)
            
            max_val = max(val_main_float, val_sub_float, benchmark_val)
            if max_val > 0:
                fig.update_yaxes(range=[0, max_val * 1.15])
            
            st.plotly_chart(fig, use_container_width=True, key=f"manual_fig_{idx}")
            # st.dataframe(df_chart[['Category', 'Value']], hide_index=True) # Optional summary
        
        st.markdown("---")

    # Render 4 Blocks
    # 使用者要求的四張圖表設定
    render_manual_chart_block(1, "% Quality Ads", 75.0, 74.93, 68.66, chart_font_size)
    render_manual_chart_block(2, "% Brand Safety", 91.47, 74.93, 68.67, chart_font_size)
    render_manual_chart_block(3, "% Viewability", 66.75, 50.67, 21.60, chart_font_size)
    render_manual_chart_block(4, "% IVT", 0.51, 0.86, 0.92, chart_font_size)
