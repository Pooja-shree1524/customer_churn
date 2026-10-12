# %% [markdown]
# # Round 2: Feature Engineering, Selection, ML Model and Intelligence Layer

# %%
import sys, matplotlib
if "ipykernel" not in sys.modules:
    matplotlib.use("Agg")   # plain-script runs: save charts without opening Tk windows (fixes the tkinter error)
import pandas as pd, numpy as np, matplotlib.pyplot as plt, seaborn as sns, json, warnings
from sklearn.model_selection import train_test_split, cross_val_predict, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, confusion_matrix, ConfusionMatrixDisplay)
warnings.filterwarnings("ignore"); sns.set_theme(style="whitegrid")
df = pd.read_csv("data/cleaned_churn_data.csv")

# %% [markdown]
# ## 1. Feature engineering

# %%
df["tenure_group"] = pd.cut(df.tenure_months, [0, 6, 12, 24, 100], labels=["0-6", "7-12", "13-24", "24+"]).astype(str)
df["late_payment_ratio"] = df.late_payments / 6
df["tickets_per_month"] = df.tickets / df.tenure_months.clip(upper=6)
df["total_usage"] = df.avg_voice / 100 + df.avg_data + df.avg_sms / 50
df["voice_drop"] = (1 - df.voice_minutes_last3 / df.voice_minutes_first3.replace(0, np.nan)).fillna(0).clip(-1, 1)
df["data_drop"] = (1 - df.data_gb_last3 / df.data_gb_first3.replace(0, np.nan)).fillna(0).clip(-1, 1)
df["usage_drop"] = (df.voice_drop + df.data_drop) / 2
df["bill_per_usage"] = df.avg_bill / (df.total_usage + 1)
df["high_complaint_flag"] = (df.tickets >= 3).astype(int)
df["service_issues"] = df.network_issues + df.outages
df["ticket_group"] = pd.cut(df.tickets, [-1, 0, 2, 100], labels=["0", "1-2", "3+"]).astype(str)
df["payment_behaviour"] = pd.cut(df.late_payments, [-1, 0, 1, 100], labels=["On-time", "1 late", "2+ late"]).astype(str)

# %% [markdown]
# ## 2. Encoding

# %%
y = df.churn_flag
cat_cols = ["plan", "region", "gender"]
num_cols = ["tenure_months", "age", "avg_voice", "avg_data", "avg_sms", "avg_bill", "late_payments",
            "avg_late_days", "tickets", "avg_resolution_hrs", "network_issues", "outages", "plan_changes",
            "late_payment_ratio", "tickets_per_month", "total_usage", "usage_drop", "bill_per_usage",
            "high_complaint_flag", "service_issues"]
X_all = pd.concat([df[num_cols], pd.get_dummies(df[cat_cols], drop_first=True, dtype=int)], axis=1)
print("Features before selection:", X_all.shape[1])

# %% [markdown]
# ## 3. Feature selection (correlation filter + Random Forest importance)

# %%
corr = X_all.corr().abs(); upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
drop_corr = [c for c in upper.columns if any(upper[c] > 0.90)]
print("Dropped (corr > 0.90 with another feature):", drop_corr)
X_f = X_all.drop(columns=drop_corr)
rf_sel = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced", n_jobs=-1).fit(X_f, y)
imp = pd.Series(rf_sel.feature_importances_, index=X_f.columns).sort_values(ascending=False)
selected = imp[imp >= 0.01].index.tolist()
print(f"Selected {len(selected)} features:\n", imp.loc[selected].round(3))
imp.head(15).sort_values().plot(kind="barh", figsize=(7, 5), color="#2b6cb0"); plt.title("Feature importance (top 15)")
plt.tight_layout(); plt.savefig("outputs/feature_importance.png", dpi=130); plt.show()

# optional PCA (information only)
from sklearn.decomposition import PCA
Xs = StandardScaler().fit_transform(X_f[selected]); pca = PCA().fit(Xs)
n95 = int(np.argmax(np.cumsum(pca.explained_variance_ratio_) >= 0.95) + 1)
print(f"PCA: {n95} components explain 95% variance out of {len(selected)}")

# %% [markdown]
# ## 4. Model training and evaluation

# %%
X = X_f[selected]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
rf = RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=5,
                            class_weight="balanced", random_state=42, n_jobs=-1).fit(X_tr, y_tr)
lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")).fit(X_tr, y_tr)

def metrics(m):
    p = m.predict(X_te); pr = m.predict_proba(X_te)[:, 1]
    return dict(Accuracy=accuracy_score(y_te, p), Precision=precision_score(y_te, p),
                Recall=recall_score(y_te, p), F1=f1_score(y_te, p), ROC_AUC=roc_auc_score(y_te, pr))
res = pd.DataFrame({"Random Forest": metrics(rf), "Logistic Regression (baseline)": metrics(lr)}).round(3)
print(res)
ConfusionMatrixDisplay(confusion_matrix(y_te, rf.predict(X_te)), display_labels=["Retained", "Churned"]).plot(cmap="Blues")
plt.title("Random Forest - confusion matrix"); plt.savefig("outputs/confusion_matrix.png", dpi=130); plt.show()
cv = cross_val_predict(rf, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=42), method="predict_proba")[:, 1]

# %% [markdown]
# ## 5. Intelligence layer: churn-risk score, segments and retention actions

# %%
df["risk_score"] = cv.round(3)          # out-of-fold probability (no leakage)
df["risk_level"] = pd.cut(df.risk_score, [-0.01, 0.4, 0.7, 1.0], labels=["Low", "Medium", "High"]).astype(str)

def segment(r):
    if r.usage_drop >= 0.25: return "Disengaged Low-Usage"
    if r.late_payments >= 2: return "Payment-Risk"
    if r.tickets >= 3 or r.outages >= 2: return "Service-Unhappy"
    if r.tenure_months <= 12: return "New Customer"
    return "Loyal Stable"
df["segment"] = df.apply(segment, axis=1)

ACTION = {"Disengaged Low-Usage": "Personalised data/voice bonus pack + re-engagement call",
          "Payment-Risk": "Flexible due date, auto-pay incentive, SMS reminder",
          "Service-Unhappy": "Priority complaint resolution + network-credit / goodwill discount",
          "New Customer": "Onboarding journey + first-year loyalty offer",
          "Loyal Stable": "Reward / upsell, no urgent action"}
df["retention_action"] = df.segment.map(ACTION)
print(df.groupby("segment").agg(customers=("customer_id", "count"), churn_rate=("churn_flag", "mean"),
                                avg_risk=("risk_score", "mean")).round(3))
print(df.risk_level.value_counts())
df.to_csv("data/churn_featured_data.csv", index=False)                       # used by Excel
df[["customer_id", "plan", "region", "risk_score", "risk_level", "segment", "retention_action"]] \
  .sort_values("risk_score", ascending=False).to_csv("outputs/churn_risk_scores.csv", index=False)

out = {"selected_features": selected, "n_features_before_selection": int(X_all.shape[1]),
       "n_selected": len(selected), "pca_components_95pct": n95, "dropped_corr": drop_corr,
       "metrics": res.to_dict(), "high_risk_customers": int((df.risk_level == "High").sum()),
       "train_size": len(X_tr), "test_size": len(X_te)}
json.dump(out, open("outputs/model_results.json", "w"), indent=2)
print(json.dumps(out["metrics"], indent=2))
