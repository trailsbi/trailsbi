# SPDX-License-Identifier: Apache-2.0
"""DAX analysis: which tables, columns and measures an expression refers to."""

from __future__ import annotations

import re

DAX_KW = {
    "RETURN",
    "VAR",
    "IN",
    "NOT",
    "AND",
    "OR",
    "TRUE",
    "FALSE",
    "ASC",
    "DESC",
    "DEFINE",
    "EVALUATE",
    "MEASURE",
    "COLUMN",
    "TABLE",
    "ORDER",
    "BY",
    "START",
    "AT",
    "BLANK",
    "ELSE",
    "THEN",
}

_Q_REF = re.compile(r"(?:'((?:[^']|'')+)'[ \t]*|([^\W\d]\w*))\[((?:[^\]]|\]\])+)\]")
_B_REF = re.compile(r"\[((?:[^\]]|\]\])+)\]")
_WORD = re.compile(r"'((?:[^']|'')+)'|(?<![\w.])([^\W\d]\w*)(?!\w)")


def dax_clean(expr: str) -> str:
    """Drops comments and string contents but keeps 'table' and [column] tokens."""
    out, i, n = [], 0, len(expr)
    while i < n:
        ch = expr[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if expr[j] == '"':
                    if j + 1 < n and expr[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            out.append('""')
            i = j + 1
        elif ch in ("'", "["):
            close = "'" if ch == "'" else "]"
            j = expr.find(close, i + 1)
            while j != -1 and j + 1 < n and expr[j + 1] == close:
                j = expr.find(close, j + 2)
            j = n - 1 if j == -1 else j
            out.append(expr[i : j + 1])
            i = j + 1
        elif expr.startswith("//", i) or expr.startswith("--", i):
            j = expr.find("\n", i)
            i = n if j == -1 else j
            out.append(" ")
        elif expr.startswith("/*", i):
            j = expr.find("*/", i + 2)
            i = n if j == -1 else j + 2
            out.append(" ")
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def dax_refs(expr: str) -> tuple:
    clean = dax_clean(expr or "")
    qual, bare, tables = [], [], []

    def qsub(m):
        name = m.group(3).replace("]]", "]")
        if m.group(2) is not None and m.group(2).upper() in DAX_KW:
            bare.append(name)
        else:
            tbl = m.group(1).replace("''", "'") if m.group(1) is not None else m.group(2)
            qual.append((tbl, name))
        return " "

    rest = _Q_REF.sub(qsub, clean)

    def bsub(m):
        bare.append(m.group(1).replace("]]", "]"))
        return " "

    rest = _B_REF.sub(bsub, rest)
    variables = {v.lower() for v in re.findall(r"\bVAR\s+([^\W\d]\w*)", rest, re.I)}
    for m in _WORD.finditer(rest):
        if m.group(1) is not None:
            tables.append(m.group(1).replace("''", "'"))
            continue
        word = m.group(2)
        after = rest[m.end() :].lstrip()[:1]
        if after == "(" or word.upper() in DAX_KW or word.lower() in variables:
            continue
        tables.append(word)
    return qual, bare, tables
