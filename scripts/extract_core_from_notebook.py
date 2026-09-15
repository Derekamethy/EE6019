from pathlib import Path
import ast
import json

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/canonical/01_final_random_forest_pipeline.ipynb"
OUTPUT = ROOT / "src/eeg_seizure_detection/legacy_core.py"

SAFE_ASSIGNMENTS = {
    "GLOBAL_SEED", "CFG", "CACHE_SCHEMA_VERSION",
    "_CONFIG_HASH_CACHE", "_SOS_CACHE", "_BAND_MASK_CACHE",
    "_SYNC_INDEX_CACHE", "_BASE_FEATURE_NAMES_CACHE",
    "_STACKED_FEATURE_NAMES_CACHE",
}

nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
items = []
skipped = []
def assigned_names(node):
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []

for cell in nb["cells"]:
    if cell.get("cell_type") != "code":
        continue
    src = "".join(cell.get("source", []))
    src = "\n".join(
        line for line in src.splitlines()
        if not line.lstrip().startswith(("%", "!"))
    )
    try:
        tree = ast.parse(src)
    except Exception as exc:
        skipped.append(str(exc))
        continue

    for node in tree.body:
        keep = isinstance(
            node,
            (ast.Import, ast.ImportFrom, ast.FunctionDef,
             ast.AsyncFunctionDef, ast.ClassDef),
        )
        names = assigned_names(node)
        if names and any(name in SAFE_ASSIGNMENTS for name in names):
            keep = True
        if keep:
            items.append(ast.unparse(node))

seen_imports = set()
ordered = []
for item in items:
    if item.startswith(("import ", "from ")):
        if "IPython" in item or item in seen_imports:
            continue
        seen_imports.add(item)
    ordered.append(item)
header = '''"""Reusable core extracted from the canonical EE6019 final notebook.

Generated only inside github_release; the original notebook is never edited.
The notebook remains the source of truth for reported experiments.
"""
'''
OUTPUT.write_text(header + "\n" + "\n\n".join(ordered) + "\n", encoding="utf-8")

init_file = OUTPUT.parent / "__init__.py"
init_file.write_text(
    '"""EE6019 seizure-detection portfolio package."""\n',
    encoding="utf-8",
)

print(f"items={len(ordered)}")
print(f"skipped_cells={len(skipped)}")
print(f"output={OUTPUT}")
