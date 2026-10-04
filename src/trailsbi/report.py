# SPDX-License-Identifier: Apache-2.0
"""Loads report definitions (PBIR folders or legacy report.json): pages, visuals and the
fields each visual uses."""

from __future__ import annotations

import re
from pathlib import Path

from .utils import loads_maybe, read_json, warn

VISUAL_NAMES = {
    "tableEx": "Table",
    "pivotTable": "Matrix",
    "cardVisual": "Card",
    "multiRowCard": "Multi-row card",
    "kpi": "KPI",
    "advancedSlicerVisual": "Button slicer",
    "actionButton": "Button",
    "textbox": "Text box",
    "basicShape": "Shape",
    "shape": "Shape",
    "image": "Image",
    "pageNavigator": "Page navigator",
    "bookmarkNavigator": "Bookmark navigator",
    "listSlicer": "List slicer",
    "textSlicer": "Text slicer",
}


def pretty_visual(vtype):
    if not vtype:
        return "Visual"
    if vtype in VISUAL_NAMES:
        return VISUAL_NAMES[vtype]
    if re.match(r"(?i)^pbi_cv_", vtype) or re.search(r"[0-9A-F]{12}", vtype):
        return "Custom visual"
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", vtype).lower()
    return words[:1].upper() + words[1:]


def _entity(expr, aliases):
    if not isinstance(expr, dict):
        return None
    sr = expr.get("SourceRef")
    if isinstance(sr, dict):
        return sr.get("Entity") or aliases.get(sr.get("Source"))
    return None


def _role_from_path(path):
    keys = [k for k in path if isinstance(k, str)]
    low = [k.lower() for k in keys]
    if any("filter" in k for k in low):
        return "Filter"
    if "querystate" in low:
        idx = low.index("querystate")
        if idx + 1 < len(keys):
            return keys[idx + 1]
    if "sortdefinition" in low:
        return "Sort"
    if any(k in ("objects", "visualcontainerobjects", "vcobjects") for k in low):
        return "Formatting"
    return "Other"


def walk_fields(node, out, path=(), aliases=None, role=None):
    """Collects every column / measure / hierarchy-level reference in a JSON tree."""
    aliases = aliases or {}
    if isinstance(node, dict):
        if isinstance(node.get("From"), list):
            aliases = dict(aliases)
            for f in node["From"]:
                if isinstance(f, dict) and f.get("Name"):
                    aliases[f["Name"]] = f.get("Entity")
        r = role or _role_from_path(path)
        for kind in ("Column", "Measure"):
            x = node.get(kind)
            if isinstance(x, dict) and "Property" in x:
                ent = _entity(x.get("Expression"), aliases)
                if ent:
                    out.add((kind.lower(), ent, x["Property"], r))
        hl = node.get("HierarchyLevel")
        if isinstance(hl, dict):
            h = (hl.get("Expression") or {}).get("Hierarchy") or {}
            hexpr = h.get("Expression") or {}
            pvs = hexpr.get("PropertyVariationSource")
            if isinstance(pvs, dict):
                ent = _entity(pvs.get("Expression"), aliases)
                if ent:
                    out.add(("column", ent, pvs.get("Property"), r))
            else:
                ent = _entity(hexpr, aliases)
                if ent:
                    out.add(("level", ent, (h.get("Hierarchy"), hl.get("Level")), r))
        for k, v in node.items():
            if k == "selector":
                # A formatting selector only says which data point a colour or label applies
                # to. Power BI ignores one that points at a field that no longer exists, so it
                # is neither a dependency nor a missing field.
                continue
            walk_fields(v, out, path + (k,), aliases, role)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            walk_fields(item, out, path + (i,), aliases, role)


def _literal_title(objs):
    try:
        v = objs["title"][0]["properties"]["text"]["expr"]["Literal"]["Value"]
    except (KeyError, IndexError, TypeError):
        return None
    if isinstance(v, str) and len(v) >= 2 and v[0] == "'" and v[-1] == "'":
        return v[1:-1].replace("''", "'")
    return v if isinstance(v, str) else None


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _box(pos):
    pos = pos or {}
    return {
        "x": _num(pos.get("x")),
        "y": _num(pos.get("y")),
        "z": _num(pos.get("z")),
        "w": _num(pos.get("width")),
        "h": _num(pos.get("height")),
    }


def _resolve_group_offsets(items, groups, page_w, page_h):
    """PBIR can store a grouped visual's position relative to its group.
    Keep the stored position if it already lies inside its group, otherwise add
    the group's offset (walking up nested groups)."""

    def absolute(name, seen=()):
        g = groups.get(name)
        if not g or name in seen:
            return None
        parent = g.get("parent")
        box = dict(g["box"])
        if parent:
            pb = absolute(parent, seen + (name,))
            if pb and not _inside(box, pb):
                box["x"] += pb["x"]
                box["y"] += pb["y"]
        return box

    for it in items:
        parent = it.pop("parent", None)
        gb = absolute(parent) if parent else None
        if gb and not _inside(it, gb):
            shifted = dict(it, x=it["x"] + gb["x"], y=it["y"] + gb["y"])
            if _inside(shifted, gb) or not _inside(it, {"x": 0, "y": 0, "w": page_w, "h": page_h}):
                it["x"], it["y"] = shifted["x"], shifted["y"]


def _inside(b, outer, tol=2.0):
    return (
        b["x"] >= outer["x"] - tol
        and b["y"] >= outer["y"] - tol
        and b["x"] + b["w"] <= outer["x"] + outer["w"] + tol
        and b["y"] + b["h"] <= outer["y"] + outer["h"] + tol
    )


def load_pbir(def_dir: Path, report_name: str) -> dict:
    pages_dir = def_dir / "pages"
    meta = read_json(pages_dir / "pages.json") if (pages_dir / "pages.json").exists() else {}
    order = (meta or {}).get("pageOrder") or []
    report_filters = set()
    rj = def_dir / "report.json"
    if rj.exists():
        walk_fields((read_json(rj) or {}).get("filterConfig"), report_filters, role="Filter")
    pages = []
    for pdir in sorted(p for p in pages_dir.iterdir() if p.is_dir()) if pages_dir.is_dir() else []:
        pj = read_json(pdir / "page.json") if (pdir / "page.json").exists() else None
        if pj is None:
            continue
        pid = pj.get("name") or pdir.name
        filters = set()
        walk_fields(pj.get("filterConfig"), filters, role="Filter")
        binding = (pj.get("pageBinding") or {}).get("type")
        page = {
            "id": pid,
            "name": pj.get("displayName") or pid,
            "order": order.index(pid) if pid in order else 999 + len(pages),
            "hidden": pj.get("visibility") == "HiddenInViewMode",
            "kind": binding or ("Tooltip" if pj.get("type") == "Tooltip" else ""),
            "width": _num(pj.get("width"), 1280.0),
            "height": _num(pj.get("height"), 720.0),
            "filters": filters,
            "visuals": [],
        }
        vroot = pdir / "visuals"
        groups = {}
        for vdir in sorted(vroot.iterdir()) if vroot.is_dir() else []:
            vf = vdir / "visual.json"
            if not vf.exists():
                continue
            vj = read_json(vf) or {}
            name = vj.get("name") or vdir.name
            v = vj.get("visual")
            if not isinstance(v, dict):
                if isinstance(vj.get("visualGroup"), dict):
                    groups[name] = {"box": _box(vj.get("position")), "parent": vj.get("parentGroupName")}
                continue
            fields = set()
            walk_fields(vj, fields)
            item = _box(vj.get("position"))
            item.update(
                {
                    "id": name,
                    "type": v.get("visualType"),
                    "title": _literal_title(v.get("visualContainerObjects") or {}),
                    "fields": fields,
                    "hidden": bool(vj.get("isHidden")),
                    "parent": vj.get("parentGroupName"),
                }
            )
            page["visuals"].append(item)
        _resolve_group_offsets(page["visuals"], groups, page["width"], page["height"])
        pages.append(page)
    return {"name": report_name, "format": "PBIR", "pages": pages, "filters": report_filters}


def load_legacy_report(path: Path, report_name: str) -> dict:
    rj = read_json(path) or {}
    report_filters = set()
    walk_fields(loads_maybe(rj.get("filters")), report_filters, role="Filter")
    pages = []
    for idx, sec in enumerate(rj.get("sections", [])):
        filters = set()
        walk_fields(loads_maybe(sec.get("filters")), filters, role="Filter")
        scfg = loads_maybe(sec.get("config")) or {}
        page = {
            "id": sec.get("name") or f"page{idx}",
            "name": sec.get("displayName") or f"Page {idx + 1}",
            "order": sec.get("ordinal", idx),
            "hidden": scfg.get("visibility") == 1,
            "kind": "",
            "filters": filters,
            "visuals": [],
            "width": _num(sec.get("width"), 1280.0),
            "height": _num(sec.get("height"), 720.0),
        }
        for n, vc in enumerate(sec.get("visualContainers", [])):
            cfg = loads_maybe(vc.get("config")) or {}
            sv = cfg.get("singleVisual")
            if not isinstance(sv, dict):
                continue
            fields = set()
            proto = sv.get("prototypeQuery") or {}
            aliases = {f.get("Name"): f.get("Entity") for f in proto.get("From", []) if isinstance(f, dict)}
            ref_role = {}
            for role, items in (sv.get("projections") or {}).items():
                for it in items or []:
                    ref_role.setdefault(it.get("queryRef"), role)
            for item in proto.get("Select", []) or []:
                walk_fields(item, fields, aliases=aliases, role=ref_role.get(item.get("Name"), "Field"))
            rest = {k: v for k, v in sv.items() if k != "prototypeQuery"}
            walk_fields(rest, fields, path=("singleVisual",), aliases=aliases)
            walk_fields(loads_maybe(vc.get("filters")), fields, role="Filter")
            item = _box(vc)
            item.update(
                {
                    "id": cfg.get("name") or f"{idx}-{n}",
                    "type": sv.get("visualType"),
                    "title": _literal_title(sv.get("vcObjects") or {}),
                    "fields": fields,
                    "hidden": ((sv.get("display") or {}).get("mode") == "hidden"),
                }
            )
            page["visuals"].append(item)
        pages.append(page)
    return {"name": report_name, "format": "PBIR-Legacy", "pages": pages, "filters": report_filters}


def load_report_dir(rdir: Path) -> dict | None:
    name = rdir.name[: -len(".Report")] if rdir.name.lower().endswith(".report") else rdir.name
    if (rdir / "definition" / "pages").is_dir():
        return load_pbir(rdir / "definition", name)
    if (rdir / "report.json").exists():
        return load_legacy_report(rdir / "report.json", name)
    warn(f"No report definition found in {rdir}")
    return None
