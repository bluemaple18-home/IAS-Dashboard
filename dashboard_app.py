import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page config
st.set_page_config(page_title="全媒體整合報表儀表板", layout="wide")

# --- SECURITY CHECK ---
def check_password():
    """Returns `True` if the user had the correct password."""
    
    # 1. Smart Auth: Check Headers
    try:
        # Use new st.context.headers (Streamlit 1.38+)
        headers = st.context.headers
        
        # DEBUG SECTION (Remove later)
        # with st.expander("🔍 Debug Network Headers (Staff Only)", expanded=True):
        #    st.write(dict(headers))
        
        if headers:
            # Check for Cloudflare-specific headers
            # Note: headers are usually case-insensitive in st.context
            cf_ip = headers.get("Cf-Connecting-Ip") or headers.get("cf-connecting-ip")
            cf_ray = headers.get("Cf-Ray") or headers.get("cf-ray")
            forwarded = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for")
            host = headers.get("Host") or headers.get("host")
            
            # Logic: If ANY sign of external proxy/tunnel is found, treat as External -> Require Password
            is_external = (cf_ip is not None) or (cf_ray is not None) or (forwarded is not None) or ("trycloudflare.com" in str(host))
            
            # Additional Check: If 'Host' is NOT localhost/127.0.0.1, it's likely external (though tunnel rewrites host, sometimes it preserves)
            
            # If it is NOT external, we bypass
            if not is_external:
                # Double check: internal usually has no X-Forwarded-For
                return True
                
    except Exception as e:
        print(f"Header Check Error: {e}")
        pass
        
    # 2. Session State Check
    if 'password_correct' not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # 3. Login Form (Only shows if NOT bypassed above)
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
    /* Try to align headers for split tables */
    .stDataFrame { width: 100%; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    file_path = "./data/00_全媒體整合報表_版位級別.csv"
    try:
        df = pd.read_csv(file_path, dtype=object)
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'], format='%Y%m%d', errors='coerce')
        
        # Numeric Conversion
        for col in df.columns:
            if col in ['日期', '小時', '版位編號', '供應商名稱', '網站', '網站名稱', '版位名稱', 'antifroud', '知名媒體', '子聯播網']:
                continue
            df[col] = (
                df[col].astype(str).str.replace(',', '').str.replace('%', '').replace(['nan', 'None', '', ' '], '0')
            )
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

# --- PRE-CALCULATE SORTS ---
supplier_stats = df.groupby('供應商名稱')['Total Tracked Ads (Viewability)'].sum().sort_values(ascending=False)
sorted_suppliers = supplier_stats.index.tolist()

site_stats = df.groupby('網站名稱')['Total Tracked Ads (Viewability)'].sum().sort_values(ascending=False)
sorted_sites = site_stats.index.tolist()

# --- SIDEBAR ---
with st.sidebar:
  if st.button("Logout"):
        st.session_state.password_correct = False
        st.rerun()

st.sidebar.header("🔍 篩選條件")
with st.sidebar.expander("詳細篩選 (Filters)", expanded=True):
    suppliers = st.multiselect("供應商名稱 (依流量排序)", options=sorted_suppliers)
    hours = st.multiselect("小時 (Hour)", options=sorted(df['小時'].unique(), key=lambda x: int(x) if str(x).isdigit() else 99))
    sites = st.multiselect("網站名稱 (依流量排序)", options=sorted_sites)
    subnetwork_opts = st.multiselect("子聯播網", options=['子聯播網', '非子聯播網'])
    antifraud_opts = st.multiselect("Antifraud (違規)", options=['Antifraud (違規)', 'Clean (正常)'])
    famous_opts = st.multiselect("知名媒體", options=['知名媒體', '非知名媒體'])

# --- FILTERING ---
mask = pd.Series(True, index=df.index)
if suppliers: mask &= df['供應商名稱'].isin(suppliers)
if hours: mask &= df['小時'].isin(hours)
if sites: mask &= df['網站名稱'].isin(sites)

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
    viewable = data_df['Viewable Impressions (Viewability)'].sum()
    measured_v = data_df['Measured Ads (Viewability)'].sum()
    rate_view = (viewable / measured_v * 100) if measured_v > 0 else 0
    
    ivt = data_df['Invalid Traffic Ads (IVT)'].sum()
    eligible_ivt = data_df['Eligible Ads for Invalid Traffic (IVT)'].sum()
    rate_ivt = (ivt / eligible_ivt * 100) if eligible_ivt > 0 else 0
    
    givt = data_df['General Invalid Traffic (GIVT) Ads (IVT)'].sum()
    rate_givt = (givt / eligible_ivt * 100) if eligible_ivt > 0 else 0
    
    sivt = data_df['Sophisticated Invalid Traffic (SIVT) Ads (IVT)'].sum()
    rate_sivt = (sivt / eligible_ivt * 100) if eligible_ivt > 0 else 0
    
    rvi = data_df['Reduced Value Inventory (RVI) Ads (SiteQuality)'].sum()
    eligible_sq = data_df['Total Eligible Ads for Site Quality (SiteQuality)'].sum()
    rate_rvi = (rvi / eligible_sq * 100) if eligible_sq > 0 else 0
    
    # seeThrough (Replaces Proxy)
    seethrough = data_df['seeThrough Ads (SiteQuality)'].sum()
    rate_seethrough = (seethrough / eligible_sq * 100) if eligible_sq > 0 else 0
    
    bs_passed = data_df['Brand Suitability Passed Ads (BrandSuitability)'].sum()
    eligible_bs = data_df['Total Eligible Ads for Brand Suitability (BrandSuitability)'].sum()
    rate_bs = (bs_passed / eligible_bs * 100) if eligible_bs > 0 else 0
    
    qual = data_df['Quality Ads (QualImpressions)'].sum()
    eligible_qi = data_df['Eligible ads for quality Impressions (QualImpressions)'].sum()
    rate_qi = (qual / eligible_qi * 100) if eligible_qi > 0 else 0
    
    return {
        'Total Tracked Ads': data_df['Total Tracked Ads (Viewability)'].sum(),
        '% Quality Ads': rate_qi,
        '% Brand Safety Passed': rate_bs,
        '% IVT': rate_ivt,
        '% SIVT': rate_sivt,
        '% GIVT': rate_givt,
        '% Viewability': rate_view,
        '% seeThrough Ads': rate_seethrough,
        '% RVI': rate_rvi
    }

# --- GLOBAL VARS ---
all_metrics_list = [
    '% Quality Ads',
    '% Brand Safety Passed',
    '% IVT',
    '% SIVT',
    '% GIVT',
    '% Viewability',
    '% seeThrough Ads',
    '% RVI'
]
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

# --- TABS ---
tab1, tab2 = st.tabs(["🕒 時報 (Hourly Report)", "📊 總表 (Total Report)"])

# === TAB 1: HOURLY ===
with tab1:
    st.markdown("### 📈 時報趨勢分析")
    
    if filtered_df.empty:
        st.warning("無資料")
    else:
        # 1. Calc Data
        hourly_groups = filtered_df.groupby('小時')
        hourly_rows = []
        for hour, group in hourly_groups:
            metrics = calculate_metrics(group)
            metrics['Hour'] = int(hour) if str(hour).isdigit() else 99
            hourly_rows.append(metrics)
            
        hourly_res = pd.DataFrame(hourly_rows).sort_values('Hour')
        
        # 2. Charts
        col_ctrl1, col_ctrl2 = st.columns([3, 1])
        
        with col_ctrl1:
            selected_metrics = st.multiselect("📍 選擇顯示指標", options=all_metrics_list, default=all_metrics_list)
        with col_ctrl2:
            use_log_scale = st.checkbox("🔍 開啟對數刻度", value=True) # Default True

        if selected_metrics:
            fig = go.Figure()
            for m in selected_metrics:
                if m in high_metrics_def:
                    fig.add_trace(go.Scatter(x=hourly_res['Hour'], y=hourly_res[m], name=m, mode='lines+markers', yaxis='y1', hovertemplate='%{y:.2f}%'))
            for m in selected_metrics:
                 if m not in high_metrics_def:
                    fig.add_trace(go.Scatter(x=hourly_res['Hour'], y=hourly_res[m], name=m, mode='lines+markers', line=dict(dash='dot'), yaxis='y2', hovertemplate='%{y:.2f}%'))

            yaxis2_config = dict(title="Low Range (%)", overlaying='y', side='right', tickformat=".2f", showgrid=True, zeroline=True, nticks=10, dtick=0.2 if not use_log_scale else None)
            if use_log_scale:
               yaxis2_config['type'] = 'log'
               yaxis2_config['title'] = "Low Range (Log Scale)"
               del yaxis2_config['dtick']; del yaxis2_config['nticks']

            fig.update_layout(
                title="8大關鍵指標趨勢圖", 
                xaxis=dict(title="Hour", tickmode='linear', dtick=1),
                yaxis=dict(title="High Range (%)", tickformat=".2f"), 
                yaxis2=yaxis2_config,
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5), height=500, hovermode="x unified", margin=dict(t=50, b=100)
            )
            st.plotly_chart(fig, use_container_width=True)
            
        # --- THRESHOLD CONTROLS (FORM) ---
        st.markdown("---")
        with st.expander("⚙️ 警示閥值設定 (Thresholds)", expanded=False):
            with st.form("threshold_form"): # Wrap in Form
                st.info("設定指標閥值，當數值觸發條件時，報表將顯示 **紅色字體** 警示。")
                t_cols = st.columns(4)
                thresholds['% Quality Ads'] = t_cols[0].number_input('% Quality Ads (低於警示)', value=50.0, step=0.1)
                thresholds['% Brand Safety Passed'] = t_cols[1].number_input('% Brand Safety (低於警示)', value=90.0, step=0.1)
                thresholds['% Viewability'] = t_cols[2].number_input('% Viewability (低於警示)', value=50.0, step=0.1)
                thresholds['% IVT'] = t_cols[3].number_input('% IVT (高於警示)', value=5.0, step=0.1)
                
                t_cols2 = st.columns(4)
                thresholds['% SIVT'] = t_cols2[0].number_input('% SIVT (高於警示)', value=2.0, step=0.1)
                thresholds['% GIVT'] = t_cols2[1].number_input('% GIVT (高於警示)', value=2.0, step=0.1)
                thresholds['% seeThrough Ads'] = t_cols2[2].number_input('% seeThrough Ads (高於警示)', value=5.0, step=0.1)
                thresholds['% RVI'] = t_cols2[3].number_input('% RVI (高於警示)', value=5.0, step=0.1)
                
                st.form_submit_button("送出設定 (Apply)") # Submit Button
            
        # 3. Table (Split for Sticky Total)
        st.subheader("📋 詳細數據報表")
        
        # Prepare Data
        cols_to_show = ['Total Tracked Ads'] + selected_metrics
        
        # A. Total Row Table
        total_row = calculate_metrics(filtered_df)
        total_row['Hour'] = 'Total'
        total_df = pd.DataFrame([total_row]).set_index('Hour')[cols_to_show]
        
        # B. Detail Rows Table
        table_df = hourly_res.copy()
        table_df['Hour'] = table_df['Hour'].astype(str)
        table_df = table_df.set_index('Hour')[cols_to_show] # Filter cols
        
        # Common Format
        format_dict = {c: "{:.2f}%" for c in cols_to_show if '%' in c}
        format_dict['Total Tracked Ads'] = "{:,.0f}"
        
        # Display Total (Sticky-ish by being separate top table)
        st.markdown("**總計 (Total)**")
        styler_total = total_df.style.format(format_dict)
        styler_total = highlight_total_row(styler_total)
        styler_total = highlight_alerts(styler_total)
        st.dataframe(styler_total, use_container_width=True, hide_index=False) # Separate table
        
        # Display Details
        st.markdown("**詳細資料 (Details)**")
        styler_detail = table_df.style.format(format_dict)
        styler_detail = highlight_alerts(styler_detail)
        st.dataframe(styler_detail, use_container_width=True, height=500) # Scrollable part

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
        st.subheader("供應商表現列表")
        
        supp_groups = filtered_df.groupby('供應商名稱')
        supp_rows = []
        for supp, group in supp_groups:
             m = calculate_metrics(group)
             m['Supplier'] = supp
             supp_rows.append(m)
        
        supp_res = pd.DataFrame(supp_rows).sort_values('Total Tracked Ads', ascending=False)
        
        # Split Total and Details for Tab 2 as well
        # A. Total
        total_row_supp = total_metrics.copy()
        total_row_supp['Supplier'] = 'Total'
        total_supp_df = pd.DataFrame([total_row_supp]).set_index('Supplier')
        
        # B. Detail
        supp_detail_res = supp_res.set_index('Supplier')

        format_dict_supp = {c: "{:.2f}%" for c in supp_detail_res.columns if '%' in c}
        format_dict_supp['Total Tracked Ads'] = "{:,.0f}"

        # Display Total
        st.markdown("**總計 (Total)**")
        styler_supp_total = total_supp_df.style.format(format_dict_supp)
        styler_supp_total = highlight_total_row(styler_supp_total)
        styler_supp_total = highlight_alerts(styler_supp_total)
        st.dataframe(styler_supp_total, use_container_width=True)
        
        # Display Details
        st.markdown("**詳細資料 (Details)**")
        styler_supp_detail = supp_detail_res.style.format(format_dict_supp)
        styler_supp_detail = highlight_alerts(styler_supp_detail)
        st.dataframe(styler_supp_detail, use_container_width=True, height=600)
