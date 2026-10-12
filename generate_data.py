"""
generate_data.py
Creates the 5 synthetic ConnectSphere Telecom CSV files in data/raw/
with the data-quality problems listed in the question paper:
  - Missing usage records        - Duplicate customer IDs
  - Different plan-name formats  - Extreme bill values
  - Incomplete support history
Run:  python generate_data.py
"""
import numpy as np, pandas as pd, os

rng = np.random.default_rng(42)
N = 5000
OUT = "data/raw"
os.makedirs(OUT, exist_ok=True)

PLANS = ["Prepaid Basic", "Prepaid Plus", "Postpaid Standard", "Postpaid Premium", "Broadband Home"]
PLAN_CHURN = {"Prepaid Basic": 0.55, "Prepaid Plus": 0.15, "Postpaid Standard": -0.15,
              "Postpaid Premium": -0.55, "Broadband Home": -0.25}
PLAN_BILL = {"Prepaid Basic": 250, "Prepaid Plus": 450, "Postpaid Standard": 700,
             "Postpaid Premium": 1200, "Broadband Home": 900}
REGIONS = ["North", "South", "East", "West", "Central"]
REGION_CHURN = {"North": 0.0, "South": -0.25, "East": 0.45, "West": -0.1, "Central": 0.15}
MONTHS = pd.period_range("2025-01", "2025-06", freq="M").astype(str)

# ---------------- customers ----------------
cid = [f"CS{100000 + i}" for i in range(N)]
plan = rng.choice(PLANS, N, p=[0.28, 0.22, 0.22, 0.12, 0.16])
region = rng.choice(REGIONS, N, p=[0.22, 0.2, 0.18, 0.22, 0.18])
tenure = np.clip(rng.exponential(24, N).round(), 1, 72).astype(int)
age = np.clip(rng.normal(38, 12, N).round(), 18, 80).astype(int)
gender = rng.choice(["Male", "Female", "Other"], N, p=[0.49, 0.49, 0.02])

logit = (-0.6 + np.array([PLAN_CHURN[p] for p in plan]) + np.array([REGION_CHURN[r] for r in region])
         - 0.035 * np.minimum(tenure, 48) + 0.35 * (tenure <= 6))
churn = rng.random(N) < 1 / (1 + np.exp(-logit))

customers = pd.DataFrame({
    "customer_id": cid, "age": age, "gender": gender, "region": region, "plan": plan,
    "tenure_months": tenure,
    "join_date": (pd.Timestamp("2025-06-30") - pd.to_timedelta(tenure * 30, unit="D")).strftime("%Y-%m-%d"),
    "churn": np.where(churn, "Yes", "No")})

# ---------------- usage (6 months per customer) ----------------
base_voice = {"Prepaid Basic": 180, "Prepaid Plus": 260, "Postpaid Standard": 340, "Postpaid Premium": 420, "Broadband Home": 60}
base_data = {"Prepaid Basic": 4, "Prepaid Plus": 9, "Postpaid Standard": 16, "Postpaid Premium": 30, "Broadband Home": 220}
rows = []
for i in range(N):
    p, ch = plan[i], churn[i]
    scale = rng.lognormal(0, 0.25)
    declining = rng.random() < (0.55 if ch else 0.12)   # not every churner fades out
    for m, month in enumerate(MONTHS):
        decay = (1 - rng.uniform(0.06, 0.12) * m) if declining else 1.0   # disengagement pattern
        decay = max(decay, 0.2)
        rows.append((cid[i], month,
                     max(0, rng.normal(base_voice[p] * scale * decay, 25)),
                     max(0, rng.normal(base_data[p] * scale * decay, base_data[p] * 0.1)),
                     max(0, rng.normal(60 * scale * decay, 12))))
usage = pd.DataFrame(rows, columns=["customer_id", "month", "voice_minutes", "data_gb", "sms_count"])
usage[["voice_minutes", "data_gb"]] = usage[["voice_minutes", "data_gb"]].round(1)
usage["sms_count"] = usage["sms_count"].round().astype(int)
# DQ: missing usage records (whole rows dropped + blank values)
usage = usage.drop(usage.sample(frac=0.04, random_state=1).index)
for k, col in enumerate(["voice_minutes", "data_gb", "sms_count"]):
    usage.loc[usage.sample(frac=0.025, random_state=10 + k).index, col] = np.nan

# ---------------- billing ----------------
rows = []
for i in range(N):
    p, ch = plan[i], churn[i]
    for month in MONTHS:
        charge = max(99, rng.normal(PLAN_BILL[p], PLAN_BILL[p] * 0.12))
        u = rng.random()
        late_p = 0.17 if ch else 0.08
        status = "Paid" if u > late_p + 0.02 else ("Late" if u > 0.02 + (late_p * 0.25) else "Unpaid")
        rows.append((cid[i], month, round(charge, 2), status))
billing = pd.DataFrame(rows, columns=["customer_id", "month", "charges", "payment_status"])
billing["late_days"] = np.where(billing.payment_status == "Paid", 0,
                                rng.integers(3, 45, len(billing)))
# DQ: extreme bill values
idx = billing.sample(frac=0.006, random_state=3).index
billing.loc[idx, "charges"] = (billing.loc[idx, "charges"] * rng.uniform(8, 30, len(idx))).round(2)

# ---------------- support ----------------
rows, t = [], 1
cats = ["Billing", "Network", "Plan Query", "Service Quality", "Other"]
for i in range(N):
    n = rng.poisson(1.9 if churn[i] else 0.8)
    for _ in range(n):
        res = max(1, rng.normal(46 if churn[i] else 32, 18) + rng.exponential(10))
        rows.append((f"TK{t:06d}", cid[i], rng.choice(cats, p=[.3, .3, .15, .15, .1]),
                     pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(rng.integers(0, 180))),
                     round(res, 1), rng.choice(["Resolved", "Open", "Escalated"], p=[.8, .08, .12])))
        t += 1
support = pd.DataFrame(rows, columns=["ticket_id", "customer_id", "category", "ticket_date",
                                      "resolution_time_hrs", "status"])
# DQ: incomplete support history (missing resolution times; many customers have no record)
support.loc[support.sample(frac=0.07, random_state=5).index, "resolution_time_hrs"] = np.nan
support.loc[support.sample(frac=0.03, random_state=6).index, "category"] = np.nan

# ---------------- service ----------------
rows, e = [], 1
for i in range(N):
    n = rng.poisson(1.4 if churn[i] else 0.7)
    for _ in range(n):
        et = rng.choice(["Network Issue", "Outage", "Plan Change"], p=[.45, .3, .25])
        rows.append((f"EV{e:06d}", cid[i], et,
                     pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(rng.integers(0, 180))),
                     round(rng.exponential(5), 1) if et != "Plan Change" else 0.0))
        e += 1
service = pd.DataFrame(rows, columns=["event_id", "customer_id", "event_type", "event_date", "duration_hrs"])

# ---------------- remaining data-quality problems ----------------
def messy(p):
    r = rng.random()
    if r < 0.60: return p
    if r < 0.70: return p.lower()
    if r < 0.78: return p.upper()
    if r < 0.86: return p.replace(" ", "-")
    if r < 0.92: return p.replace(" ", "_").lower()
    if r < 0.96: return "  " + p + " "
    return p.replace("Prepaid", "Pre-paid").replace("Postpaid", "Post paid")
customers["plan"] = customers["plan"].map(messy)          # different plan-name formats
dups = customers.sample(150, random_state=7)               # duplicate customer IDs
customers = pd.concat([customers, dups]).sample(frac=1, random_state=8).reset_index(drop=True)

customers.to_csv(f"{OUT}/customers.csv", index=False)
usage.to_csv(f"{OUT}/usage.csv", index=False)
billing.to_csv(f"{OUT}/billing.csv", index=False)
support.to_csv(f"{OUT}/support.csv", index=False)
service.to_csv(f"{OUT}/service.csv", index=False)
for n, d in [("customers", customers), ("usage", usage), ("billing", billing), ("support", support), ("service", service)]:
    print(f"{n}.csv: {d.shape[0]} rows x {d.shape[1]} cols")
print("True churn rate:", round(churn.mean() * 100, 1), "%")
