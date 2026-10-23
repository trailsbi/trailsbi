# SPDX-License-Identifier: Apache-2.0
"""Puts a TrailsBI visual build into the package, for `trailsbi --embed`:

    python tools/update_visual.py path/to/TrailsBI.pbiviz

Copies it to src/trailsbi/visual/TrailsBI.pbiviz and prints its ID and version. Use a released
build of https://github.com/trailsbi/trailsbi-visual, and name the version in CHANGELOG.md.
"""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "src" / "trailsbi" / "visual" / "TrailsBI.pbiviz"


def main(argv: list) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    source = Path(argv[0])
    with zipfile.ZipFile(source) as z:
        visual = json.loads(z.read("package.json").decode("utf-8-sig"))["visual"]
        if f"resources/{visual['guid']}.pbiviz.json" not in z.namelist():
            raise SystemExit(f"{source.name} is not a packaged Power BI visual")
    if len(visual["guid"]) > 20:
        raise SystemExit(
            f"Visual ID {visual['guid']} is too long: Desktop puts it twice in a path capped at 256"
        )
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != TARGET.resolve():
        shutil.copyfile(source, TARGET)
    print(f"Bundled {visual['displayName']} {visual['version']} ({visual['guid']}) into src/trailsbi/visual/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
