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
    "src/eeg_seizure_detection/config.py",
    "src/eeg_seizure_detection/data.py",
    "src/eeg_seizure_detection/features.py",
    "src/eeg_seizure_detection/models.py",
    "src/eeg_seizure_detection/evaluation.py",
    "extensions/cnn/cnn_addon.py",
    "notebooks/reference/01_final_rf_reference.ipynb",
    "notebooks/reference/02_cnn_addon_reference.ipynb",
    "clinical_error_analysis/reference_notebooks/v5_clinical_error_analysis.ipynb",
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

reference_notebooks = list((ROOT / "notebooks" / "reference").glob("*.ipynb"))
clinical_notebooks = list(
    (ROOT / "clinical_error_analysis" / "reference_notebooks").glob("v*_*.ipynb")
)
all_notebooks = reference_notebooks + clinical_notebooks
for path in all_notebooks:
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"notebook JSON failed: {path.relative_to(ROOT)}: {exc}")
        continue
    for index, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            if cell.get("outputs"):
                errors.append(f"saved notebook output: {path.relative_to(ROOT)} cell {index}")
            if cell.get("execution_count") is not None:
                errors.append(f"saved execution count: {path.relative_to(ROOT)} cell {index}")

if len(reference_notebooks) != 2:
    errors.append(f"expected 2 primary reference notebooks, found {len(reference_notebooks)}")
if len(clinical_notebooks) != 5:
    errors.append(f"expected 5 clinical-error reference notebooks, found {len(clinical_notebooks)}")

try:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    declared = {
        str(item).split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip().lower()
        for item in project.get("dependencies", [])
    }
    required_deps = {
        "numpy", "pandas", "scipy", "scikit-learn", "matplotlib",
        "seaborn", "mne", "joblib", "xgboost", "emlearn",
    }
    missing_deps = sorted(required_deps - declared)
    if missing_deps:
        errors.append(f"pyproject runtime dependencies missing: {', '.join(missing_deps)}")
except Exception as exc:
    errors.append(f"pyproject parse failed: {exc}")

cjk_pattern = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
for path in list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.md")) + all_notebooks:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if cjk_pattern.search(text):
        errors.append(f"non-English CJK text in public source/reference file: {path.relative_to(ROOT)}")

legacy = ROOT / "src" / "eeg_seizure_detection" / "legacy_core.py"
if legacy.exists() and len(legacy.read_text(encoding="utf-8").splitlines()) > 80:
    errors.append("legacy_core.py must remain a thin compatibility layer (<= 80 lines)")

windows_user_prefix = "C:" + chr(92) + "Users" + chr(92)
github_repo_prefix = "github.com/Derekamethy/"
stale_repo_refs = (
    github_repo_prefix + "EE" + "6019",
    github_repo_prefix + "Patient-specific-" + "seazure-detection",
)
text_suffixes = {".py", ".md", ".csv", ".json", ".toml", ".txt", ".cff", ".ipynb"}
for path in ROOT.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in text_suffixes:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    if windows_user_prefix.lower() in text.lower():
        errors.append(f"local Windows user path leaked: {path.relative_to(ROOT)}")
    if any(stale in text for stale in stale_repo_refs):
        errors.append(f"stale repository URL in public file: {path.relative_to(ROOT)}")

markdown_link_pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
root_resolved = ROOT.resolve()
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

for stale_dir in [
    ROOT / "notebooks" / "canonical",
    ROOT / "clinical_error_analysis" / "notebooks",
    ROOT / "EE6019_DL_DG_Rebuild",
]:
    if stale_dir.exists():
        errors.append(f"stale or excluded directory must not exist: {stale_dir.relative_to(ROOT)}")

if errors:
    print("RELEASE QA FAILED")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("RELEASE QA PASSED")
print(f"Python files parsed: {len(list(ROOT.rglob('*.py')))}")
print(f"Primary reference notebooks: {len(reference_notebooks)}")
print(f"Clinical error reference notebooks: {len(clinical_notebooks)}")
print("Public Python/Markdown/reference notebooks: English-only")
print("Notebook saved outputs: none")
print("legacy_core.py: compatibility-only")
print("Exploratory DL/DG rebuild: excluded")
