# %% [markdown]
# # Round 1/2: Data Understanding, Cleaning & EDA
# ConnectSphere Telecom - Customer Churn Insight (U23AD491, SBA-2, Use Case 02)

# %%
import sys, matplotlib
if "ipykernel" not in sys.modules:
    matplotlib.use("Agg")   # plain-script runs: save charts without opening Tk windows (fixes the tkinter error)
import pandas as pd, numpy as np, seaborn as sns, matplotlib.pyplot as plt, os, warnings
warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid")
os.makedirs("outputs", exist_ok=True); os.makedirs("data", exist_ok=True)
RAW = "data/raw/"
cust = pd.read_csv(RAW + "customers.csv"); usage = pd.read_csv(RAW + "usage.csv")
bill = pd.read_csv(RAW + "billing.csv");   sup = pd.read_csv(RAW + "support.csv")
svc = pd.read_csv(RAW + "service.csv")

# %% [markdown]
# ## 1. Understand the data: shape, types, missing, duplicates

# %%
files = {"customers": cust, "usage": usage, "billing": bill, "support": sup, "service": svc}
summary = pd.DataFrame({n: {"rows": d.shape[0], "cols": d.shape[1],
                            "missing_cells": int(d.isnull().sum().sum()),
                            "duplicate_rows": int(d.duplicated().sum())} for n, d in files.items()}).T
print(summary)
print("\nDuplicate customer IDs in customers.csv:", cust.customer_id.duplicated().sum())
print("\nRaw plan-name variants:", cust.plan.nunique()); print(cust.plan.value_counts().head(12))
print("\nBilling charges describe:\n", bill.charges.describe())
print("\nMissing per column (usage):\n", usage.isnull().sum())
print("\nCustomers with NO usage rows:", len(set(cust.customer_id) - set(usage.customer_id)))
print("Customers with NO support tickets:", len(set(cust.customer_id) - set(sup.customer_id)))

# %% [markdown]
# ## 2. Cleaning

# %%
log = {}  # numbers to copy into the submission sheet
# 2.1 duplicate customer IDs
log["duplicate_ids_removed"] = int(cust.customer_id.duplicated().sum())
cust = cust.drop_duplicates("customer_id", keep="first").reset_index(drop=True)

# 2.2 plan-name standardisation
def std_plan(x):
    x = str(x).strip().lower().replace("-", " ").replace("_", " ")
    x = x.replace("pre paid", "prepaid").replace("post paid", "postpaid")
    return " ".join(w.capitalize() for w in x.split())
log["plan_variants_before"] = int(pd.read_csv(RAW + "customers.csv").plan.nunique())
cust["plan"] = cust["plan"].map(std_plan)
log["plan_names_after"] = int(cust.plan.nunique())
print(cust.plan.value_counts())

# 2.3 missing usage: count, then impute with plan-wise median + flag
log["usage_rows_missing_entirely"] = int(len(cust) * 6 - len(usage))
log["usage_blank_values"] = int(usage[["voice_minutes", "data_gb", "sms_count"]].isnull().sum().sum())
usage = usage.merge(cust[["customer_id", "plan"]], on="customer_id", how="left")
for c in ["voice_minutes", "data_gb", "sms_count"]:
    usage[c] = usage[c].fillna(usage.groupby("plan")[c].transform("median"))
usage = usage.drop(columns="plan")

# 2.4 extreme bill values: IQR capping
q1, q3 = bill.charges.quantile([.25, .75]); iqr = q3 - q1
lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
log["extreme_bills_capped"] = int(((bill.charges > hi) | (bill.charges < lo)).sum())
bill["charges"] = bill.charges.clip(lo, hi)
bill["late_flag"] = (bill.payment_status != "Paid").astype(int)

# 2.5 incomplete support history
log["support_resolution_missing"] = int(sup.resolution_time_hrs.isnull().sum())
sup["resolution_time_hrs"] = sup.resolution_time_hrs.fillna(sup.resolution_time_hrs.median())
sup["category"] = sup.category.fillna("Unknown")

# %% [markdown]
# ## 3. Combine at CUSTOMER level (aggregate first, then merge)

# %%
usage = usage.sort_values(["customer_id", "month"])
u = usage.groupby("customer_id").agg(avg_voice=("voice_minutes", "mean"), avg_data=("data_gb", "mean"),
                                     avg_sms=("sms_count", "mean"))
first3 = usage[usage.month <= "2025-03"].groupby("customer_id")[["voice_minutes", "data_gb"]].mean().add_suffix("_first3")
last3 = usage[usage.month > "2025-03"].groupby("customer_id")[["voice_minutes", "data_gb"]].mean().add_suffix("_last3")
b = bill.groupby("customer_id").agg(avg_bill=("charges", "mean"), late_payments=("late_flag", "sum"),
                                    avg_late_days=("late_days", "mean"))
s = sup.groupby("customer_id").agg(tickets=("ticket_id", "count"), avg_resolution_hrs=("resolution_time_hrs", "mean"))
v = svc.pivot_table(index="customer_id", columns="event_type", values="event_id", aggfunc="count", fill_value=0)
v.columns = [c.lower().replace(" ", "_") + "s" for c in v.columns]       # network_issues, outages, plan_changes

df = cust.copy()
for part in [u, first3, last3, b, s, v]:
    df = df.merge(part, on="customer_id", how="left")
df["usage_missing_flag"] = df.avg_voice.isnull().astype(int)
for c in ["avg_voice", "avg_data", "avg_sms"]:
    df[c] = df[c].fillna(df.groupby("plan")[c].transform("median"))
for c in ["voice_minutes_first3", "voice_minutes_last3", "data_gb_first3", "data_gb_last3"]:
    df[c] = df[c].fillna(df.groupby("plan")[c].transform("median"))
df["tickets"] = df.tickets.fillna(0).astype(int)
df["avg_resolution_hrs"] = df.avg_resolution_hrs.fillna(0)          # no tickets -> 0 hrs
for c in ["network_issues", "outages", "plan_changes"]:
    df[c] = df[c].fillna(0).astype(int)
df["late_payments"] = df.late_payments.fillna(0).astype(int)
df["churn_flag"] = (df.churn == "Yes").astype(int)
log["final_rows"], log["final_cols"] = df.shape
df.to_csv("data/cleaned_churn_data.csv", index=False)      # DELIVERABLE 1
print("Cleaned dataset:", df.shape, "| remaining missing:", int(df.isnull().sum().sum()))

# %% [markdown]
# ## 4. EDA - the 6 analytical questions

# %%
df["tenure_group"] = pd.cut(df.tenure_months, [0, 6, 12, 24, 100], labels=["0-6", "7-12", "13-24", "24+"])
overall = df.churn_flag.mean()
print(f"Overall churn rate: {overall:.1%}")

def rate_plot(col, title, fname, order=None):
    r = df.groupby(col, observed=True).churn_flag.mean().mul(100)
    if order is None: r = r.sort_values(ascending=False)
    ax = r.plot(kind="bar", color="#2b6cb0", figsize=(7, 4), rot=30)
    ax.axhline(overall * 100, color="red", ls="--", label=f"Overall {overall:.1%}")
    ax.set_ylabel("Churn rate (%)"); ax.set_title(title); ax.legend()
    for i, val in enumerate(r): ax.text(i, val + .3, f"{val:.1f}", ha="center")
    plt.tight_layout(); plt.savefig(f"outputs/{fname}", dpi=130); plt.show()
    return r

# Q1 plans
q1_r = rate_plot("plan", "Q1. Churn rate by plan", "q1_churn_by_plan.png"); print(q1_r.round(1))
# Q2 tenure
q2_r = rate_plot("tenure_group", "Q2. Churn rate by tenure group (months)", "q2_churn_by_tenure.png", order=True); print(q2_r.round(1))
plt.figure(figsize=(6, 4)); sns.boxplot(data=df, x="churn", y="tenure_months"); plt.title("Tenure vs churn")
plt.savefig("outputs/q2_tenure_boxplot.png", dpi=130); plt.show()
# Q3 complaints
print(df.groupby("churn")[["tickets", "avg_resolution_hrs"]].mean().round(2))
plt.figure(figsize=(6, 4)); sns.barplot(data=df, x="churn", y="tickets", errorbar=None); plt.title("Q3. Avg tickets: churned vs retained")
plt.savefig("outputs/q3_tickets_vs_churn.png", dpi=130); plt.show()
# Q4 late payments
q4_r = df.groupby(df.late_payments.clip(upper=4)).churn_flag.mean().mul(100)
q4_r.plot(kind="bar", color="#c05621", figsize=(6, 4), rot=0); plt.xlabel("Late payments in 6 months (4 = 4+)")
plt.ylabel("Churn rate (%)"); plt.title("Q4. Late payments vs churn"); plt.tight_layout()
plt.savefig("outputs/q4_late_vs_churn.png", dpi=130); plt.show(); print(q4_r.round(1))
# Q5 region
q5_r = rate_plot("region", "Q5. Churn rate by region", "q5_churn_by_region.png"); print(q5_r.round(1))
# Q6 usage / disengagement
fig, ax = plt.subplots(1, 3, figsize=(13, 4))
for a, c in zip(ax, ["avg_voice", "avg_data", "avg_sms"]):
    sns.boxplot(data=df, x="churn", y=c, ax=a, showfliers=False); a.set_title(c)
plt.suptitle("Q6. Usage patterns by churn"); plt.tight_layout(); plt.savefig("outputs/q6_usage_vs_churn.png", dpi=130); plt.show()
df["voice_drop"] = 1 - df.voice_minutes_last3 / df.voice_minutes_first3.replace(0, np.nan)
print(df.groupby("churn").voice_drop.mean().round(3))

# heatmap
num = df.select_dtypes("number").drop(columns=["age"]).corr()
plt.figure(figsize=(11, 8)); sns.heatmap(num, cmap="coolwarm", center=0, annot=False)
plt.title("Correlation heatmap"); plt.tight_layout(); plt.savefig("outputs/correlation_heatmap.png", dpi=130); plt.show()
print(num["churn_flag"].drop("churn_flag").sort_values(key=abs, ascending=False).round(3).head(10))

# %%
import json
log["overall_churn_rate_pct"] = round(overall * 100, 1)
json.dump(log, open("outputs/cleaning_log.json", "w"), indent=2)
print(json.dumps(log, indent=2))
