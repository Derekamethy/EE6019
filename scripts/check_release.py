"""Dependency-light structural QA for the public GitHub release."""
from pathlib import Path
import ast
import json
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "CITATION.cff",
    "pyproject.toml",
    "configs/final_rf.json",
    "notebooks/canonical/01_final_random_forest_pipeline.ipynb",
    "clinical_error_analysis/README.md",
    "clinical_error_analysis/notebooks/v5_clinical_error_analysis.ipynb",
    "src/eeg_seizure_detection/legacy_core.py",
    "tests/test_core_behaviour.py",
    "results/headline_metrics.csv",
    "docs/EE6019_Final_Report_PUBLIC_REDACTED.pdf",
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

try:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    declared = {str(item).split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip().lower() for item in project.get("dependencies", [])}
    required_deps = {"numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "seaborn", "mne", "joblib", "xgboost", "emlearn"}
    missing_deps = sorted(required_deps - declared)
    if missing_deps:
        errors.append(f"pyproject runtime dependencies missing: {', '.join(missing_deps)}")
except Exception as exc:
    errors.append(f"pyproject parse failed: {exc}")

text_suffixes = {".py", ".md", ".csv", ".json", ".toml", ".txt", ".cff"}
windows_user_prefix = "C:" + chr(92) + "Users" + chr(92)
private_patterns = [re.compile(re.escape(windows_user_prefix), re.I)]
github_repo_prefix = "github.com/Derekamethy/"
stale_repo_refs = (
    github_repo_prefix + "EE" + "6019",
    github_repo_prefix + "Patient-specific-" + "seazure-detection",
)
for path in ROOT.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in text_suffixes:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    if any(pattern.search(text) for pattern in private_patterns):
        errors.append(f"local Windows user path leaked: {path.relative_to(ROOT)}")
    if any(stale in text for stale in stale_repo_refs):
        errors.append(f"stale repository URL in public file: {path.relative_to(ROOT)}")
markdown_link_pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
root_resolved = ROOT.resolve()
for readme in [ROOT / "README.md", ROOT / "clinical_error_analysis/README.md"]:
    text = readme.read_text(encoding="utf-8", errors="ignore")
    if chr(0x8DEF) in text:
        errors.append(f"unexpected encoding artifact in public README: {readme.relative_to(ROOT)}")

for path in ROOT.rglob("*.md"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    for target in markdown_link_pattern.findall(text):
        target = target.strip()
        if not target or target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        local_target = target.split("#", 1)[0]
        if not local_target:
            continue
        resolved = (path.parent / local_target).resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
            errors.append(f"markdown link escapes repository: {path.relative_to(ROOT)} -> {target}")
            continue
        if not resolved.exists():
            errors.append(f"broken markdown link: {path.relative_to(ROOT)} -> {target}")

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
print("Runtime dependency declaration: complete")
print("Clinical error notebooks: 5")
print("Exploratory DL/DG rebuild: excluded")
