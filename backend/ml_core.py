import os
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    auc,
)
import lightgbm as lgb
from functools import lru_cache

# ============================================================
# DATA LOADING & FEATURE ENGINEERING
# ============================================================
@lru_cache(maxsize=1)
def load_and_prepare_data():
    """
    อ่าน Excel → Merge → Wide-to-Long → DTI + Label + Lag Features + Growth
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # go up one level since it's in backend/

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
    df_panel["Income"] = pd.to_numeric(df_panel["Income"], errors="coerce").fillna(0)
    df_panel["Debt"] = pd.to_numeric(df_panel["Debt"], errors="coerce").fillna(0)
    df_panel = df_panel.sort_values(["Province", "Year"]).reset_index(drop=True)

    # --- DTI & Label ---
    df_panel["Annual_Income"] = df_panel["Income"] * 12
    df_panel["Annual_Income"] = df_panel["Annual_Income"].replace(0, np.nan)
    df_panel["DTI"] = df_panel["Debt"] / df_panel["Annual_Income"]
    DTI_THRESHOLD = 1.0
    df_panel["Label"] = (df_panel["DTI"] > DTI_THRESHOLD).astype(int)

    # --- Lag features & Annualized Growth ---
    def annualized_growth(curr, prev, gap):
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            g = (curr / prev) ** (1 / gap) - 1
        return g

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

    for col in feature_cols:
        df_model[col] = pd.to_numeric(df_model[col], errors="coerce")

    return df_panel, df_panel_encoded, df_model, feature_cols


# ============================================================
# MODEL TRAINING
# ============================================================
@lru_cache(maxsize=1)
def train_models():
    """เทรน 3 โมเดล พร้อม evaluation metrics"""
    df_panel, df_panel_encoded, df_model, feature_cols = load_and_prepare_data()
    
    TEST_YEAR = 2566
    train_df = df_model[df_model["Year"] < TEST_YEAR]
    test_df = df_model[df_model["Year"] == TEST_YEAR]

    X_train = train_df[feature_cols]
    y_train = train_df["Label"]
    X_test = test_df[feature_cols]
    y_test = test_df["Label"]

    # --- Logistic Regression ---
    log_reg = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    log_reg.fit(X_train, y_train)

    # --- Random Forest ---
    rf_model = RandomForestClassifier(n_estimators=300, max_depth=5, class_weight="balanced", random_state=42)
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

        if y_test.sum() > 0:
            prec_curve, rec_curve, _ = precision_recall_curve(y_test, y_prob)
            pr_auc = auc(rec_curve, prec_curve)
        else:
            prec_curve, rec_curve, pr_auc = [0], [0], 0.0

        results[name] = {
            "y_pred": y_pred.tolist(),
            "y_prob": y_prob.tolist(),
            "report": cr,
            "confusion_matrix": cm.tolist(),
            "pr_auc": float(pr_auc),
            "precision_curve": prec_curve.tolist(),
            "recall_curve": rec_curve.tolist(),
        }

    return {
        "models": models,
        "results": results,
        "feature_cols": feature_cols,
        "df_panel": df_panel,
        "df_model": df_model,
        "test_df": test_df
    }
