# SPDX-License-Identifier: Apache-2.0
"""Release helpers used by .github/workflows/release.yml. Standard library only.

python tools/release_prep.py check v1.0.0     the tag matches trailsbi.brand.VERSION
python tools/release_prep.py readme v1.0.0    README images point at the tagged files on GitHub,
                                              so they also show on PyPI
python tools/release_prep.py notes 1.0.0      the CHANGELOG section for that version
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "trailsbi/trailsbi"


def version() -> str:
    text = (ROOT / "src" / "trailsbi" / "brand.py").read_text(encoding="utf-8")
    return re.search(r'^VERSION = "([^"]+)"', text, re.M).group(1)


def check(tag: str) -> int:
    if tag.lstrip("v") != version():
        print(f"Tag {tag} does not match VERSION {version()} in src/trailsbi/brand.py", file=sys.stderr)
        return 1
    print(f"Releasing {version()}")
    return 0


def readme(tag: str) -> int:
    path = ROOT / "README.md"
    base = f"https://raw.githubusercontent.com/{REPO}/{tag}/"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'src="(docs/[^"]+)"', lambda m: f'src="{base}{m.group(1)}"', text)
    path.write_text(text, encoding="utf-8")
    return 0


def notes(ver: str) -> int:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(ver)}\b.*?\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        print(f"CHANGELOG.md has no section for {ver}", file=sys.stderr)
        return 1
    print(m.group(1).strip())
    return 0


if __name__ == "__main__":
    commands = {"check": check, "readme": readme, "notes": notes}
    if len(sys.argv) != 3 or sys.argv[1] not in commands:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(commands[sys.argv[1]](sys.argv[2]))
