# SPDX-License-Identifier: Apache-2.0
"""Parser for TMDL (Tabular Model Definition Language) files."""

from __future__ import annotations

import re
import textwrap

from .utils import unquote

TMDL_OBJECTS = {
    "table",
    "column",
    "measure",
    "partition",
    "expression",
    "relationship",
    "hierarchy",
    "level",
    "calculationItem",
    "model",
    "database",
    "role",
    "tablePermission",
    "columnPermission",
    "perspective",
    "perspectiveTable",
    "perspectiveColumn",
    "perspectiveMeasure",
    "perspectiveHierarchy",
    "cultureInfo",
    "linguisticMetadata",
    "translation",
    "annotation",
    "extendedProperty",
    "changedProperty",
    "variation",
    "dataSource",
    "queryGroup",
    "function",
    "calendar",
    "roleMembership",
    "alternateOf",
    "member",
}

_DECL_RE = re.compile(
    r"^(?P<kw>[A-Za-z]+)[ \t]+(?P<name>'(?:[^']|'')*'|[^\s='][^\s=]*)"
    r"(?:[ \t]*=[ \t]*(?P<rest>.*))?$"
)
_PROP_RE = re.compile(r"^(?P<key>[A-Za-z_]\w*)[ \t]*(?P<sep>[:=])[ \t]*(?P<val>.*)$")


def _indent(line):
    tabs = spaces = 0
    for ch in line:
        if ch == "\t":
            tabs += 1
        elif ch == " ":
            spaces += 1
        else:
            break
    return tabs + spaces // 4


def _dedent(buf):
    fixed = [re.sub(r"^\t+", lambda m: "    " * len(m.group()), ln) for ln in buf]
    return textwrap.dedent("\n".join(fixed)).strip("\n")


def _is_structural(stripped):
    m = _DECL_RE.match(stripped)
    if m and m.group("kw") in TMDL_OBJECTS:
        return True
    p = _PROP_RE.match(stripped)
    return bool(p and p.group("sep") == ":")


def _gather_indented(lines, i, min_indent, stop_on_structure=False):
    buf = []
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s:
            d = _indent(ln)
            if d < min_indent:
                break
            if stop_on_structure and d == min_indent and _is_structural(s):
                break
        buf.append(ln)
        i += 1
    while buf and not buf[-1].strip():
        buf.pop()
    return _dedent(buf), i


def _gather_fenced(lines, i):
    buf = []
    while i < len(lines):
        ln = lines[i]
        i += 1
        if ln.strip().startswith("```"):
            break
        buf.append(ln)
    return _dedent(buf), i


def _peek_indent(lines, i):
    while i < len(lines) and not lines[i].strip():
        i += 1
    return _indent(lines[i]) if i < len(lines) else -1


def parse_tmdl_text(text: str) -> list:
    """Returns a tree of {kw, name, rest, expr, props, children}."""
    lines = text.replace("\r\n", "\n").split("\n")
    roots, stack = [], []
    i = 0
    pending_desc = []
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("///"):
            pending_desc.append(s[3:].strip())
            i += 1
            continue
        if not s or s.startswith("//"):
            i += 1
            continue
        d = _indent(ln)
        while stack and stack[-1][0] >= d:
            stack.pop()
        parent = stack[-1][1] if stack else None

        m = _DECL_RE.match(s)
        if m and m.group("kw") in TMDL_OBJECTS:
            kw = m.group("kw")
            obj = {
                "kw": kw,
                "name": unquote(m.group("name")),
                "rest": None,
                "expr": None,
                "props": {},
                "children": [],
                "desc": "\n".join(pending_desc),
            }
            pending_desc = []
            rest = m.group("rest")
            i += 1
            if rest is not None:
                rest = rest.strip()
                if kw == "partition":
                    obj["rest"] = rest
                elif rest.startswith("```"):
                    obj["expr"], i = _gather_fenced(lines, i)
                elif rest == "":
                    if _peek_indent(lines, i) >= d + 2:
                        obj["expr"], i = _gather_indented(lines, i, d + 2)
                    else:
                        obj["expr"], i = _gather_indented(lines, i, d + 1, True)
                else:
                    obj["expr"] = rest
            (parent["children"] if parent else roots).append(obj)
            stack.append((d, obj))
            continue

        p = _PROP_RE.match(s)
        if p and parent is not None:
            key, sep, val = p.group("key"), p.group("sep"), p.group("val").strip()
            i += 1
            if sep == "=":
                if val.startswith("```"):
                    val, i = _gather_fenced(lines, i)
                elif val == "":
                    val, i = _gather_indented(lines, i, d + 1)
            parent["props"][key] = val
            continue

        if parent is not None and re.fullmatch(r"[A-Za-z_]\w*", s):
            parent["props"][s] = True  # flag such as isHidden / calculationGroup
        i += 1
    return roots


def split_col_ref(ref: str) -> tuple:
    """'Dim Customer'.'Customer Key'  ->  ('Dim Customer', 'Customer Key')"""
    m = re.match(r"^\s*('(?:[^']|'')*'|[^.]+)\.(.+?)\s*$", ref or "")
    if not m:
        return "", ""
    return unquote(m.group(1)), unquote(m.group(2))
