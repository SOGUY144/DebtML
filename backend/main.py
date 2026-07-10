from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np

# Import our ML logic
from ml_core import train_models

app = FastAPI(title="DebtML API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load everything up on startup (caching ensures it only runs once)
ML_CONTEXT = train_models()

@app.get("/api/overview")
def get_overview():
    df_panel = ML_CONTEXT["df_panel"]
    latest_year = int(df_panel["Year"].max())
    df_latest = df_panel[df_panel["Year"] == latest_year].copy()

    n_provinces = int(df_latest["Province"].nunique())
    n_high_risk = int(df_latest[df_latest["Label"] == 1]["Province"].nunique())
    avg_dti = float(df_latest["DTI"].mean())
    
    top10_df = df_latest.nlargest(10, "DTI")[["Province", "DTI", "Label"]].copy()
    top10_df["Status"] = top10_df["Label"].map({0: "Stable", 1: "High-Risk"})
    top10 = top10_df.to_dict(orient="records")
    
    return {
        "latest_year": latest_year,
        "n_provinces": n_provinces,
        "n_high_risk": n_high_risk,
        "avg_dti": avg_dti,
        "top10_dti": top10
    }

@app.get("/api/provinces")
def get_provinces():
    df_panel = ML_CONTEXT["df_panel"]
    provinces = sorted(df_panel["Province"].unique().tolist())
    return {"provinces": provinces}

@app.get("/api/province/{province_name}")
def get_province_data(province_name: str):
    df_panel = ML_CONTEXT["df_panel"]
    prov_df = df_panel[df_panel["Province"] == province_name].copy()
    if prov_df.empty:
        raise HTTPException(status_code=404, detail="Province not found")
        
    latest_data = prov_df.iloc[-1]
    
    # Time series for charts
    time_series = prov_df[["Year", "Debt", "Annual_Income", "DTI", "Label"]].to_dict(orient="records")
    
    return {
        "province": province_name,
        "latest_year": int(latest_data["Year"]),
        "latest_dti": float(latest_data["DTI"]),
        "latest_debt": float(latest_data["Debt"]),
        "latest_income": float(latest_data["Annual_Income"]),
        "status": "High-Risk" if latest_data["Label"] == 1 else "Stable",
        "time_series": time_series
    }

@app.get("/api/models/evaluation")
def get_model_evaluations():
    results = ML_CONTEXT["results"]
    evals = []
    
    for name, res in results.items():
        f1 = res["report"].get("1", {}).get("f1-score", 0)
        recall = res["report"].get("1", {}).get("recall", 0)
        precision = res["report"].get("1", {}).get("precision", 0)
        
        evals.append({
            "model_name": name,
            "pr_auc": res["pr_auc"],
            "f1_high_risk": f1,
            "recall_high_risk": recall,
            "precision_high_risk": precision,
            "confusion_matrix": res["confusion_matrix"],
            "precision_curve": res["precision_curve"],
            "recall_curve": res["recall_curve"]
        })
        
    # Feature importances for all 3 models, ordered: Logistic Regression > Random Forest > LightGBM
    feature_cols = ML_CONTEXT["feature_cols"]

    def build_importance_list(raw_importances):
        total = float(np.sum(raw_importances))
        pairs = list(zip(feature_cols, raw_importances))
        pairs.sort(key=lambda x: x[1], reverse=True)
        return [
            {"feature": f, "importance": float(v) / total if total > 0 else 0.0}
            for f, v in pairs[:15]
        ]

    log_reg_model = ML_CONTEXT["models"]["Logistic Regression"]
    rf_model = ML_CONTEXT["models"]["Random Forest"]
    lgb_model = ML_CONTEXT["models"]["LightGBM"]

    # Logistic Regression: coefficients aren't inherently "importances", so we
    # use the absolute value of the (scaled-feature) coefficients as a proxy.
    lr_top_features = build_importance_list(np.abs(log_reg_model.coef_[0]))
    rf_top_features = build_importance_list(rf_model.feature_importances_)
    lgb_top_features = build_importance_list(lgb_model.feature_importances_)

    feature_importances = [
        {"model_name": "Logistic Regression", "top_features": lr_top_features},
        {"model_name": "Random Forest", "top_features": rf_top_features},
        {"model_name": "LightGBM", "top_features": lgb_top_features},
    ]

    return {
        "evaluations": evals,
        # Kept for backwards compatibility with any older frontend build
        "top_features": rf_top_features,
        "feature_importances": feature_importances
    }

class SimulateRequest(BaseModel):
    province: str
    debt_growth: float
    income_growth: float

@app.post("/api/models/simulate")
def simulate(req: SimulateRequest):
    df_model = ML_CONTEXT["df_model"]
    feature_cols = ML_CONTEXT["feature_cols"]
    models = ML_CONTEXT["models"]
    
    prov_df = df_model[df_model["Province"] == req.province]
    if prov_df.empty:
        raise HTTPException(status_code=404, detail="Province not found")
        
    base_data = prov_df.iloc[-1].copy()
    
    # Convert to a single-row dataframe for the model
    sim_df = pd.DataFrame([base_data])
    
    # Update simulated values
    sim_df["Debt_growth_ann"] = req.debt_growth
    sim_df["Income_growth_ann"] = req.income_growth
    
    # Calculate new simulated DTI (approximate based on growth)
    # Debt(t+1) = Debt(t) * (1 + debt_growth)
    sim_debt = float(sim_df["Debt"].iloc[0]) * (1 + req.debt_growth)
    sim_income = float(sim_df["Annual_Income"].iloc[0]) * (1 + req.income_growth)
    sim_dti = sim_debt / sim_income if sim_income > 0 else 0
    sim_df["DTI"] = sim_dti
    sim_df["DTI_lag"] = base_data["DTI"]
    
    # Keep only feature cols for prediction
    sim_features = sim_df[feature_cols].copy()
    for col in feature_cols:
        sim_features[col] = pd.to_numeric(sim_features[col], errors="coerce").fillna(0)
        
    scaler = ML_CONTEXT["scaler"]
    results = {}
    for name, model in models.items():
        if name == "Logistic Regression":
            sim_features_eval = pd.DataFrame(scaler.transform(sim_features), columns=feature_cols)
        else:
            sim_features_eval = sim_features
            
        pred = int(model.predict(sim_features_eval)[0])
        prob = float(model.predict_proba(sim_features_eval)[0][1])
        results[name] = {
            "prediction": pred,
            "status": "High-Risk" if pred == 1 else "Stable",
            "probability_high_risk": prob
        }
        
    return {
        "province": req.province,
        "simulated_dti": float(sim_dti),
        "results": results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)