import joblib
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_curve, auc
import DTI_ML
import numpy as np

# Retrieve variables from the loaded module
X_test = DTI_ML.X_test
X_test_scaled = DTI_ML.X_test_scaled
y_test = DTI_ML.y_test
scaler = DTI_ML.scaler
trained_models = DTI_ML.trained_models

# Save the scaler
joblib.dump(scaler, 'scaler.pkl')
print("Saved scaler.pkl successfully.")

results = {}

for name, model in trained_models.items():
    print(f"\n{'='*50}\nModel: {name}\n{'='*50}")
    
    # Use scaled test set for Logistic Regression, raw test set for tree-based models
    if name == 'Logistic Regression':
        X_eval = X_test_scaled
    else:
        X_eval = X_test
        
    y_pred = model.predict(X_eval)
    
    try:
        y_prob = model.predict_proba(X_eval)[:, 1]
    except AttributeError:
        y_prob = model.decision_function(X_eval)
        
    print("Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    print("\nClassification Report:")
    report = classification_report(y_test, y_pred, zero_division=0)
    print(report)
    
    precision, recall, _ = precision_recall_curve(y_test, y_prob)
    pr_auc = auc(recall, precision)
    print(f"PR AUC Score: {pr_auc:.4f}")
    
    results[name] = {
        "Confusion Matrix": cm.tolist(),
        "PR AUC": pr_auc
    }
