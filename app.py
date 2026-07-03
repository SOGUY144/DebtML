"""
DebtML — Policy Dashboard
แดชบอร์ดวิเคราะห์ความเสี่ยงหนี้ครัวเรือนระดับจังหวัด
สำหรับนักวิเคราะห์นโยบาย / ธปท. / สศช.

Data: NSO Household Socio-Economic Survey (สำรวจภาวะเศรษฐกิจและสังคมของครัวเรือน)
Models: Logistic Regression, Random Forest, LightGBM
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    auc,
)
import lightgbm as lgb
import os

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="DebtML — Policy Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CUSTOM CSS — Premium dark styling
# ============================================================
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Outfit:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main container */
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }

    /* KPI Metric Cards - Premium Glassmorphism */
    .metric-card {
        background: rgba(22, 33, 62, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(255, 107, 107, 0.15);
        border-color: rgba(255, 107, 107, 0.3);
    }
    .metric-value {
        font-family: 'Outfit', sans-serif;
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0;
        line-height: 1.2;
    }
    .metric-label {
        font-family: 'Outfit', sans-serif;
        font-size: 0.9rem;
        color: #A0ABCC;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }

    /* Status badges */
    .badge-risk {
        background: linear-gradient(135deg, #FF416C, #FF4B2B);
        color: white;
        padding: 6px 16px;
        border-radius: 30px;
        font-weight: 600;
        font-size: 0.85rem;
        box-shadow: 0 4px 10px rgba(255, 65, 108, 0.3);
    }
    .badge-stable {
        background: linear-gradient(135deg, #11998e, #38ef7d);
        color: #0E1117;
        padding: 6px 16px;
        border-radius: 30px;
        font-weight: 600;
        font-size: 0.85rem;
        box-shadow: 0 4px 10px rgba(56, 239, 125, 0.2);
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        border-radius: 12px 12px 0 0;
        font-family: 'Outfit', sans-serif;
        font-size: 1rem;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255, 107, 107, 0.1);
        color: #FF6B6B !important;
    }

    /* Header styling */
    .main-header {
        text-align: center;
        padding: 2rem 0 1.5rem 0;
        animation: fadeIn 0.8s ease-out;
    }
    .main-header h1 {
        font-family: 'Outfit', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(to right, #FF6B6B, #FCA048);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        line-height: 1.2;
    }
    .main-header p {
        color: #A0ABCC;
        font-size: 1.1rem;
        font-weight: 300;
        max-width: 650px;
        margin: 0 auto;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-15px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Divider */
    .section-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, rgba(42,42,74,0) 0%, rgba(42,42,74,1) 50%, rgba(42,42,74,0) 100%);
        margin: 2.5rem 0;
    }

    /* What-if result card */
    .whatif-result {
        background: rgba(26, 26, 46, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 107, 107, 0.15);
        border-radius: 16px;
        padding: 2rem;
        margin-top: 1.5rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none;}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADING & FEATURE ENGINEERING (cached)
# ============================================================
@st.cache_data
def load_and_prepare_data():
    """
    อ่าน Excel → Merge → Wide-to-Long → DTI + Label + Lag Features + Growth
    ทำเหมือนใน DebtML.ipynb ทุกประการ
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # --- Debt data ---
    df_debt = pd.read_excel(
        os.path.join(base_dir, "20230521160827_42424.xlsx"), skiprows=2
    )
    df_debt.columns = [
        "Region", "Province", "Purpose",
        "Debt_2547", "Debt_2549", "Debt_2550", "Debt_2552", "Debt_2554",
        "Debt_2556", "Debt_2558", "Debt_2560", "Debt_2562", "Debt_2564", "Debt_2566",
    ]
    df_debt[["Province", "Region"]] = df_debt[["Province", "Region"]].ffill()
    df_debt = df_debt.drop(df_debt.index[-2:])
    df_debt = df_debt.replace("-", 0)

    vicinity_provinces = [
        "กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี",
        "สมุทรปราการ", "นครปฐม", "สมุทรสาคร",
    ]
    df_debt.loc[
        df_debt["Province"].isin(vicinity_provinces), "Region"
    ] = "กรุงเทพมหานครและปริมณฑล"

    df_debt_summary = df_debt[df_debt["Purpose"] == "หนี้สินทั้งสิ้น"].copy()
    df_debt_summary = df_debt_summary.drop(columns=["Purpose"])

    # --- Income data ---
    df_income = pd.read_excel(
        os.path.join(base_dir, "20230521160113_19514.xlsx"), skiprows=2
    )
    df_income = df_income.drop(columns=[df_income.columns[0]])
    df_income.columns = [
        "Region", "Province",
        "Income_2547", "Income_2549", "Income_2550", "Income_2552", "Income_2554",
        "Income_2556", "Income_2558", "Income_2560", "Income_2562", "Income_2564",
        "Income_2566",
    ]
    df_income[["Region"]] = df_income[["Region"]].ffill()
    df_income.loc[
        df_income["Province"].isin(vicinity_provinces), "Region"
    ] = "กรุงเทพมหานครและปริมณฑล"
    df_income = df_income.drop(df_income.index[-1:])
    df_income = df_income.fillna(0)
    df_income_sorted = df_income.sort_values(
        by=["Region", "Province"]
    ).reset_index(drop=True)
    df_income_clean = df_income_sorted[
        df_income_sorted["Region"] != df_income_sorted["Province"]
    ].copy()

    # --- Merge ---
    df_merged = pd.merge(df_income_clean, df_debt_summary, on=["Province", "Region"])

    # --- Wide to Long ---
    df_panel = pd.wide_to_long(
        df_merged,
        stubnames=["Income", "Debt"],
        i=["Region", "Province"],
        j="Year",
        sep="_",
    ).reset_index()

    df_panel["Year"] = df_panel["Year"].astype(int)
    # แปลง Income/Debt เป็นตัวเลข (บาง cell จาก Excel อาจยังเป็น string)
    df_panel["Income"] = pd.to_numeric(df_panel["Income"], errors="coerce").fillna(0)
    df_panel["Debt"] = pd.to_numeric(df_panel["Debt"], errors="coerce").fillna(0)
    df_panel = df_panel.sort_values(["Province", "Year"]).reset_index(drop=True)

    # --- DTI & Label ---
    df_panel["Annual_Income"] = df_panel["Income"] * 12
    # ป้องกัน ZeroDivisionError: แทนที่ 0 ด้วย NaN ก่อนหาร
    df_panel["Annual_Income"] = df_panel["Annual_Income"].replace(0, np.nan)
    df_panel["DTI"] = df_panel["Debt"] / df_panel["Annual_Income"]
    DTI_THRESHOLD = 1.0
    df_panel["Label"] = (df_panel["DTI"] > DTI_THRESHOLD).astype(int)

    # --- Lag features & Annualized Growth ---
    def annualized_growth(curr, prev, gap):
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            g = (curr / prev) ** (1 / gap) - 1
        return g

    # สร้าง Lag features แบบ vectorized (ไม่ใช้ groupby.apply เพราะ pandas ใหม่จะลบ grouping column)
    df_panel = df_panel.sort_values(["Province", "Year"]).reset_index(drop=True)
    grp = df_panel.groupby("Province")

    df_panel["Year_prev"] = grp["Year"].shift(1)
    df_panel["gap"] = df_panel["Year"] - df_panel["Year_prev"]
    df_panel["Debt_lag1"] = grp["Debt"].shift(1)
    df_panel["Income_lag1"] = grp["Income"].shift(1)
    df_panel["DTI_lag1"] = grp["DTI"].shift(1)

    growth_gap = grp["gap"].shift(1)
    debt_lag1_prev = grp["Debt_lag1"].shift(1)
    income_lag1_prev = grp["Income_lag1"].shift(1)

    df_panel["Debt_growth_ann"] = annualized_growth(
        df_panel["Debt_lag1"], debt_lag1_prev, growth_gap
    )
    df_panel["Income_growth_ann"] = annualized_growth(
        df_panel["Income_lag1"], income_lag1_prev, growth_gap
    )

    # --- One-hot encode Region ---
    df_panel_encoded = pd.get_dummies(df_panel, columns=["Region"], prefix="Region")

    # --- Feature columns ---
    LEAKY_COLS = ["Debt", "Income", "Annual_Income", "DTI"]
    feature_cols = [
        c
        for c in df_panel_encoded.columns
        if c not in LEAKY_COLS + ["Label", "Province", "Year", "Year_prev", "gap"]
    ]

    df_model = (
        df_panel_encoded.replace([np.inf, -np.inf], np.nan)
        .dropna(subset=feature_cols)
        .copy()
    )

    # แปลง feature columns ทั้งหมดเป็น float (บาง column เป็น object จาก Excel)
    for col in feature_cols:
        df_model[col] = pd.to_numeric(df_model[col], errors="coerce")

    return df_panel, df_panel_encoded, df_model, feature_cols


# ============================================================
# MODEL TRAINING (cached)
# ============================================================
@st.cache_resource
def train_models(_df_model, _feature_cols):
    """เทรน 3 โมเดล พร้อม evaluation metrics"""
    TEST_YEAR = 2566

    train_df = _df_model[_df_model["Year"] < TEST_YEAR]
    test_df = _df_model[_df_model["Year"] == TEST_YEAR]

    X_train = train_df[_feature_cols]
    y_train = train_df["Label"]
    X_test = test_df[_feature_cols]
    y_test = test_df["Label"]

    # --- Logistic Regression ---
    log_reg = LogisticRegression(
        class_weight="balanced", max_iter=1000, random_state=42
    )
    log_reg.fit(X_train, y_train)

    # --- Random Forest ---
    rf_model = RandomForestClassifier(
        n_estimators=300, max_depth=5, class_weight="balanced", random_state=42
    )
    rf_model.fit(X_train, y_train)

    # --- LightGBM ---
    lgb_model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        is_unbalance=True,
        random_state=42,
        verbose=-1,
    )
    lgb_model.fit(X_train, y_train)

    models = {
        "Logistic Regression": log_reg,
        "Random Forest": rf_model,
        "LightGBM": lgb_model,
    }

    # --- Evaluation ---
    results = {}
    for name, model in models.items():
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        cr = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        cm = confusion_matrix(y_test, y_pred)

        # PR-AUC
        if y_test.sum() > 0:
            prec_curve, rec_curve, _ = precision_recall_curve(y_test, y_prob)
            pr_auc = auc(rec_curve, prec_curve)
        else:
            prec_curve, rec_curve, pr_auc = [0], [0], 0.0

        results[name] = {
            "y_pred": y_pred,
            "y_prob": y_prob,
            "report": cr,
            "confusion_matrix": cm,
            "pr_auc": pr_auc,
            "precision_curve": prec_curve,
            "recall_curve": rec_curve,
        }

    return models, results, X_train, X_test, y_test, test_df


# ============================================================
# HELPER: Plotly color palette
# ============================================================
COLORS = {
    "risk": "#FF6B6B",
    "stable": "#2ed573",
    "accent": "#ffa502",
    "blue": "#70a1ff",
    "purple": "#a29bfe",
    "bg": "#0E1117",
    "card_bg": "#1a1a2e",
    "grid": "#2a2a4a",
    "text": "#8892b0",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FAFAFA", size=12),
    margin=dict(l=40, r=40, t=50, b=40),
    xaxis=dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
    yaxis=dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
)


def metric_card(label, value, emoji=""):
    """Render a styled KPI metric card."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{emoji} {value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN APP
# ============================================================
def main():
    # --- Header ---
    st.markdown(
        """
        <div class="main-header">
            <h1>📊 DebtML — Policy Dashboard</h1>
            <p>วิเคราะห์ความเสี่ยงหนี้ครัวเรือนระดับจังหวัด สำหรับนักวิเคราะห์นโยบาย</p>
            <p style="font-size: 0.75rem; color: #555;">แหล่งข้อมูล: สำรวจภาวะเศรษฐกิจและสังคมของครัวเรือน (NSO) | 77 จังหวัด × 11 ปี (พ.ศ. 2547–2566)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Load Data ---
    with st.spinner("กำลังโหลดข้อมูลและเทรนโมเดล..."):
        df_panel, df_panel_encoded, df_model, feature_cols = load_and_prepare_data()
        models, results, X_train, X_test, y_test, test_df = train_models(
            df_model, feature_cols
        )

    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🗺️ ภาพรวมทั้งประเทศ",
            "📈 วิเคราะห์รายจังหวัด",
            "🤖 ผลโมเดล ML",
            "🔮 What-if Simulation",
        ]
    )

    # ============================================================
    # TAB 1: OVERVIEW
    # ============================================================
    with tab1:
        latest_year = df_panel["Year"].max()
        df_latest = df_panel[df_panel["Year"] == latest_year].copy()

        n_provinces = df_latest["Province"].nunique()
        n_high_risk = df_latest[df_latest["Label"] == 1]["Province"].nunique()
        avg_dti = df_latest["DTI"].mean()

        # --- KPI Cards ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_card("ปีข้อมูลล่าสุด", f"พ.ศ. {latest_year}", "📅")
        with col2:
            metric_card("จำนวนจังหวัด", f"{n_provinces}", "🏛️")
        with col3:
            metric_card("จังหวัด High-Risk", f"{n_high_risk}", "🔴")
        with col4:
            metric_card("DTI เฉลี่ยทั้งประเทศ", f"{avg_dti:.2f}", "📊")

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # --- Top 10 DTI Bar Chart ---
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.subheader(f"🏆 Top 10 จังหวัด DTI สูงสุด (พ.ศ. {latest_year})")
            top10 = df_latest.nlargest(10, "DTI")[["Province", "DTI", "Label"]].copy()
            top10["Status"] = top10["Label"].map({0: "Stable", 1: "High-Risk"})
            top10 = top10.sort_values("DTI", ascending=True)

            fig_top10 = go.Figure()
            fig_top10.add_trace(
                go.Bar(
                    y=top10["Province"],
                    x=top10["DTI"],
                    orientation="h",
                    marker=dict(
                        color=[
                            COLORS["risk"] if s == "High-Risk" else COLORS["stable"]
                            for s in top10["Status"]
                        ],
                        line=dict(width=0),
                    ),
                    text=[f"{d:.2f}" for d in top10["DTI"]],
                    textposition="outside",
                    textfont=dict(size=12, color="#FAFAFA"),
                    hovertemplate="<b>%{y}</b><br>DTI: %{x:.3f}<extra></extra>",
                )
            )
            fig_top10.add_vline(
                x=1.0,
                line_dash="dash",
                line_color=COLORS["risk"],
                annotation_text="Threshold (DTI=1.0)",
                annotation_font_color=COLORS["risk"],
            )
            fig_top10.update_layout(
                **PLOTLY_LAYOUT,
                height=420,
                showlegend=False,
                xaxis_title="Debt-to-Income Ratio",
                yaxis_title="",
            )
            st.plotly_chart(fig_top10, use_container_width=True)

        with col_right:
            st.subheader("📊 สัดส่วน High-Risk แบ่งตามภาค")
            df_region_risk = (
                df_latest.groupby("Region")
                .agg(
                    total=("Province", "nunique"),
                    high_risk=("Label", "sum"),
                    avg_dti=("DTI", "mean"),
                )
                .reset_index()
            )
            df_region_risk["pct_risk"] = (
                df_region_risk["high_risk"] / df_region_risk["total"] * 100
            )

            fig_region = go.Figure()
            fig_region.add_trace(
                go.Bar(
                    x=df_region_risk["Region"],
                    y=df_region_risk["avg_dti"],
                    name="DTI เฉลี่ย",
                    marker_color=COLORS["blue"],
                    text=[f"{d:.2f}" for d in df_region_risk["avg_dti"]],
                    textposition="outside",
                    textfont=dict(size=11),
                )
            )
            fig_region.add_hline(
                y=1.0,
                line_dash="dash",
                line_color=COLORS["risk"],
                annotation_text="Threshold",
                annotation_font_color=COLORS["risk"],
            )
            fig_region.update_layout(
                **PLOTLY_LAYOUT,
                height=420,
                showlegend=False,
                xaxis_title="",
                yaxis_title="DTI เฉลี่ย",
                xaxis_tickangle=-25,
            )
            st.plotly_chart(fig_region, use_container_width=True)

        # --- DTI Heatmap ---
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.subheader("🌡️ DTI Heatmap — ทุกจังหวัด × ทุกปี")

        heatmap_data = df_panel.pivot_table(
            index="Province", columns="Year", values="DTI"
        )
        heatmap_data = heatmap_data.sort_index()

        fig_heatmap = go.Figure(
            data=go.Heatmap(
                z=heatmap_data.values,
                x=[str(y) for y in heatmap_data.columns],
                y=heatmap_data.index,
                colorscale=[
                    [0, "#2ed573"],
                    [0.5, "#ffa502"],
                    [1.0, "#ff4757"],
                ],
                zmin=0,
                zmax=2.0,
                colorbar=dict(
                    title=dict(text="DTI", side="right"),
                    tickvals=[0, 0.5, 1.0, 1.5, 2.0],
                ),
                hovertemplate="<b>%{y}</b><br>ปี %{x}<br>DTI: %{z:.3f}<extra></extra>",
            )
        )
        fig_heatmap.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#FAFAFA", size=12),
            margin=dict(l=40, r=40, t=50, b=40),
            height=max(500, len(heatmap_data) * 12),
            xaxis_title="ปี (พ.ศ.)",
            xaxis=dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
            yaxis_title="",
            yaxis=dict(
                gridcolor=COLORS["grid"],
                zerolinecolor=COLORS["grid"],
                dtick=1,
                tickfont=dict(size=9),
            ),
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

    # ============================================================
    # TAB 2: PROVINCE DEEP-DIVE
    # ============================================================
    with tab2:
        provinces_list = sorted(df_panel["Province"].unique())
        selected_province = st.selectbox(
            "🔍 เลือกจังหวัด",
            provinces_list,
            index=provinces_list.index("กรุงเทพมหานคร")
            if "กรุงเทพมหานคร" in provinces_list
            else 0,
        )

        df_prov = df_panel[df_panel["Province"] == selected_province].sort_values(
            "Year"
        )
        region = df_prov["Region"].iloc[0] if len(df_prov) > 0 else "N/A"

        # Province header
        latest_dti = df_prov[df_prov["Year"] == latest_year]["DTI"].values
        latest_label = df_prov[df_prov["Year"] == latest_year]["Label"].values
        status_badge = ""
        if len(latest_label) > 0:
            if latest_label[0] == 1:
                status_badge = '<span class="badge-risk">🔴 High-Risk</span>'
            else:
                status_badge = '<span class="badge-stable">🟢 Stable</span>'

        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                <h2 style="margin: 0;">{selected_province}</h2>
                {status_badge}
                <span style="color: {COLORS['text']}; font-size: 0.9rem;">ภาค: {region}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # KPI row for province
        if len(latest_dti) > 0:
            col1, col2, col3 = st.columns(3)
            with col1:
                metric_card("DTI ปีล่าสุด", f"{latest_dti[0]:.3f}", "📊")
            with col2:
                latest_debt = df_prov[df_prov["Year"] == latest_year]["Debt"].values
                metric_card(
                    "หนี้สินเฉลี่ย (บาท)",
                    f"{latest_debt[0]:,.0f}" if len(latest_debt) > 0 else "N/A",
                    "💰",
                )
            with col3:
                latest_income = df_prov[df_prov["Year"] == latest_year]["Income"].values
                metric_card(
                    "รายได้เฉลี่ย/เดือน (บาท)",
                    f"{latest_income[0]:,.0f}" if len(latest_income) > 0 else "N/A",
                    "💵",
                )

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # --- Dual-axis chart: Debt vs Income ---
        col_chart1, col_chart2 = st.columns([1, 1])

        with col_chart1:
            st.subheader("💰 หนี้สิน vs รายได้ (ย้อนหลัง)")

            fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
            fig_dual.add_trace(
                go.Scatter(
                    x=df_prov["Year"].astype(str),
                    y=df_prov["Debt"],
                    name="หนี้สิน (บาท)",
                    line=dict(color=COLORS["risk"], width=3),
                    mode="lines+markers",
                    marker=dict(size=8),
                    hovertemplate="ปี %{x}<br>หนี้: %{y:,.0f} บาท<extra></extra>",
                ),
                secondary_y=False,
            )
            fig_dual.add_trace(
                go.Scatter(
                    x=df_prov["Year"].astype(str),
                    y=df_prov["Income"],
                    name="รายได้/เดือน (บาท)",
                    line=dict(color=COLORS["stable"], width=3),
                    mode="lines+markers",
                    marker=dict(size=8),
                    hovertemplate="ปี %{x}<br>รายได้: %{y:,.0f} บาท/เดือน<extra></extra>",
                ),
                secondary_y=True,
            )
            fig_dual.update_layout(
                **PLOTLY_LAYOUT,
                height=400,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
                ),
            )
            fig_dual.update_yaxes(
                title_text="หนี้สิน (บาท)",
                secondary_y=False,
                gridcolor=COLORS["grid"],
            )
            fig_dual.update_yaxes(
                title_text="รายได้/เดือน (บาท)",
                secondary_y=True,
                gridcolor=COLORS["grid"],
            )
            st.plotly_chart(fig_dual, use_container_width=True)

        with col_chart2:
            st.subheader("📈 DTI Trend")

            fig_dti = go.Figure()
            fig_dti.add_trace(
                go.Scatter(
                    x=df_prov["Year"].astype(str),
                    y=df_prov["DTI"],
                    name="DTI",
                    line=dict(color=COLORS["accent"], width=3),
                    mode="lines+markers",
                    marker=dict(size=8),
                    fill="tozeroy",
                    fillcolor="rgba(255, 165, 2, 0.1)",
                    hovertemplate="ปี %{x}<br>DTI: %{y:.3f}<extra></extra>",
                )
            )
            fig_dti.add_hline(
                y=1.0,
                line_dash="dash",
                line_color=COLORS["risk"],
                line_width=2,
                annotation_text="⚠️ Threshold (DTI = 1.0)",
                annotation_font_color=COLORS["risk"],
                annotation_font_size=12,
            )
            fig_dti.update_layout(
                **PLOTLY_LAYOUT,
                height=400,
                showlegend=False,
                yaxis_title="Debt-to-Income Ratio",
            )
            st.plotly_chart(fig_dti, use_container_width=True)

        # --- Data table ---
        st.subheader("📋 ข้อมูลดิบ")
        display_cols = ["Year", "Income", "Debt", "Annual_Income", "DTI", "Label"]
        df_display = df_prov[display_cols].copy()
        df_display["Year"] = df_display["Year"].astype(str)
        df_display["Label"] = df_display["Label"].map({0: "🟢 Stable", 1: "🔴 High-Risk"})
        df_display.columns = [
            "ปี (พ.ศ.)", "รายได้/เดือน", "หนี้สิน",
            "รายได้ทั้งปี", "DTI", "สถานะ",
        ]
        st.dataframe(
            df_display.style.format(
                {
                    "รายได้/เดือน": "{:,.2f}",
                    "หนี้สิน": "{:,.2f}",
                    "รายได้ทั้งปี": "{:,.2f}",
                    "DTI": "{:.4f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    # ============================================================
    # TAB 3: MODEL RESULTS
    # ============================================================
    with tab3:
        st.subheader("🤖 เปรียบเทียบผลโมเดล 3 ตัว (Test Year: 2566)")

        # --- Summary Metrics ---
        model_names = list(results.keys())
        cols_metric = st.columns(len(model_names))
        for i, name in enumerate(model_names):
            r = results[name]
            with cols_metric[i]:
                f1_1 = r["report"].get("1", {}).get("f1-score", 0)
                recall_1 = r["report"].get("1", {}).get("recall", 0)
                precision_1 = r["report"].get("1", {}).get("precision", 0)
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">{name}</div>
                        <div class="metric-value" style="font-size:1.6rem;">PR-AUC {r['pr_auc']:.3f}</div>
                        <div style="color: {COLORS['text']}; font-size: 0.8rem; margin-top:0.3rem;">
                            F1(High-Risk): {f1_1:.3f} &nbsp;|&nbsp;
                            Recall: {recall_1:.3f} &nbsp;|&nbsp;
                            Precision: {precision_1:.3f}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # --- Confusion Matrices ---
        st.subheader("📊 Confusion Matrix")
        cm_cols = st.columns(len(model_names))
        for i, name in enumerate(model_names):
            cm = results[name]["confusion_matrix"]
            with cm_cols[i]:
                fig_cm = go.Figure(
                    data=go.Heatmap(
                        z=cm,
                        x=["Pred: Stable", "Pred: High-Risk"],
                        y=["Actual: Stable", "Actual: High-Risk"],
                        colorscale=[[0, "#16213e"], [1, COLORS["risk"]]],
                        text=cm,
                        texttemplate="%{text}",
                        textfont=dict(size=18, color="white"),
                        showscale=False,
                        hovertemplate="Actual: %{y}<br>Predicted: %{x}<br>Count: %{z}<extra></extra>",
                    )
                )
                fig_cm.update_layout(
                    **PLOTLY_LAYOUT,
                    title=dict(text=name, font=dict(size=14)),
                    height=300,
                )
                fig_cm.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_cm, use_container_width=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # --- Feature Importance ---
        st.subheader("🏆 Feature Importance")
        fi_cols = st.columns(2)

        # Random Forest
        with fi_cols[0]:
            rf = models["Random Forest"]
            fi_rf = pd.DataFrame(
                {"feature": feature_cols, "importance": rf.feature_importances_}
            ).sort_values("importance", ascending=True)

            fig_fi_rf = go.Figure(
                go.Bar(
                    y=fi_rf["feature"],
                    x=fi_rf["importance"],
                    orientation="h",
                    marker_color=COLORS["blue"],
                    text=[f"{v:.3f}" for v in fi_rf["importance"]],
                    textposition="outside",
                    textfont=dict(size=10),
                )
            )
            fig_fi_rf.update_layout(
                **PLOTLY_LAYOUT,
                title=dict(text="Random Forest", font=dict(size=14)),
                height=400,
                xaxis_title="Importance",
            )
            st.plotly_chart(fig_fi_rf, use_container_width=True)

        # LightGBM
        with fi_cols[1]:
            lgb_m = models["LightGBM"]
            fi_lgb = pd.DataFrame(
                {"feature": feature_cols, "importance": lgb_m.feature_importances_}
            ).sort_values("importance", ascending=True)

            fig_fi_lgb = go.Figure(
                go.Bar(
                    y=fi_lgb["feature"],
                    x=fi_lgb["importance"],
                    orientation="h",
                    marker_color=COLORS["purple"],
                    text=[f"{v:.0f}" for v in fi_lgb["importance"]],
                    textposition="outside",
                    textfont=dict(size=10),
                )
            )
            fig_fi_lgb.update_layout(
                **PLOTLY_LAYOUT,
                title=dict(text="LightGBM", font=dict(size=14)),
                height=400,
                xaxis_title="Importance (split count)",
            )
            st.plotly_chart(fig_fi_lgb, use_container_width=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # --- Prediction Table for 2566 ---
        st.subheader(f"📋 ตาราง Prediction ปี {latest_year} — ทุกจังหวัด")

        pred_rows = []
        for idx, row in test_df.iterrows():
            prov = row["Province"]
            actual = int(row["Label"])
            x_row = row[feature_cols].values.reshape(1, -1)
            row_data = {"จังหวัด": prov, "Actual": actual}
            for name, model in models.items():
                prob = model.predict_proba(x_row)[0][1]
                pred = model.predict(x_row)[0]
                short = name.split()[0]  # Logistic, Random, LightGBM
                row_data[f"{short}_Prob"] = prob
                row_data[f"{short}_Pred"] = int(pred)
            pred_rows.append(row_data)

        df_pred = pd.DataFrame(pred_rows)
        df_pred["Actual_Status"] = df_pred["Actual"].map(
            {0: "🟢 Stable", 1: "🔴 High-Risk"}
        )

        # Reorder columns
        display_pred_cols = ["จังหวัด", "Actual_Status"]
        for name in models.keys():
            short = name.split()[0]
            display_pred_cols.extend([f"{short}_Prob", f"{short}_Pred"])

        st.dataframe(
            df_pred[display_pred_cols].style.format(
                {
                    col: "{:.3f}"
                    for col in df_pred.columns
                    if col.endswith("_Prob")
                }
            ),
            use_container_width=True,
            hide_index=True,
            height=500,
        )

    # ============================================================
    # TAB 4: WHAT-IF SIMULATION
    # ============================================================
    with tab4:
        st.subheader("🔮 Policy Simulation — What-if Analysis")
        st.markdown(
            f"""
            <p style="color: {COLORS['text']};">
            ปรับค่าตัวแปรด้านล่างเพื่อจำลองสถานการณ์ แล้วดูว่าโมเดลจะทำนายสถานะความเสี่ยงอย่างไร<br>
            <b>ใช้สำหรับ:</b> "ถ้ารายได้จังหวัดนี้โตขึ้น X% จะหลุดจากโซน High-Risk ไหม?"
            </p>
            """,
            unsafe_allow_html=True,
        )

        # Pre-fill with a province's latest data
        provinces_list_sim = sorted(df_panel["Province"].unique())
        selected_sim = st.selectbox(
            "📍 เลือกจังหวัดเป็นจุดเริ่มต้น (โหลดค่าตั้งต้น)",
            provinces_list_sim,
            key="sim_province",
        )

        df_sim_prov = df_panel[
            (df_panel["Province"] == selected_sim) & (df_panel["Year"] == latest_year)
        ]

        # Default values
        default_debt = float(
            df_sim_prov["Debt"].iloc[0] if len(df_sim_prov) > 0 else 150000
        )
        default_income = float(
            df_sim_prov["Income"].iloc[0] if len(df_sim_prov) > 0 else 20000
        )
        default_dti = float(
            df_sim_prov["DTI"].iloc[0] if len(df_sim_prov) > 0 else 0.5
        )

        # Get region for encoding
        sim_region = (
            df_panel[df_panel["Province"] == selected_sim]["Region"].iloc[0]
            if len(df_panel[df_panel["Province"] == selected_sim]) > 0
            else "ภาคกลาง"
        )

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        col_input1, col_input2 = st.columns(2)

        with col_input1:
            st.markdown("##### 💰 ข้อมูลปีก่อนหน้า (Lag)")
            sim_debt_lag = st.number_input(
                "หนี้สินเฉลี่ยปีก่อน (Debt_lag1)",
                min_value=0.0,
                max_value=1_000_000.0,
                value=default_debt,
                step=5000.0,
                format="%.0f",
            )
            sim_income_lag = st.number_input(
                "รายได้เฉลี่ย/เดือน ปีก่อน (Income_lag1)",
                min_value=0.0,
                max_value=200_000.0,
                value=default_income,
                step=1000.0,
                format="%.0f",
            )
            sim_dti_lag = st.slider(
                "DTI ปีก่อน (DTI_lag1)",
                min_value=0.0,
                max_value=3.0,
                value=min(default_dti, 3.0),
                step=0.01,
            )

        with col_input2:
            st.markdown("##### 📈 อัตราการเปลี่ยนแปลง")
            sim_debt_growth = st.slider(
                "อัตราเติบโตหนี้ต่อปี (Debt_growth_ann)",
                min_value=-0.50,
                max_value=1.00,
                value=0.05,
                step=0.01,
                format="%.2f",
            )
            sim_income_growth = st.slider(
                "อัตราเติบโตรายได้ต่อปี (Income_growth_ann)",
                min_value=-0.50,
                max_value=1.00,
                value=0.03,
                step=0.01,
                format="%.2f",
            )

        # Build feature vector
        region_cols = [c for c in feature_cols if c.startswith("Region_")]
        sim_features = {col: 0 for col in feature_cols}
        sim_features["Debt_lag1"] = sim_debt_lag
        sim_features["Income_lag1"] = sim_income_lag
        sim_features["DTI_lag1"] = sim_dti_lag
        sim_features["Debt_growth_ann"] = sim_debt_growth
        sim_features["Income_growth_ann"] = sim_income_growth

        # Set region encoding
        for rc in region_cols:
            region_name = rc.replace("Region_", "")
            sim_features[rc] = 1 if region_name == sim_region else 0

        sim_df = pd.DataFrame([sim_features])[feature_cols]

        # --- Prediction ---
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        st.markdown('<div class="whatif-result">', unsafe_allow_html=True)
        st.markdown(f"### 📍 ผลการทำนาย — {selected_sim} (ภาค: {sim_region})")

        result_cols = st.columns(len(models))
        for i, (name, model) in enumerate(models.items()):
            prob = model.predict_proba(sim_df)[0][1]
            pred = model.predict(sim_df)[0]
            status = "High-Risk" if pred == 1 else "Stable"
            badge_class = "badge-risk" if pred == 1 else "badge-stable"
            emoji = "🔴" if pred == 1 else "🟢"

            with result_cols[i]:
                st.markdown(
                    f"""
                    <div class="metric-card" style="border-color: {'#ff4757' if pred == 1 else '#2ed573'};">
                        <div class="metric-label">{name}</div>
                        <div class="metric-value" style="font-size:1.8rem;">{emoji} {prob:.1%}</div>
                        <div style="margin-top: 0.5rem;">
                            <span class="{badge_class}">{status}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Insight
        st.markdown("")
        avg_prob = np.mean(
            [m.predict_proba(sim_df)[0][1] for m in models.values()]
        )
        if avg_prob > 0.5:
            st.warning(
                f"⚠️ ค่าเฉลี่ย Probability จากทุกโมเดล = **{avg_prob:.1%}** — "
                f"สถานการณ์นี้มีแนวโน้มเข้าข่าย **High-Risk** "
                f"ลองปรับอัตราเติบโตรายได้ให้สูงขึ้นเพื่อดูว่าจะช่วยลดความเสี่ยงได้ไหม"
            )
        else:
            st.success(
                f"✅ ค่าเฉลี่ย Probability จากทุกโมเดล = **{avg_prob:.1%}** — "
                f"สถานการณ์นี้อยู่ในโซน **Stable**"
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # --- Footer ---
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="text-align: center; color: {COLORS['text']}; font-size: 0.75rem; padding: 1rem 0;">
            DebtML Policy Dashboard v1.0 &nbsp;|&nbsp;
            Models: Logistic Regression, Random Forest, LightGBM &nbsp;|&nbsp;
            Data: NSO Household Socio-Economic Survey (พ.ศ. 2547–2566)
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
