"""
03_excel_workbook.py - builds ChurnAnalysis.xlsx with live formulas + charts.
Sheets: Summary | Analysis | Stats | Data   (Pivot Tables: see PIVOT_GUIDE.md)
Run after 02_features_model.py
"""
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from openpyxl.worksheet.table import Table, TableStyleInfo

df = pd.read_csv("data/churn_featured_data.csv")
cols = ["customer_id", "region", "plan", "tenure_months", "tenure_group", "churn", "avg_voice", "avg_data",
        "avg_sms", "avg_bill", "late_payments", "payment_behaviour", "tickets", "ticket_group",
        "avg_resolution_hrs", "outages", "usage_drop", "risk_score", "risk_level", "segment"]
d = df[cols].round(3)
N = len(d) + 1                                   # last data row
L = {c: get_column_letter(i + 1) for i, c in enumerate(cols)}
R = lambda c: f"Data!${L[c]}$2:${L[c]}${N}"      # absolute range of a column

F = "Arial"
H = Font(name=F, bold=True, color="FFFFFF"); HF = PatternFill("solid", fgColor="1F4E78")
B = Font(name=F); BB = Font(name=F, bold=True); T = Font(name=F, bold=True, size=14, color="1F4E78")
thin = Side(style="thin", color="BBBBBB"); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

wb = Workbook()
ws_sum, ws_an, ws_st, ws_d = wb.active, wb.create_sheet("Analysis"), wb.create_sheet("Stats"), wb.create_sheet("Data")
ws_sum.title = "Summary"

# ---------- Data sheet ----------
ws_d.append(cols)
for row in d.itertuples(index=False): ws_d.append(list(row))
for c in ws_d[1]: c.font, c.fill = H, HF
ws_d.freeze_panes = "A2"
tab = Table(displayName="ChurnData", ref=f"A1:{get_column_letter(len(cols))}{N}")
tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True); ws_d.add_table(tab)
for i in range(1, len(cols) + 1): ws_d.column_dimensions[get_column_letter(i)].width = 17

# ---------- Analysis sheet: churn by group (COUNTIFS) ----------
def hdr(ws, r, labels, c0=1):
    for j, t in enumerate(labels):
        c = ws.cell(r, c0 + j, t); c.font, c.fill, c.alignment, c.border = H, HF, Alignment(horizontal="center", wrap_text=True), BOX

ws_an["A1"] = "Churn analysis by group (all values are COUNTIFS formulas on the Data sheet)"; ws_an["A1"].font = T
blocks = [("Churn by Plan", "plan", sorted(d.plan.unique())),
          ("Churn by Tenure Group (months)", "tenure_group", ["0-6", "7-12", "13-24", "24+"]),
          ("Complaint Analysis (tickets in 6 months)", "ticket_group", ["0", "1-2", "3+"]),
          ("Payment Behaviour", "payment_behaviour", ["On-time", "1 late", "2+ late"]),
          ("Regional Comparison", "region", sorted(d.region.unique())),
          ("Customer Segments", "segment", sorted(d.segment.unique())),
          ("Risk Level (model)", "risk_level", ["High", "Medium", "Low"])]
r, pos = 3, {}
for title, col, cats in blocks:
    ws_an.cell(r, 1, title).font = BB
    hdr(ws_an, r + 1, [col.replace("_", " ").title(), "Customers", "Churned", "Churn Rate", "Avg Tickets", "Avg Late Payments"])
    first = r + 2
    for k, cat in enumerate(cats):
        rr = first + k
        ws_an.cell(rr, 1, cat)
        ws_an.cell(rr, 2, f'=COUNTIFS({R(col)},A{rr})')
        ws_an.cell(rr, 3, f'=COUNTIFS({R(col)},A{rr},{R("churn")},"Yes")')
        ws_an.cell(rr, 4, f'=IF(B{rr}=0,0,C{rr}/B{rr})'); ws_an.cell(rr, 4).number_format = "0.0%"
        ws_an.cell(rr, 5, f'=IFERROR(AVERAGEIFS({R("tickets")},{R(col)},A{rr}),0)'); ws_an.cell(rr, 5).number_format = "0.00"
        ws_an.cell(rr, 6, f'=IFERROR(AVERAGEIFS({R("late_payments")},{R(col)},A{rr}),0)'); ws_an.cell(rr, 6).number_format = "0.00"
        for c in range(1, 7): ws_an.cell(rr, c).font, ws_an.cell(rr, c).border = B, BOX
    last = first + len(cats) - 1
    pos[col] = (first, last, r + 1)
    r = last + 3
for i, w in enumerate([26, 12, 12, 12, 12, 18]): ws_an.column_dimensions[get_column_letter(i + 1)].width = w

def chart(ws, col, anchor, title, w=13, h=7):
    f, l, hr = pos[col]
    ch = BarChart(); ch.type = "col"; ch.title = title; ch.height, ch.width = h, w
    ch.add_data(Reference(ws_an, min_col=4, min_row=hr, max_row=l), titles_from_data=True)
    ch.set_categories(Reference(ws_an, min_col=1, min_row=f, max_row=l))
    ch.y_axis.title = "Churn rate"; ch.y_axis.numFmt = "0%"; ch.legend = None
    ch.y_axis.delete = False; ch.x_axis.delete = False
    ws.add_chart(ch, anchor)
chart(ws_an, "plan", "H3", "Churn rate by plan"); chart(ws_an, "tenure_group", "H19", "Churn rate by tenure group")
chart(ws_an, "ticket_group", "H35", "Churn rate by complaints"); chart(ws_an, "payment_behaviour", "H51", "Churn rate by payment behaviour")
chart(ws_an, "region", "H67", "Churn rate by region"); chart(ws_an, "segment", "H83", "Churn rate by customer segment")

# ---------- Stats sheet ----------
ws_st["A1"] = "Statistical analysis (formulas)"; ws_st["A1"].font = T
nums = ["tenure_months", "avg_voice", "avg_data", "avg_sms", "avg_bill", "late_payments", "tickets", "avg_resolution_hrs", "usage_drop"]
hdr(ws_st, 3, ["Variable", "Mean", "Median", "Std Dev", "Min", "Max", "Mean (Churned)", "Mean (Retained)", "Correlation with churn"])
for k, c in enumerate(nums):
    rr = 4 + k; ws_st.cell(rr, 1, c)
    for j, fn in enumerate(["AVERAGE", "MEDIAN", "STDEV", "MIN", "MAX"]):
        ws_st.cell(rr, 2 + j, f"={fn}({R(c)})")
    ws_st.cell(rr, 7, f'=AVERAGEIFS({R(c)},{R("churn")},"Yes")'); ws_st.cell(rr, 8, f'=AVERAGEIFS({R(c)},{R("churn")},"No")')
    # churn as 0/1 inside CORREL via helper column on Data (added below)
    ws_st.cell(rr, 9, f"=CORREL({R(c)},Data!$V$2:$V${N})")
    for j in range(1, 10):
        ws_st.cell(rr, j).font = B; ws_st.cell(rr, j).border = BOX
        if j > 1: ws_st.cell(rr, j).number_format = "0.00"
ws_d["V1"] = "churn_flag"; ws_d["V1"].font, ws_d["V1"].fill = H, HF
for i in range(2, N + 1): ws_d[f"V{i}"] = f'=IF({L["churn"]}{i}="Yes",1,0)'
ws_st["A15"] = "Assumption: correlation uses churn_flag (Data!V) = 1 if churn = Yes, else 0."; ws_st["A15"].font = Font(name=F, italic=True)
for i in range(1, 10): ws_st.column_dimensions[get_column_letter(i)].width = 20

# ---------- Summary sheet ----------
ws_sum["A1"] = "ConnectSphere Telecom - Customer Churn Insight: Summary"; ws_sum["A1"].font = Font(name=F, bold=True, size=16, color="1F4E78")
kpis = [("Total customers", f"=COUNTA({R('customer_id')})", "#,##0"),
        ("Churned customers", f'=COUNTIFS({R("churn")},"Yes")', "#,##0"),
        ("Overall churn rate", "=B4/B3", "0.0%"),
        ("Avg tenure (months)", f"=AVERAGE({R('tenure_months')})", "0.0"),
        ("Avg tickets - churned", f'=AVERAGEIFS({R("tickets")},{R("churn")},"Yes")', "0.00"),
        ("Avg tickets - retained", f'=AVERAGEIFS({R("tickets")},{R("churn")},"No")', "0.00"),
        ("High-risk customers (model)", f'=COUNTIFS({R("risk_level")},"High")', "#,##0")]
hdr(ws_sum, 2, ["Key metric", "Value"])
for k, (t, f, nf) in enumerate(kpis):
    ws_sum.cell(3 + k, 1, t).font = BB; c = ws_sum.cell(3 + k, 2, f); c.number_format, c.font = nf, B
    ws_sum.cell(3 + k, 1).border = c.border = BOX
# highest-churn lookups
def top(col, rr, label):
    f, l, _ = pos[col]
    ws_sum.cell(rr, 1, label).font = BB
    ws_sum.cell(rr, 2, f"=INDEX(Analysis!$A${f}:$A${l},MATCH(MAX(Analysis!$D${f}:$D${l}),Analysis!$D${f}:$D${l},0))")
    ws_sum.cell(rr, 3, f"=MAX(Analysis!$D${f}:$D${l})").number_format = "0.0%"
    for c in (1, 2, 3): ws_sum.cell(rr, c).border = BOX
    ws_sum.cell(rr, 2).font = ws_sum.cell(rr, 3).font = B
hdr(ws_sum, 11, ["Highest churn in...", "Group", "Churn rate"])
top("plan", 12, "Plan"); top("tenure_group", 13, "Tenure group"); top("region", 14, "Region")
top("segment", 15, "Segment"); top("payment_behaviour", 16, "Payment behaviour"); top("ticket_group", 17, "Complaint group")
ws_sum["A19"] = "Key findings, recommendations and the Pivot Tables / Pivot Charts are described in PIVOT_GUIDE.md. Charts below link to the Analysis sheet."
ws_sum["A19"].font = Font(name=F, italic=True)
for col, anc, ttl in [("plan", "E2", "Churn by plan"), ("tenure_group", "N2", "Churn by tenure"),
                      ("region", "E17", "Churn by region"), ("segment", "N17", "Churn by segment")]:
    chart(ws_sum, col, anc, ttl, w=12, h=7)
ws_sum.column_dimensions["A"].width = 30; ws_sum.column_dimensions["B"].width = 22; ws_sum.column_dimensions["C"].width = 14
wb.save("ChurnAnalysis.xlsx"); print("saved ChurnAnalysis.xlsx")
