# SPDX-License-Identifier: Apache-2.0
"""Builds src/trailsbi/data/m_functions.json, the Power Query function help.

The source is the standard library description that ships with Microsoft's Power
Query language service (github.com/microsoft/vscode-powerquery, MIT licence):
server/src/library/standard/standard-enUs.json. Only what the help shows is kept:
each function's signature and its one-line description.

    python tools/build_m_functions.py path/to/standard-enUs.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "src" / "trailsbi" / "data" / "m_functions.json"


def signature(fn: dict) -> str:
    params = []
    for p in fn.get("functionParameters") or []:
        text = ("optional " if not p.get("isRequired") else "") + p["name"]
        ptype = re.sub(r"\s*\{[^}]*\}", "", p.get("type") or "")
        if ptype:
            nullable = p.get("isNullable") and ptype != "any" and not ptype.startswith("nullable")
            text += " as " + ("nullable " if nullable else "") + ptype
        params.append(text)
    ret = re.sub(r"\s*\{[^}]*\}", "", fn.get("type") or "") or "any"
    return f"{fn['name']}({', '.join(params)}) as {ret}"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    lib = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = {}
    for fn in lib:
        desc = ((fn.get("documentation") or {}).get("description") or "").strip()
        if not desc or fn.get("functionParameters") is None:
            continue  # constants and types have no call to explain
        out[fn["name"]] = [signature(fn), " ".join(desc.split())]
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(dict(sorted(out.items())), ensure_ascii=False, indent=0) + "\n", encoding="utf-8"
    )
    print(f"Wrote {TARGET.name}: {len(out)} functions, {TARGET.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
