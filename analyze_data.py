import pandas as pd
import os

files = [
    "/Users/matt/IAS-Dashboard/data/00_全媒體整合報表_版位級別.csv"
]

def clean_col_name(c):
    return str(c).strip().replace('\n', '').replace('\r', '')

for f in files:
    print(f"Analyzing {f}...")
    try:
        df = pd.read_csv(f, dtype=object, on_bad_lines='skip')
        df.columns = [clean_col_name(c) for c in df.columns]
        
        # Check IVT
        tt_ivt = [c for c in df.columns if "Total Tracked Ads" in c and "IVT" in c]
        el_ivt = [c for c in df.columns if "Eligible Ads for Invalid Traffic" in c]
        
        if tt_ivt and el_ivt:
            c1 = tt_ivt[0]
            c2 = el_ivt[0]
            print(f"Comparing {c1} vs {c2}")
            v1 = pd.to_numeric(df[c1].str.replace(',',''), errors='coerce').fillna(0)
            v2 = pd.to_numeric(df[c2].str.replace(',',''), errors='coerce').fillna(0)
            
            diff = (v1 != v2).sum()
            print(f"  Rows where they differ: {diff} / {len(df)}")
            if diff > 0:
                print("  Sample differences:")
                print(pd.concat([v1, v2], axis=1)[v1 != v2].head())
        else:
            print("  Columns not found for IVT comparison")

        # Check Viewability
        tt_view = [c for c in df.columns if "Total Tracked Ads" in c and "Viewability" in c]
        el_view = [c for c in df.columns if "Measured Ads" in c and "Viewability" in c] # Typically Eligible for Viewability
        
        if tt_view and el_view:
            c1 = tt_view[0]
            c2 = el_view[0]
            print(f"Comparing {c1} vs {c2}")
            v1 = pd.to_numeric(df[c1].str.replace(',',''), errors='coerce').fillna(0)
            v2 = pd.to_numeric(df[c2].str.replace(',',''), errors='coerce').fillna(0)
            
            diff = (v1 != v2).sum()
            print(f"  Rows where they differ: {diff} / {len(df)}")
    except Exception as e:
        print(f"Error: {e}")
