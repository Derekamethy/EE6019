from pathlib import Path
import ast
import json

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/canonical/01_final_random_forest_pipeline.ipynb"
OUTPUT = ROOT / "src/eeg_seizure_detection/legacy_core.py"

nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
imports = []
definitions = []
skipped = []

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
        segment = ast.get_source_segment(src, node)
        if not segment:
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(segment)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.append(segment)

seen = set()
unique_imports = []
for item in imports:
    if item in seen or "IPython" in item:
        continue
    seen.add(item)
    unique_imports.append(item)

header = '''"""Reusable core extracted from the canonical EE6019 final notebook.

This generated copy exists only inside github_release. The original notebook is
never edited. The notebook remains the source of truth for reported experiments.
"""
from __future__ import annotations
'''
output = header + "\n" + "\n".join(unique_imports)
output += "\n\n" + "\n\n".join(definitions) + "\n"
OUTPUT.write_text(output, encoding="utf-8")

init_file = OUTPUT.parent / "__init__.py"
init_file.write_text(
    '"""EE6019 seizure-detection portfolio package."""\n',
    encoding="utf-8",
)

print(f"definitions={len(definitions)}")
print(f"imports={len(unique_imports)}")
print(f"skipped_cells={len(skipped)}")
print(f"output={OUTPUT}")
