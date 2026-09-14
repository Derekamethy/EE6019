"""Dependency-light structural QA for the public GitHub release."""
from pathlib import Path
import ast
import json
import re

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "configs/final_rf.json",
    "notebooks/canonical/01_final_random_forest_pipeline.ipynb",
    "clinical_error_analysis/README.md",
    "clinical_error_analysis/notebooks/v5_clinical_error_analysis.ipynb",
    "src/eeg_seizure_detection/legacy_core.py",
    "results/headline_metrics.csv",
]

errors = []
for rel in REQUIRED:
    if not (ROOT / rel).exists():
        errors.append(f"missing required file: {rel}")

for path in ROOT.rglob("*.py"):
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"python parse failed: {path.relative_to(ROOT)}: {exc}")
for path in ROOT.rglob("*.ipynb"):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"notebook JSON failed: {path.relative_to(ROOT)}: {exc}")

text_suffixes = {".py", ".md", ".csv", ".json", ".toml", ".txt"}
windows_user_prefix = "C:" + chr(92) + "Users" + chr(92)
private_patterns = [re.compile(re.escape(windows_user_prefix), re.I)]
for path in ROOT.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in text_suffixes:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    if any(pattern.search(text) for pattern in private_patterns):
        errors.append(f"local Windows user path leaked: {path.relative_to(ROOT)}")

if (ROOT / "EE6019_DL_DG_Rebuild").exists():
    errors.append("exploratory DL/DG rebuild must remain excluded")
clinical = list((ROOT / "clinical_error_analysis/notebooks").glob("v*_*.ipynb"))
if len(clinical) != 5:
    errors.append(f"expected 5 clinical-error notebooks, found {len(clinical)}")
if errors:
    print("RELEASE QA FAILED")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("RELEASE QA PASSED")
print(f"Python files parsed: {len(list(ROOT.rglob('*.py')))}")
print(f"Notebooks validated: {len(list(ROOT.rglob('*.ipynb')))}")
print("Clinical error notebooks: 5")
print("Exploratory DL/DG rebuild: excluded")