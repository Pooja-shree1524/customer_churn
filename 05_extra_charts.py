"""Extra charts -> outputs/: churn distribution, customer count by plan, billing distribution,
missing value analysis, customer churn dashboard.  Run after 02_features_model.py"""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, seaborn as sns
sns.set_theme(style="whitegrid")
BLUE, RED, GREY = "#2b6cb0", "#e53e3e", "#a0aec0"
df = pd.read_csv("data/churn_featured_data.csv")
raw = {n: pd.read_csv(f"data/raw/{n}.csv") for n in ["customers", "usage", "billing", "support", "service"]}

# 1. churn distribution
fig, ax = plt.subplots(1, 2, figsize=(10, 4.5))
cnt = df.churn.value_counts().reindex(["No", "Yes"])
ax[0].pie(cnt, labels=["Retained", "Churned"], colors=[BLUE, RED], autopct="%1.1f%%", startangle=90,
          wedgeprops=dict(width=0.45), textprops={"fontsize": 11})
ax[0].set_title("Churn distribution (share)")
b = ax[1].bar(["Retained", "Churned"], cnt.values, color=[BLUE, RED])
for r in b: ax[1].text(r.get_x() + r.get_width() / 2, r.get_height() + 40, f"{int(r.get_height()):,}", ha="center")
ax[1].set_ylabel("Customers"); ax[1].set_title("Churn distribution (count)")
plt.tight_layout(); plt.savefig("outputs/churn_distribution.png", dpi=140); plt.close()

# 2. customer count by plan (retained vs churned stacked)
ct = pd.crosstab(df.plan, df.churn).reindex(df.plan.value_counts().index)
ax = ct[["No", "Yes"]].plot(kind="bar", stacked=True, color=[BLUE, RED], figsize=(8, 4.8), rot=20)
ax.legend(["Retained", "Churned"]); ax.set_ylabel("Customers"); ax.set_xlabel("")
ax.set_title("Customer count by plan")
for i, (n, y) in enumerate(zip(ct.sum(axis=1), ct.sum(axis=1))): ax.text(i, y + 25, f"{int(n):,}", ha="center", fontweight="bold")
plt.tight_layout(); plt.savefig("outputs/customer_count_by_plan.png", dpi=140); plt.close()

# 3. billing charge distribution (raw vs after IQR capping)
bill = raw["billing"].charges
q1, q3 = bill.quantile([.25, .75]); hi = q3 + 1.5 * (q3 - q1); lo = q1 - 1.5 * (q3 - q1)
capped = bill.clip(lo, hi)
fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
ax[0].hist(bill, bins=60, color=RED); ax[0].set_title("Raw charges (extreme values visible)"); ax[0].set_xlabel("Charge")
ax[1].hist(capped, bins=40, color=BLUE); ax[1].set_title("After IQR capping"); ax[1].set_xlabel("Charge")
ax[1].axvline(hi, color="k", ls="--", label=f"Upper cap = {hi:,.0f}"); ax[1].legend()
sns.boxplot(data=pd.DataFrame({"Raw": bill, "Capped": capped}), ax=ax[2], palette=[RED, BLUE]); ax[2].set_title("Boxplot: raw vs capped")
ax[2].set_ylabel("Charge")
plt.suptitle(f"Billing charge distribution ({int((bill > hi).sum())} extreme values capped)", fontweight="bold")
plt.tight_layout(); plt.savefig("outputs/billing_charge_distribution.png", dpi=140); plt.close()

# 4. missing value analysis (raw files)
rows = []
for f, cols in [("usage", ["voice_minutes", "data_gb", "sms_count"]), ("support", ["resolution_time_hrs", "category"]),
                ("customers", ["plan", "age"]), ("billing", ["charges"])]:
    for c in cols: rows.append((f"{f}.{c}", raw[f][c].isnull().mean() * 100))
n_cust = raw["customers"].customer_id.nunique()
rows.append(("usage.months not recorded", (1 - len(raw["usage"]) / (n_cust * 6)) * 100))
rows.append(("customers with no support history", (1 - raw["support"].customer_id.nunique() / n_cust) * 100))
m = pd.DataFrame(rows, columns=["field", "pct"]).sort_values("pct")
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(m.field, m.pct, color=[RED if p > 0 else GREY for p in m.pct])
for i, p in enumerate(m.pct): ax.text(p + 0.4, i, f"{p:.1f}%", va="center")
ax.set_xlabel("% missing / incomplete"); ax.set_title("Missing value analysis (raw data, before cleaning)")
ax.set_xlim(0, m.pct.max() * 1.15); plt.tight_layout(); plt.savefig("outputs/missing_value_analysis.png", dpi=140); plt.close()

# 5. dashboard
fig = plt.figure(figsize=(16, 10)); fig.suptitle("ConnectSphere Telecom - Customer Churn Dashboard", fontsize=20, fontweight="bold", color="#1F4E78")
gs = fig.add_gridspec(3, 4, height_ratios=[0.5, 1.5, 1.5], hspace=0.55, wspace=0.35)
kp = [("Customers", f"{len(df):,}", BLUE), ("Churned", f"{(df.churn=='Yes').sum():,}", RED),
      ("Churn rate", f"{df.churn_flag.mean():.1%}", RED), ("High-risk (model)", f"{(df.risk_level=='High').sum():,}", "#dd6b20")]
for i, (t, v, c) in enumerate(kp):
    a = fig.add_subplot(gs[0, i]); a.axis("off")
    a.add_patch(plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.12, transform=a.transAxes))
    a.text(.5, .62, v, ha="center", va="center", fontsize=24, fontweight="bold", color=c); a.text(.5, .15, t, ha="center", fontsize=12)
def bar(a, s, title, color=BLUE, rot=20):
    s = s.sort_values(ascending=False); a.bar(s.index, s.values, color=color)
    a.axhline(df.churn_flag.mean() * 100, color="k", ls="--", lw=1); a.set_title(title, fontsize=11); a.tick_params(axis="x", rotation=rot, labelsize=8)
    for i, v in enumerate(s.values): a.text(i, v + .5, f"{v:.0f}%", ha="center", fontsize=8)
rate = lambda c: df.groupby(c).churn_flag.mean() * 100
bar(fig.add_subplot(gs[1, 0]), rate("plan"), "Churn rate by plan")
a = fig.add_subplot(gs[1, 1]); t = rate("tenure_group").reindex(["0-6", "7-12", "13-24", "24+"]); a.bar(t.index, t.values, color=BLUE)
a.set_title("Churn rate by tenure (months)", fontsize=11)
for i, v in enumerate(t.values): a.text(i, v + .5, f"{v:.0f}%", ha="center", fontsize=8)
bar(fig.add_subplot(gs[1, 2]), rate("region"), "Churn rate by region", rot=0)
bar(fig.add_subplot(gs[1, 3]), rate("payment_behaviour"), "Churn rate by payment behaviour", color="#c05621", rot=0)
bar(fig.add_subplot(gs[2, 0]), rate("ticket_group"), "Churn rate by complaints (tickets)", color="#c05621", rot=0)
bar(fig.add_subplot(gs[2, 1:3]), rate("segment"), "Churn rate by customer segment", color="#2f855a", rot=10)
a = fig.add_subplot(gs[2, 3]); rl = df.risk_level.value_counts().reindex(["Low", "Medium", "High"])
a.pie(rl, labels=rl.index, colors=["#68d391", "#f6e05e", RED], autopct="%1.0f%%", wedgeprops=dict(width=0.45)); a.set_title("Model risk levels", fontsize=11)
fig.text(0.5, 0.02, "Dashed line = overall churn rate", ha="center", fontsize=9, style="italic")
plt.savefig("outputs/customer_churn_dashboard.png", dpi=130, bbox_inches="tight"); plt.close()
print("5 charts saved to outputs/")
