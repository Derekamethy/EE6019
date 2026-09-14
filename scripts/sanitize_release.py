from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]

# Remove duplicates created during the first staging pass.
for rel in [
    "notebooks/01_canonical_random_forest_pipeline.ipynb",
    "extensions/01_1d_cnn_addon.ipynb",
]:
    p = ROOT / rel
    if p.exists():
        p.unlink()

# Sanitize local absolute paths only in the release copies.
pattern = re.compile(r"C:\\\\Users\\\\12276\\\\[^\"\n\\r]*", re.IGNORECASE)
changed = []
for path in ROOT.rglob("*.ipynb"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    new_text = pattern.sub("<LOCAL_DATA_ROOT>", text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        changed.append(str(path.relative_to(ROOT)))

print("sanitized", len(changed), "notebooks")
for item in changed:
    print(item)

# Sanitize generated Markdown reports without changing scientific content.
md_path_pattern = re.compile(r"C:\\Users\\12276\\[^\r\n]*", re.IGNORECASE)
md_changed = []
for path in (ROOT / "clinical_error_analysis" / "reports").glob("*.md"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = []
    for line in text.splitlines():
        line = md_path_pattern.sub("<LOCAL_EXPORT_PATH>", line)
        lines.append(line.rstrip())
    new_text = "\n".join(lines).rstrip() + "\n"
    if new_text != text:
        path.write_text(new_text, encoding="utf-8", newline="\n")
        md_changed.append(str(path.relative_to(ROOT)))

print("sanitized markdown", len(md_changed))
for item in md_changed:
    print(item)

# Sanitize absolute paths embedded in exported CSV evidence.
csv_changed = []
for path in (ROOT / "clinical_error_analysis" / "results").rglob("*.csv"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    new_text = re.sub(
        r"C:\\Users\\12276\\[^,\r\n]*",
        "<LOCAL_EXPORT_PATH>",
        text,
        flags=re.IGNORECASE,
    )
    if new_text != text:
        path.write_text(new_text, encoding="utf-8", newline="\n")
        csv_changed.append(str(path.relative_to(ROOT)))

print("sanitized csv", len(csv_changed))
for item in csv_changed:
    print(item)
