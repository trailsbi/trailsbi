# SPDX-License-Identifier: Apache-2.0
"""Workspace runs: picking what to build, the overview of items and the CSV export.

A workspace is a folder with several reports and semantic models (see project.py).
This module holds what only a workspace needs:

* display names that stay unique when two items share a folder name;
* --model / --report / --with-reports / --include, and --list;
* the scope the page opens on (a large workspace opens on its busiest model);
* the item overview: data sources -> semantic models -> reports, including
  models that read other models (composite models) and published models the
  folder does not hold;
* the nodes and edges as CSV files.
"""

from __future__ import annotations

import fnmatch
from collections import defaultdict
from pathlib import Path, PurePosixPath

from .project import ITEM_SUFFIX, display_name, space_key
from .utils import read_json, warn

SCOPE_LIMIT = 1500  # above this many items the page opens on one model, not the whole folder


class SelectionError(Exception):
    """The selection names nothing in the folder, or its file cannot be read."""


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


# ---------------------------------------------------------------- names


def labels(paths, root) -> dict:
    """{path: (display name, path inside the folder)}. Two items with the same display name
    are told apart by their path inside the folder. `root` is the folder, or a function that
    gives an item's path."""

    def rel(p):
        if callable(root):
            return root(p)
        try:
            return p.relative_to(root).as_posix()
        except ValueError:
            return p.name

    base = {p: display_name(p) for p in paths}
    counts = defaultdict(int)
    for v in base.values():
        counts[v.lower()] += 1
    return {
        p: ((ITEM_SUFFIX.sub("", rel(p)) if counts[base[p].lower()] > 1 else base[p]), rel(p)) for p in paths
    }


# ---------------------------------------------------------------- selection


def sel_names(values) -> list:
    """--model A --model "B,C" and --model "B, C" all mean the same three."""
    out = []
    for v in values or []:
        out += [x.strip() for x in str(v).split(",") if x.strip()]
    return out


def sel_match(pats, label: str, rel: str) -> bool:
    """True when one of the patterns names this item. A pattern may be the display name, the
    path inside the folder or the folder name, with or without the .SemanticModel / .Report
    suffix, and may use * and ? wildcards. Case and slash direction do not matter."""
    if not pats:
        return False
    cands = set()
    for v in (label, rel, PurePosixPath(str(rel).replace("\\", "/")).name):
        if not v:
            continue
        low = str(v).replace("\\", "/").lower()
        cands.add(low)
        cands.add(ITEM_SUFFIX.sub("", low))
    for raw in pats:
        pat = str(raw).strip().replace("\\", "/").lower()
        if not pat:
            continue
        for q in (pat, ITEM_SUFFIX.sub("", pat)):
            if any(c == q or fnmatch.fnmatchcase(c, q) for c in cands):
                return True
    return False


def select(
    ws,
    mlabels: dict,
    rlabels: dict,
    models=None,
    reports=None,
    include=None,
    with_reports=False,
    workspaces=None,
):
    """Narrows the workspace to the models and reports asked for, in place.

    Returns True when a selection was given. A report whose model is left out is still built,
    with the fields it uses shown as that model's.
    """
    models = sel_names(models)
    reports = sel_names(reports)
    spaces = sel_names(workspaces)
    if include:
        inc = read_json(Path(include)) if Path(include).is_file() else None
        if not isinstance(inc, dict):
            raise SelectionError(
                f"Could not read the selection file {include}. It must be a JSON object with "
                '"models" and "reports" lists, as the Scope menu saves it.'
            )
        models += [str(x) for x in (inc.get("models") or [])]
        reports += [str(x) for x in (inc.get("reports") or [])]
        spaces += [str(x) for x in (inc.get("workspaces") or [])]
    if not models and not reports and not spaces:
        return False
    names = [sp[0] for sp in getattr(ws, "spaces", [])]
    for pat in spaces:
        if not any(sel_match([pat], n, n) for n in names):
            warn(
                f"No workspace matches {pat!r}"
                + (f" (the workspaces are {', '.join(names)})" if names else "")
            )

    def in_space(d):
        here = ws.space_of(d) if len(names) > 1 else (names[0] if names else "")
        return bool(spaces) and bool(here) and sel_match(spaces, here, here)

    keep_m = [d for d in ws.models if sel_match(models, *mlabels[d]) or in_space(d)]
    keep_r = [item for item in ws.reports if sel_match(reports, *rlabels[item[0]]) or in_space(item[0])]
    for pat in models:
        if not any(sel_match([pat], *mlabels[d]) for d in ws.models):
            warn(f"No semantic model matches {pat!r}")
    for pat in reports:
        if not any(sel_match([pat], *rlabels[item[0]]) for item in ws.reports):
            warn(f"No report matches {pat!r}")
    if with_reports:  # every report bound to a chosen model
        chosen = set(keep_m)
        have = {item[0] for item in keep_r}
        keep_r += [item for item in ws.reports if item[1] in chosen and item[0] not in have]
        order = {item[0]: i for i, item in enumerate(ws.reports)}
        keep_r.sort(key=lambda item: order[item[0]])
    if not keep_m and not keep_r:
        raise SelectionError(
            "Nothing matched the selection. Run with --list to see the names in this folder."
        )
    ws.models = keep_m
    ws.reports = keep_r
    return True


def list_lines(ws, mlabels: dict, rlabels: dict) -> list:
    """What --list prints: grouped by workspace when the run covers several."""
    spaces = [sp[0] for sp in getattr(ws, "spaces", [])] if len(getattr(ws, "spaces", [])) > 1 else [""]

    def where(d):
        return ws.space_of(d) if spaces != [""] else ""

    out = []
    for sp in spaces:
        ms = [d for d in ws.models if where(d) == sp]
        rs = [item for item in ws.reports if where(item[0]) == sp]
        if sp:
            if not ms and not rs:
                continue
            out.append(f"\n  Workspace {sp}:")
        pad = "  " if sp else ""
        if ms or not sp:
            out.append(f"\n  {pad}{_plural(len(ms), 'semantic model')}:")
        for md in ms:
            label, rel = mlabels[md]
            out.append(f"    {pad}{label}" + (f"   [{rel}]" if rel != label else ""))
        if rs or not sp:
            out.append(f"\n  {pad}{_plural(len(rs), 'report')}:")
        for rd, md, pub in rs:
            label, rel = rlabels[rd]
            bound = mlabels[md][0] if md in mlabels else (pub or {}).get("label", "")
            if md in mlabels and sp and where(md) and where(md) != sp:
                bound += f" (in {where(md)})"
            live = " (published)" if md is None and pub else ""
            loc = f"   [{rel}]" if rel != label else ""
            out.append(f"    {pad}{label}{loc}" + (f"   -> {bound}{live}" if bound else ""))
    out.append(
        "\n  Build a subset with --model NAME, --report NAME, --with-reports"
        + (", --workspace NAME" if spaces != [""] else "")
        + " or --include FILE.\n"
        "  Names may be the display name or the path shown in [ ], and may use * wildcards."
    )
    return out


def default_scope(G, models: list, reports: list, chosen: bool, limit: int = SCOPE_LIMIT) -> dict:
    """What the page shows first. Everything, unless the workspace is large and nothing was
    chosen: then the model most reports use, with its reports."""
    everything = {"models": [m["key"] for m in models], "reports": [r["key"] for r in reports], "all": True}
    size = sum(1 for n in G.nodes.values() if not n.get("auto"))
    if chosen or size <= limit or len(models) <= 1:
        return everything
    counts = defaultdict(int)
    for r in reports:
        if r["model"]:
            counts[r["model"]] += 1
    first = max(models, key=lambda m: (counts[m["key"]], -len(m["name"])))["key"]
    return {"models": [first], "reports": [r["key"] for r in reports if r["model"] == first], "all": False}


# ---------------------------------------------------------------- the overview


def _put_space(it: dict, space) -> None:
    """Notes which workspace an item is in, when the run covers several."""
    if space:
        it["space"] = space
        it["props"].insert(0, ["Workspace", space])


def _external_item(xid: str, e: dict, reports: list) -> dict:
    label = e.get("label") or "Published semantic model"
    unknown = label == "Unknown semantic model"
    server = e.get("server", "")
    where = (
        "The report's semantic model could not be identified"
        if unknown
        else "Analysis Services database this report connects to"
        if server
        else "Published semantic model, not in this folder"
    )
    return {
        "id": xid,
        "kind": "external",
        "key": xid,
        "label": label,
        "icon": "ws_model",
        "server": server,
        "line": "Semantic model not found"
        if unknown
        else "Analysis Services · " + server
        if server
        else "Published · not in this folder",
        "props": [["Where", where]]
        + ([["Server", server]] if server else [])
        + ([["Perspective", e["cube"]]] if e.get("cube") else [])
        + ([["Workspace", e["workspace"]]] if e.get("workspace") else [])
        + ([["Model id", e["id"]]] if e.get("id") and e.get("id") != label else []),
        "reports": reports,
    }


def build_items(G, models: list, reports: list) -> tuple:
    """(items, item edges) for the Workspace view: data sources -> semantic models -> reports."""
    items, edges = [], []
    per_model = defaultdict(lambda: defaultdict(int))
    broken_by_report = defaultdict(int)
    rmeasures = defaultdict(int)
    for n in G.nodes.values():
        k = n.get("mkey")
        if n.get("broken"):
            for rk in n.get("rkeys", []):
                broken_by_report[rk] += 1
            continue
        if n["type"] == "measure" and n.get("sub") == "report":
            for rk in n.get("rkeys", []):
                rmeasures[rk] += 1
            continue
        if not k or n.get("auto") or n.get("external"):
            continue
        t = n["type"]
        if t == "measure" and n.get("sub") == "measure":
            per_model[k]["measures"] += 1
            if not n.get("used"):
                per_model[k]["unused"] += 1
        elif t in ("table", "calcgroup"):
            per_model[k]["tables"] += 1
        elif t == "column":
            per_model[k]["columns"] += 1
            if n.get("sub") == "calculated":
                per_model[k]["calc"] += 1

    def ext_key(r):
        return "X:" + ((r.get("external") or {}).get("label") or "Unknown semantic model")

    reports_of = defaultdict(list)
    for r in reports:
        reports_of[("M:" + r["model"]) if r["model"] else ext_key(r)].append(r["key"])

    for m in models:
        st = per_model[m["key"]]
        modes = sorted(
            {
                (p.get("mode") or "import")
                for t in m["model"].tables.values()
                for p in t.get("partitions", [])
                if p.get("kind") in ("m", "entity", "calculated", "")
            }
        )
        live = getattr(m["model"], "live_ref", None)
        data_cols = st["columns"] - st["calc"]
        it = {
            "id": "M:" + m["key"],
            "kind": "model",
            "key": m["key"],
            "label": m["name"],
            "icon": "ws_model",
            "rel": m["rel"],
            "line": " · ".join(
                [
                    _plural(st["tables"], "table"),
                    _plural(data_cols, "data column"),
                    _plural(st["calc"], "calculated column"),
                    _plural(st["measures"], "measure"),
                ]
            ),
            "counts": [
                ["table", "table", st["tables"], _plural(st["tables"], "table")],
                ["column", "column", data_cols, _plural(data_cols, "data column")],
                ["calccolumn", "column s-calculated", st["calc"], _plural(st["calc"], "calculated column")],
                ["measure", "measure", st["measures"], _plural(st["measures"], "measure")],
            ],
            "props": [
                ["Folder", m["rel"]],
                ["Format", m.get("format") or "not readable"],
                ["Tables", str(st["tables"])],
                ["Columns", f"{st['columns']} ({st['calc']} calculated)"],
                ["Measures", f"{st['measures']} ({st['unused']} not used in any report)"],
                ["Storage mode", ", ".join(modes) or "—"],
            ],
            "unused": st["unused"],
            "reports": reports_of.get("M:" + m["key"], []),
        }
        _put_space(it, m.get("space"))
        if live:  # a pointer to a model, not a definition
            it["line"] = live["typeLabel"] + " · " + (live["database"] or live["server"])
            it["counts"] = []
            it["live"] = live["label"]
            it["props"] = (
                [["Folder", m["rel"]], ["Definition", "Live connection only"]]
                + [["Connection", live["typeLabel"]], ["Server", live["server"] or "—"]]
                + ([["Database", live["database"]]] if live["database"] else [])
                + ([["Perspective", live["cube"]]] if live["cube"] else [])
            )
        if live:
            _put_space(it, m.get("space"))
        items.append(it)

    ext_seen = {}
    for r in reports:
        if r["model"]:
            continue
        xid = ext_key(r)
        if xid not in ext_seen:
            ext_seen[xid] = _external_item(xid, r.get("external") or {}, reports_of.get(xid, []))
            items.append(ext_seen[xid])

    model_name = {m["key"]: m["name"] for m in models}
    for r in reports:
        visuals = sum(1 for p in r["pages"] for v in p["visuals"] if v.get("fields"))
        uses = model_name.get(r["model"]) or (r.get("external") or {}).get("label") or "Unknown"
        n_rm = rmeasures.get(r["key"], 0)
        items.append(
            {
                "id": "R:" + r["key"],
                "kind": "report",
                "key": r["key"],
                "label": r["name"],
                "icon": "nav_report",
                "rel": r["rel"],
                "model": r["model"],
                "external": None if r["model"] else ext_key(r),
                "line": f"{_plural(len(r['pages']), 'page')} · {_plural(visuals, 'visual')}",
                "counts": [
                    ["page", "page", len(r["pages"]), _plural(len(r["pages"]), "page")],
                    ["v_column", "visual", visuals, _plural(visuals, "visual") + " using data"],
                ]
                + ([["rmeasure", "measure", n_rm, _plural(n_rm, "report measure")]] if n_rm else []),
                "missing": broken_by_report.get(r["key"], 0),
                "props": [
                    ["Folder", r["rel"]],
                    ["Format", r.get("format") or ""],
                    ["Semantic model", uses + ("" if r["model"] else " (published)")],
                    ["Pages", str(len(r["pages"]))],
                    ["Data visuals", str(visuals)],
                ]
                + ([["Report measures", str(n_rm)]] if n_rm else []),
            }
        )
        _put_space(items[-1], r.get("space"))
        edges.append([("M:" + r["model"]) if r["model"] else ext_key(r), "R:" + r["key"]])

    by_model_name = defaultdict(list)
    for m in models:
        by_model_name[m["name"].lower()].append(m)

    def find_model(ds):
        """The model in the run a composite model reads: the one in the workspace it names first."""
        cands = by_model_name.get((ds.get("model") or "").lower()) or []
        want = space_key(ds.get("workspace") or "")
        cands = sorted(cands, key=lambda m: not want or space_key(m.get("space") or "") != want)
        return cands[0]["key"] if cands else None

    upstream = defaultdict(list)  # model key -> models it reads
    for n in G.nodes.values():
        if n["type"] != "source" or not (n.get("mkeys") or n.get("mkey")):
            continue
        mkeys = n.get("mkeys") or [n["mkey"]]
        ds = n.get("dataset")
        if ds:  # this "source" is another semantic model: a composite model reads it
            target = find_model(ds)
            src_id = ("M:" + target) if target else ("X:" + ds["model"])
            if not target and src_id not in ext_seen:
                ext_seen[src_id] = {
                    "id": src_id,
                    "kind": "external",
                    "key": src_id,
                    "label": ds["model"],
                    "icon": "ws_model",
                    "line": "Semantic model in another workspace",
                    "props": [["Where", "Read live by another semantic model in this folder"]]
                    + ([["Workspace", ds["workspace"]]] if ds.get("workspace") else []),
                    "reports": [],
                }
                items.append(ext_seen[src_id])
            n["wsid"] = src_id  # where this lands in the workspace
            for k in mkeys:
                if src_id == "M:" + k:
                    continue
                edges.append([src_id, "M:" + k])
                upstream[k].append(ds["model"])
            continue
        items.append(
            {
                "id": n["id"],
                "kind": "source",
                "key": n["id"],
                "label": n["label"],
                "name": n.get("name") or n["label"],
                "icon": n.get("icon", "db"),
                "line": n.get("sub", ""),
                "props": (n.get("detail") or {}).get("props", []),
                "mkeys": mkeys,
            }
        )
        for k in mkeys:
            edges.append([n["id"], "M:" + k])
    for it in items:  # note composite models in their details
        if it["kind"] == "model" and upstream.get(it["key"]):
            names = sorted(set(upstream[it["key"]]))
            it["props"].append(["Reads other models", ", ".join(names)])
            it["line"] += " · reads " + _plural(len(names), "semantic model")
    return items, edges
