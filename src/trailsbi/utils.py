# SPDX-License-Identifier: Apache-2.0
"""Small helpers shared by every module: warnings, file reading and value coercion."""

from __future__ import annotations

import json
import sys
from pathlib import Path

WARNINGS = []


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print(f"  ! {msg}", file=sys.stderr)


def read_text(path) -> str:
    return Path(path).read_text(encoding="utf-8-sig", errors="replace")


def read_json(path):
    try:
        return json.loads(read_text(path))
    except (OSError, ValueError) as exc:
        warn(f"Could not parse {path}: {exc}")
        return None


def loads_maybe(value):
    """Legacy report.json nests JSON documents inside strings."""
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return None
    try:
        return json.loads(value)
    except ValueError:
        return None


def as_text(value):
    """model.bim stores long expressions as a string or a list of lines."""
    if value is None:
        return None
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)
    return str(value)


def truthy(value) -> bool:
    return value is True or str(value).strip().lower() == "true"


def unquote(name: str) -> str:
    name = (name or "").strip()
    if len(name) >= 2 and name[0] == "'" and name[-1] == "'":
        return name[1:-1].replace("''", "'")
    return name


def is_auto_table(name: str) -> bool:
    """Auto date/time tables Power BI adds for each date column."""
    return name.startswith(("LocalDateTable_", "DateTableTemplate_"))
