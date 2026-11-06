# SPDX-License-Identifier: Apache-2.0
"""Function help for the code the page shows.

Only the functions a project actually uses travel with its page, so the help
costs a few kilobytes rather than the whole reference.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.resources import files

from .dax_functions import DAX_FUNCTIONS

_DAX_CALL = re.compile(r"([A-Za-z][A-Za-z0-9.]*)\s*\(")
_M_NAME = re.compile(r"#?[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


@lru_cache(maxsize=1)
def m_functions() -> dict:
    """Power Query functions: name -> [signature, description]."""
    text = files(__package__).joinpath("data").joinpath("m_functions.json").read_text(encoding="utf-8")
    return json.loads(text)


def code_lang(title: str) -> str:
    """dax, m or sql, from a code block's title (the page decides the same way)."""
    if "SQL" in title:
        return "sql"
    if "(M)" in title or "Power Query" in title:
        return "m"
    return "dax"


def _code_blocks(data: dict):
    for n in data.get("nodes", []):
        d = n.get("detail") or {}
        for c in d.get("code") or []:
            yield code_lang(c.get("title") or ""), c.get("text") or ""
        for s in d.get("steps") or []:
            yield "m", s.get("code") or ""
    for m in (data.get("meta") or {}).get("models") or []:
        for it in m.get("outline") or []:
            if it.get("x"):
                yield ("dax" if it.get("l") == "DAX" else "m"), it["x"]


def function_help(data: dict) -> dict:
    """Help for the functions used: {"dax": {NAME: [syntax, text]}, "m": {Name: [signature, text]}}."""
    mf = m_functions()
    dax, m = {}, {}
    for lang, text in _code_blocks(data):
        if lang == "dax":
            for name in _DAX_CALL.findall(text):
                key = name.upper()
                if key in DAX_FUNCTIONS:
                    dax[key] = list(DAX_FUNCTIONS[key])
        elif lang == "m":
            for name in set(_M_NAME.findall(text)):
                if name in mf:
                    m[name] = mf[name]
    return {"dax": dict(sorted(dax.items())), "m": dict(sorted(m.items()))}
