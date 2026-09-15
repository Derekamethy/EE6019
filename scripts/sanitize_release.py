"""Sanitize machine-specific paths in public release copies."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WINDOWS_USER_PREFIX = "C:" + chr(92) + "Users" + chr(92)
path_pattern = re.compile(
    re.escape(WINDOWS_USER_PREFIX) + r"[^\"\r\n,]*",
    re.IGNORECASE,
)

changed = []
for suffix in ("*.ipynb", "*.md", "*.csv"):
    for path in ROOT.rglob(suffix):
        text = path.read_text(encoding="utf-8", errors="ignore")
        replacement = "<LOCAL_DATA_ROOT>" if path.suffix == ".ipynb" else "<LOCAL_EXPORT_PATH>"
        cleaned = path_pattern.sub(replacement, text)
        if cleaned != text:
            path.write_text(cleaned, encoding="utf-8", newline="\n")
            changed.append(str(path.relative_to(ROOT)))

print(f"sanitized {len(changed)} public release files")
for item in changed:
    print(item)
