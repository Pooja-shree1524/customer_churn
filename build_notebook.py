"""Converts 01_eda_cleaning.py + 02_features_model.py ('# %%' cells) into notebooks/churn_eda_model.ipynb and executes it."""
import nbformat as nbf
nb = nbf.v4.new_notebook(); cells = []
for fn in ["01_eda_cleaning.py", "02_features_model.py"]:
    for chunk in open(fn).read().split("# %%"):
        chunk = chunk.strip("\n")
        if not chunk.strip(): continue
        if chunk.startswith(" [markdown]"):
            md = "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#") for l in chunk.split("\n")[1:])
            cells.append(nbf.v4.new_markdown_cell(md))
        else:
            cells.append(nbf.v4.new_code_cell(chunk))
nb.cells = cells
nbf.write(nb, "notebooks/churn_eda_model.ipynb")
from nbconvert.preprocessors import ExecutePreprocessor
ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": "."}})
nbf.write(nb, "notebooks/churn_eda_model.ipynb"); print("notebook built + executed")
