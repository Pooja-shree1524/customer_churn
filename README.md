# ConnectSphere Telecom - Customer Churn Insight (U23AD491, DS Sprint SBA-2, Use Case 02)

NOTE: the 5 CSV files in data/raw/ are SYNTHETIC (made by generate_data.py) because the real files were not
available. They contain the 5 data-quality problems in the question paper. If your college gives you real
files, put them in data/raw/ with the same names, then check the column names used in 01_eda_cleaning.py.

## Run
    pip install -r requirements.txt
    python run_all.py          # whole pipeline (about 1-2 min)

## Files
| File | Purpose |
|---|---|
| generate_data.py | creates customers/usage/billing/support/service CSVs (seed 42, reproducible) |
| 01_eda_cleaning.py | cleaning, customer-level merge, 6 EDA questions, charts -> data/cleaned_churn_data.csv |
| 02_features_model.py | feature engineering, encoding, selection, Random Forest + Logistic baseline, risk scores, segments |
| 03_excel_workbook.py | builds ChurnAnalysis.xlsx (formulas, stats, 10 charts, Summary) |
| 05_extra_charts.py | churn distribution, plan counts, billing distribution, missing values, dashboard |
| 04_submission_numbers.py | prints the actual numbers to copy onto your answer sheets |
| build_notebook.py | builds + executes notebooks/churn_eda_model.ipynb (the Python notebook deliverable) |
| PIVOT_GUIDE.md | steps to add the Pivot Tables / Pivot Charts in Excel |
| outputs/ | charts (png), churn_risk_scores.csv, cleaning_log.json, model_results.json |

## Deliverables mapping
Cleaned dataset -> data/cleaned_churn_data.csv | Notebook -> notebooks/churn_eda_model.ipynb |
Excel -> ChurnAnalysis.xlsx (+ pivots) | Slides -> make 5-6 slides from outputs/*.png and the Summary sheet.
