# SPDX-License-Identifier: Apache-2.0
"""Builds dist/trailsbi.pyz: the whole package in one file, runnable with `python trailsbi.pyz`.

For machines where pip is not available. Uses only the standard library.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "trailsbi"
TARGET = ROOT / "dist" / "trailsbi.pyz"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "app"
        shutil.copytree(PACKAGE, stage / "trailsbi", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (stage / "__main__.py").write_text(
            "from trailsbi.cli import main\n\nraise SystemExit(main())\n", encoding="utf-8"
        )
        TARGET.parent.mkdir(exist_ok=True)
        zipapp.create_archive(stage, TARGET, interpreter="/usr/bin/env python3", compressed=True)
    print(f"Wrote {TARGET} ({TARGET.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
