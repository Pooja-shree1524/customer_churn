# Pivot Tables & Pivot Charts (manual - 10 minutes in Excel)

Python/openpyxl cannot create real PivotTables, so create them in Excel. `ChurnAnalysis.xlsx` already has the
formula tables (Analysis sheet), stats (Stats sheet), 10 charts and the Summary sheet.

1. Open `ChurnAnalysis.xlsx` -> sheet **Data** -> click any cell in the table (named `ChurnData`).
2. **Insert > PivotTable > New Worksheet**. Build the six pivots below (one new sheet each, rename the sheets).
3. For churn rate: put `churn_flag` in Values -> Value Field Settings -> **Average** -> Number format **Percentage**.
   (`churn_flag` is column V; if it shows as blank, press F9 / recalculate.)
4. Click inside each pivot -> **PivotTable Analyze > PivotChart > Clustered Column**.

| Pivot | Rows | Values |
|---|---|---|
| Churn by plan | plan | Count of customer_id, Average of churn_flag |
| Churn by tenure group | tenure_group | Count of customer_id, Average of churn_flag |
| Complaint analysis | ticket_group | Count of customer_id, Average of churn_flag, Average of avg_resolution_hrs |
| Payment behaviour | payment_behaviour | Count of customer_id, Average of churn_flag |
| Regional comparison | region (Columns: plan optional) | Average of churn_flag |
| Customer segments | segment | Count of customer_id, Average of churn_flag, Average of risk_score |

5. Optional: Insert > **Slicer** on `region` and `plan` for an interactive dashboard.
6. Copy 2-3 pivot charts to the **Summary** sheet and add 3 lines of key findings (use your real numbers).
