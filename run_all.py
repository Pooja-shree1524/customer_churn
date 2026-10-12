"""Runs the whole pipeline in order:  python run_all.py"""
import subprocess, sys
for step in ["generate_data.py", "01_eda_cleaning.py", "02_features_model.py", "03_excel_workbook.py",
             "04_submission_numbers.py", "05_extra_charts.py", "build_notebook.py"]:
    print(f"\n>>> {step}"); subprocess.run([sys.executable, step], check=True)
print("\nDone. Open ChurnAnalysis.xlsx (recalculate in Excel if prompted) and follow PIVOT_GUIDE.md.")
