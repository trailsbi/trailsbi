# SPDX-License-Identifier: Apache-2.0
"""Loads a semantic model (TMDL folder or model.bim) into a Model, plus the outline and
diagram data the Model view shows."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .bpa import bpa_inventory_bim, bpa_inventory_tmdl
from .tmdl import parse_tmdl_text, split_col_ref
from .utils import as_text, is_auto_table, read_json, read_text, truthy, unquote, warn


class Model:
    def __init__(self):
        self.tables = {}
        self.expressions = {}
        self.relationships = []
        self.rls = []
        self.outline = []
        self.bpa_inv = None
        self.live_ref = None  # set when the folder only points at a live model

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = {
                "name": name,
                "columns": {},
                "measures": {},
                "partitions": [],
                "hierarchies": {},
                "hidden": False,
                "description": "",
                "calc_group": False,
            }
        return self.tables[name]

    def add_expression(self, name, code, group=None, description=None):
        code = code or ""
        is_param = bool(re.search(r"IsParameterQuery\s*=\s*true", code, re.I))
        value = None
        if is_param:
            mm = re.match(r'\s*("(?:[^"]|"")*"|\S+)\s+meta\b', code)
            if mm:
                raw = mm.group(1)
                value = raw[1:-1].replace('""', '"') if raw.startswith('"') else raw
        self.expressions[name] = {
            "name": name,
            "code": code,
            "is_param": is_param,
            "value": value,
            "group": group,
            "description": description,
        }

    def add_relationship(
        self, ft, fc, tt, tc, active=True, cross="oneDirection", from_card="many", to_card="one"
    ):
        self.relationships.append(
            {
                "from_table": ft,
                "from_col": fc,
                "to_table": tt,
                "to_col": tc,
                "active": active,
                "cross": cross or "oneDirection",
                "from_card": from_card or "many",
                "to_card": to_card or "one",
            }
        )


def _ingest_tmdl(objs, model):
    for o in objs:
        kw, props = o["kw"], o["props"]
        if kw == "table":
            _ingest_tmdl_table(o, model)
        elif kw == "expression":
            model.add_expression(o["name"], o["expr"], props.get("queryGroup"))
        elif kw == "relationship":
            ft, fc = split_col_ref(props.get("fromColumn", ""))
            tt, tc = split_col_ref(props.get("toColumn", ""))
            if ft and tt:
                model.add_relationship(
                    ft,
                    fc,
                    tt,
                    tc,
                    active=str(props.get("isActive", "true")).lower() != "false",
                    cross=props.get("crossFilteringBehavior"),
                    from_card=props.get("fromCardinality"),
                    to_card=props.get("toCardinality"),
                )
        elif kw == "role":
            for ch in o["children"]:
                if ch["kw"] == "tablePermission" and ch["expr"]:
                    model.rls.append({"role": o["name"], "table": ch["name"], "expr": ch["expr"]})
        elif kw in ("model", "database"):
            _ingest_tmdl(o["children"], model)


def _ingest_tmdl_table(o, model):
    t = model.table(o["name"])
    p = o["props"]
    t["hidden"] = truthy(p.get("isHidden"))
    if "calculationGroup" in p:
        t["calc_group"] = True
    for ch in o["children"]:
        k, cp = ch["kw"], ch["props"]
        if k == "column":
            t["columns"][ch["name"]] = {
                "name": ch["name"],
                "expr": ch["expr"],
                "source": unquote(cp.get("sourceColumn") or "") or None,
                "dataType": cp.get("dataType"),
                "hidden": truthy(cp.get("isHidden")),
                "sortBy": unquote(cp["sortByColumn"]) if cp.get("sortByColumn") else None,
                "folder": unquote(cp.get("displayFolder") or ""),
                "format": cp.get("formatString"),
            }
        elif k in ("measure", "calculationItem"):
            if k == "calculationItem":
                t["calc_group"] = True
            fsd = cp.get("formatStringDefinition")
            t["measures"][ch["name"]] = {
                "name": ch["name"],
                "expr": ch["expr"] or "",
                "format": cp.get("formatString"),
                "fsExpr": fsd if isinstance(fsd, str) else None,
                "folder": unquote(cp.get("displayFolder") or ""),
                "hidden": truthy(cp.get("isHidden")),
                "calc_item": k == "calculationItem",
            }
        elif k == "partition":
            src = cp.get("source")
            t["partitions"].append(
                {
                    "name": ch["name"],
                    "kind": (ch["rest"] or cp.get("type") or "").strip().lower(),
                    "mode": cp.get("mode"),
                    "source": src if isinstance(src, str) else "",
                    "entity": unquote(cp.get("entityName") or ""),
                    "schema": unquote(cp.get("schemaName") or ""),
                    "expressionSource": unquote(cp.get("expressionSource") or ""),
                }
            )
        elif k == "hierarchy":
            t["hierarchies"][ch["name"]] = [
                (lv["name"], unquote(lv["props"].get("column", "")))
                for lv in ch["children"]
                if lv["kw"] == "level"
            ]


def load_tmdl_folder(def_dir, model):
    for f in sorted(def_dir.rglob("*.tmdl")):
        if "cultures" in (part.lower() for part in f.parts):
            continue
        try:
            _ingest_tmdl(parse_tmdl_text(read_text(f)), model)
        except Exception as exc:  # keep going on odd files
            warn(f"Skipped {f.name}: {exc}")


def load_bim(path, model):
    data = read_json(path) or {}
    m = data.get("model", data)
    for tj in m.get("tables", []):
        t = model.table(tj["name"])
        t["hidden"] = bool(tj.get("isHidden"))
        t["description"] = as_text(tj.get("description")) or ""
        cg = tj.get("calculationGroup")
        if cg:
            t["calc_group"] = True
            for it in cg.get("calculationItems", []):
                t["measures"][it["name"]] = {
                    "name": it["name"],
                    "expr": as_text(it.get("expression")) or "",
                    "format": None,
                    "fsExpr": None,
                    "folder": "",
                    "hidden": False,
                    "calc_item": True,
                }
        for c in tj.get("columns", []):
            ctype = c.get("type", "data")
            if ctype == "rowNumber":
                continue
            t["columns"][c["name"]] = {
                "name": c["name"],
                "expr": as_text(c.get("expression")) if ctype == "calculated" else None,
                "source": c.get("sourceColumn"),
                "dataType": c.get("dataType"),
                "hidden": bool(c.get("isHidden")),
                "sortBy": c.get("sortByColumn"),
                "folder": c.get("displayFolder") or "",
                "format": c.get("formatString"),
            }
        for ms in tj.get("measures", []):
            fsd = (ms.get("formatStringDefinition") or {}).get("expression")
            t["measures"][ms["name"]] = {
                "name": ms["name"],
                "expr": as_text(ms.get("expression")) or "",
                "format": ms.get("formatString"),
                "fsExpr": as_text(fsd),
                "folder": ms.get("displayFolder") or "",
                "hidden": bool(ms.get("isHidden")),
                "calc_item": False,
            }
        for pt in tj.get("partitions", []):
            s = pt.get("source") or {}
            t["partitions"].append(
                {
                    "name": pt.get("name", ""),
                    "kind": (s.get("type") or "").lower(),
                    "mode": pt.get("mode"),
                    "source": as_text(s.get("expression") or s.get("query")) or "",
                    "entity": s.get("entityName") or "",
                    "schema": s.get("schemaName") or "",
                    "expressionSource": s.get("expressionSource") or "",
                }
            )
        for h in tj.get("hierarchies", []):
            t["hierarchies"][h["name"]] = [(lv.get("name"), lv.get("column")) for lv in h.get("levels", [])]
    for e in m.get("expressions", []):
        model.add_expression(
            e["name"], as_text(e.get("expression")), e.get("queryGroup"), as_text(e.get("description"))
        )
    for r in m.get("relationships", []):
        model.add_relationship(
            r.get("fromTable"),
            r.get("fromColumn"),
            r.get("toTable"),
            r.get("toColumn"),
            active=r.get("isActive", True),
            cross=r.get("crossFilteringBehavior"),
            from_card=r.get("fromCardinality"),
            to_card=r.get("toCardinality"),
        )
    for role in m.get("roles", []):
        for tp in role.get("tablePermissions", []):
            if tp.get("filterExpression"):
                model.rls.append(
                    {
                        "role": role.get("name"),
                        "table": tp.get("name"),
                        "expr": as_text(tp.get("filterExpression")),
                    }
                )


# ---------------------------------------------------------------------------
# Model outline: every object in the definition, in TMDL order, kept light.
# Each entry: k (object type), n (name), d (depth), t (type label),
# h (hidden), key, x (expression), l (DAX / M), tb (owning table).
# ---------------------------------------------------------------------------
OUTLINE_SKIP_CHILDREN = {"cultureInfo"}  # linguistic metadata is huge and not model structure
OUTLINE_TOP_ORDER = [
    "database",
    "model",
    "tables",
    "relationships",
    "roles",
    "cultures",
    "perspectives",
    "expressions",
    "dataSources",
    "functions",
]


def _truthy_prop(props, key):
    v = props.get(key)
    return v is True or (isinstance(v, str) and v.strip().lower() == "true")


def _outline_label(o, table=None):
    kw, props, rest = o["kw"], o["props"], (o.get("rest") or "")
    if kw == "table":
        parts = [c for c in o["children"] if c["kw"] == "partition"]
        kinds = {(c.get("rest") or "").lower() for c in parts}
        dax = " ".join(
            (c["props"].get("source") or "") for c in parts if (c.get("rest") or "").lower() == "calculated"
        )
        if props.get("calculationGroup") or any(c["kw"] == "calculationItem" for c in o["children"]):
            return "calculation group"
        if re.search(r"(?i)\bNAMEOF\s*\(", dax):
            return "field parameter"
        if "calculated" in kinds:
            return "calculated table"
        mode = next((c["props"].get("mode") for c in parts if c["props"].get("mode")), "")
        return "table" + (" · " + str(mode) if mode else "")
    if kw == "column":
        dt = props.get("dataType") or ""
        dt = dt[:1].upper() + dt[1:] if isinstance(dt, str) else ""
        return ("calculated column" if o.get("expr") else "column") + (" · " + dt if dt else "")
    if kw == "partition":
        return "partition · " + (rest or "?") + (" · " + str(props.get("mode")) if props.get("mode") else "")
    if kw == "expression":
        return (
            "parameter"
            if re.search(r"IsParameterQuery\s*=\s*true", o.get("expr") or "", re.I)
            else "expression"
        )
    if kw == "relationship":
        return "relationship" + ("" if props.get("isActive") not in ("false", False) else " · inactive")
    if kw == "role":
        return "role · " + str(props.get("modelPermission") or "")
    if kw == "level":
        return "level · " + str(props.get("column") or "")
    return re.sub(r"(?<!^)([A-Z])", r" \1", kw).lower()


def _outline_walk(o, depth, out, table=None, auto=False):
    kw = o["kw"]
    name = o["name"]
    expr, lang = o.get("expr"), None
    if expr and kw in ("measure", "calculationItem", "tablePermission", "function", "column"):
        lang = "DAX"
    elif kw == "expression" and expr:
        lang = "M"
    elif kw == "partition":
        expr = o["props"].get("source") or o["props"].get("expression") or None
        lang = "DAX" if (o.get("rest") or "").lower() == "calculated" else ("M" if expr else None)
    elif kw == "annotation":
        expr = None
    if kw == "relationship":
        fc, tc = o["props"].get("fromColumn") or "", o["props"].get("toColumn") or ""
        if fc and tc:
            name = f"{fc} → {tc}".replace("'", "")
    item = {"k": kw, "n": name, "d": depth, "t": _outline_label(o, table)}
    # Power BI's automatic date tables, and the relationships into them
    if kw == "table":
        auto = is_auto_table(o["name"])
    elif kw == "relationship":
        sides = [
            split_col_ref(str(o["props"].get(p) or ""))[0] or unquote(str(o["props"].get(q) or ""))
            for p, q in (("fromColumn", "fromTable"), ("toColumn", "toTable"))
        ]
        auto = any(is_auto_table(x) for x in sides)
    if auto:
        item["auto"] = 1
    if _truthy_prop(o["props"], "isHidden"):
        item["h"] = 1
    if _truthy_prop(o["props"], "isKey"):
        item["key"] = 1
    if kw == "annotation" and o.get("expr"):
        item["t"] = "annotation · " + str(o["expr"])[:60]
    if expr and lang:
        item["x"], item["l"] = str(expr), lang
    if table and kw in ("column", "measure", "hierarchy", "partition", "calculationItem"):
        item["tb"] = table
    out.append(item)
    if kw in OUTLINE_SKIP_CHILDREN:
        return
    child_table = o["name"] if kw == "table" else table
    for c in o["children"]:
        _outline_walk(c, depth + 1, out, child_table, auto)


def outline_tmdl(def_dir):
    files = sorted(def_dir.rglob("*.tmdl"))
    refs = defaultdict(list)  # ref order from model.tmdl
    model_file = def_dir / "model.tmdl"
    if model_file.exists():
        for ln in read_text(model_file).splitlines():
            mm = re.match(r"\s*ref\s+(table|role|culture|perspective)\s+(.+?)\s*$", ln)
            if mm:
                refs[mm.group(1)].append(unquote(mm.group(2)))

    def group_of(f):
        rel = f.relative_to(def_dir).parts
        if len(rel) > 1:
            return rel[0].lower()
        stem = f.stem.lower()
        return {"datasources": "dataSources"}.get(stem, stem)

    by_group = defaultdict(list)
    for f in files:
        by_group[group_of(f)].append(f)

    def ordered(folder, kind):
        fs = by_group.get(folder, [])
        order = {n.lower(): i for i, n in enumerate(refs.get(kind, []))}
        return sorted(fs, key=lambda f: (order.get(f.stem.lower(), 10**6), f.stem.lower()))

    sequence = []
    for g in OUTLINE_TOP_ORDER:
        if g == "tables":
            sequence += ordered("tables", "table")
        elif g == "roles":
            sequence += ordered("roles", "role")
        elif g == "cultures":
            sequence += ordered("cultures", "culture")
        elif g == "perspectives":
            sequence += ordered("perspectives", "perspective")
        else:
            sequence += by_group.get(g, []) + by_group.get(g.lower(), [])
    seen = set(sequence)
    sequence += [f for f in files if f not in seen]

    out = []
    for f in dict.fromkeys(sequence):
        try:
            text = read_text(f)
            if group_of(f) == "cultures":  # keep only the culture declaration
                first = next((ln for ln in text.splitlines() if ln.strip()), "")
                text = first
            for o in parse_tmdl_text(text):
                _outline_walk(o, 0, out)
        except Exception as exc:
            warn(f"Outline skipped {f.name}: {exc}")
    return out


def outline_bim(path):
    data = read_json(path) or {}
    mdl = data.get("model") or {}
    out = [
        {"k": "database", "n": data.get("name") or path.parent.name, "d": 0, "t": "database"},
        {"k": "model", "n": mdl.get("name") or "Model", "d": 0, "t": "model"},
    ]
    for t in mdl.get("tables") or []:
        tname = t.get("name", "")
        first = len(out)  # stamped auto below if this is a date table
        parts = t.get("partitions") or []
        src_types = {(p.get("source") or {}).get("type", "") for p in parts}
        label = "calculated table" if "calculated" in src_types else "table"
        if t.get("calculationGroup"):
            label = "calculation group"
        out.append({"k": "table", "n": tname, "d": 0, "t": label, **({"h": 1} if t.get("isHidden") else {})})
        for c in t.get("columns") or []:
            e = as_text(c.get("expression"))
            dt = c.get("dataType") or ""
            it = {
                "k": "column",
                "n": c.get("name", ""),
                "d": 1,
                "tb": tname,
                "t": ("calculated column" if e or c.get("type") == "calculated" else "column")
                + (" · " + dt[:1].upper() + dt[1:] if dt else ""),
            }
            if c.get("isHidden"):
                it["h"] = 1
            if c.get("isKey"):
                it["key"] = 1
            if e:
                it["x"], it["l"] = e, "DAX"
            out.append(it)
        for ms in t.get("measures") or []:
            it = {"k": "measure", "n": ms.get("name", ""), "d": 1, "tb": tname, "t": "measure"}
            if ms.get("isHidden"):
                it["h"] = 1
            e = as_text(ms.get("expression"))
            if e:
                it["x"], it["l"] = e, "DAX"
            out.append(it)
        for hname in t.get("hierarchies") or []:
            out.append({"k": "hierarchy", "n": hname.get("name", ""), "d": 1, "tb": tname, "t": "hierarchy"})
            for lv in hname.get("levels") or []:
                out.append(
                    {
                        "k": "level",
                        "n": lv.get("name", ""),
                        "d": 2,
                        "t": "level · " + str(lv.get("column", "")),
                    }
                )
        for ci in (t.get("calculationGroup") or {}).get("calculationItems") or []:
            it = {
                "k": "calculationItem",
                "n": ci.get("name", ""),
                "d": 1,
                "tb": tname,
                "t": "calculation item",
            }
            e = as_text(ci.get("expression"))
            if e:
                it["x"], it["l"] = e, "DAX"
            out.append(it)
        for p in parts:
            src = p.get("source") or {}
            e = as_text(src.get("expression") or src.get("query"))
            it = {
                "k": "partition",
                "n": p.get("name", ""),
                "d": 1,
                "tb": tname,
                "t": "partition · " + (src.get("type") or "?") + (" · " + p["mode"] if p.get("mode") else ""),
            }
            if e:
                it["x"], it["l"] = e, ("DAX" if src.get("type") == "calculated" else "M")
            out.append(it)
        if is_auto_table(tname):
            for it in out[first:]:
                it["auto"] = 1
    for r in mdl.get("relationships") or []:
        name = f"{r.get('fromTable')}.{r.get('fromColumn')} → {r.get('toTable')}.{r.get('toColumn')}"
        it = {
            "k": "relationship",
            "n": name,
            "d": 0,
            "t": "relationship" + (" · inactive" if r.get("isActive") is False else ""),
        }
        if is_auto_table(r.get("fromTable") or "") or is_auto_table(r.get("toTable") or ""):
            it["auto"] = 1
        out.append(it)
    for ro in mdl.get("roles") or []:
        out.append(
            {
                "k": "role",
                "n": ro.get("name", ""),
                "d": 0,
                "t": "role · " + str(ro.get("modelPermission", "")),
            }
        )
        for tp in ro.get("tablePermissions") or []:
            it = {"k": "tablePermission", "n": tp.get("name", ""), "d": 1, "t": "table permission"}
            e = as_text(tp.get("filterExpression"))
            if e:
                it["x"], it["l"] = e, "DAX"
            out.append(it)
    for cu in mdl.get("cultures") or []:
        out.append({"k": "cultureInfo", "n": cu.get("name", ""), "d": 0, "t": "culture"})
    for pe in mdl.get("perspectives") or []:
        out.append({"k": "perspective", "n": pe.get("name", ""), "d": 0, "t": "perspective"})
    for ex in mdl.get("expressions") or []:
        e = as_text(ex.get("expression"))
        is_param = bool(re.search(r"IsParameterQuery\s*=\s*true", e or "", re.I))
        it = {
            "k": "expression",
            "n": ex.get("name", ""),
            "d": 0,
            "t": "parameter" if is_param else "expression",
        }
        if e:
            it["x"], it["l"] = e, "M"
        out.append(it)
    for ds in mdl.get("dataSources") or []:
        out.append(
            {
                "k": "dataSource",
                "n": ds.get("name", ""),
                "d": 0,
                "t": "data source · " + str(ds.get("type", "")),
            }
        )
    return out


def model_diagram(inv: dict | None) -> dict | None:
    """Compact tables, fields and relationships for the model diagram."""
    if not inv:
        return None
    tables = []
    for t in inv["tables"]:
        kind = "calc" if t["isCalc"] else "table"
        if t["calcGroup"]:
            kind = "calcgroup"
        elif t["isCalc"] and any(re.search(r"(?i)\bNAMEOF\s*\(", p["query"] or "") for p in t["partitions"]):
            kind = "fieldparam"
        tables.append(
            {
                "n": t["name"],
                "h": 1 if t["hidden"] else 0,
                "k": kind,
                "auto": 1 if is_auto_table(t["name"]) else 0,
                "cols": [
                    {
                        "n": c["name"],
                        "dt": c["dataType"],
                        "h": 1 if c["hidden"] else 0,
                        "key": 1 if c["isKey"] else 0,
                        "calc": 1 if c["type"] == "calculated" else 0,
                        "d": (c["desc"] or "")[:200],
                    }
                    for c in t["columns"]
                ],
                "ms": [
                    {"n": m["name"], "h": 1 if m["hidden"] else 0, "d": (m["desc"] or "")[:200]}
                    for m in t["measures"]
                ],
                "d": (t["desc"] or "")[:200],
            }
        )
    rels = [
        {
            "f": [r["fromTable"], r["fromColumn"]],
            "t": [r["toTable"], r["toColumn"]],
            "fc": r["fromCard"],
            "tc": r["toCard"],
            "both": 1 if r["both"] else 0,
            "active": 1 if r["active"] else 0,
            "auto": 1 if (is_auto_table(r["fromTable"]) or is_auto_table(r["toTable"])) else 0,
        }
        for r in inv["relationships"]
        if r["fromTable"] and r["toTable"]
    ]
    return {"tables": tables, "rels": rels}


def connection_parts(conn: str) -> dict:
    """ "Data Source=x;Initial Catalog=y" -> {"data source": "x", "initial catalog": "y"}."""
    return {
        k.strip().lower(): v.strip()
        for k, _, v in (x.partition("=") for x in (conn or "").split(";") if "=" in x)
    }


_LIVE_TYPE_LABELS = {
    "analysisservicesdatabaselive": "Analysis Services database (live)",
    "analysisservicesdatabase": "Analysis Services database",
    "powerbisemanticmodellive": "Power BI semantic model (live)",
    "powerbidatasetlive": "Power BI semantic model (live)",
    "powerbiservicelive": "Power BI semantic model (live)",
}


def read_model_reference(model_dir):
    """A .SemanticModel folder can be a pointer at a model that lives elsewhere -
    an Analysis Services cube, or a published semantic model - instead of a
    definition of its own. Then there is no TMDL and no model.bim, only
    modelReference.json holding the connection string."""
    ref = None
    for name in ("modelReference.json", "definition/modelReference.json", "definition.pbidataset"):
        p = model_dir / name
        if p.is_file():
            ref = read_json(p)
            if isinstance(ref, dict):
                break
            ref = None
    if not ref:
        return None
    conn = ref.get("connectionString") or ref.get("connection") or ""
    parts = connection_parts(conn)
    server = parts.get("data source") or parts.get("datasource") or parts.get("server") or ""
    database = parts.get("initial catalog") or parts.get("catalog") or parts.get("database") or ""
    cube = parts.get("cube") or parts.get("perspective") or ""
    ctype = (ref.get("connectionType") or "").strip()
    if not (server or database):
        return None
    low = server.lower()
    scheme = low.split("://", 1)[0] if "://" in low else ""
    # A powerbi:// server is another semantic model; everything else is an AS engine.
    if scheme in ("powerbi", "pbiazure", "powerbi-df", "pbidedicated"):
        connector, icon = "Power BI semantic model", "ws_model"
        host = re.sub(r"(?i)^[a-z0-9-]+://[^/]+(/v1\.0/myorg)?/?", "", server).strip("/")
    elif scheme == "asazure":
        connector, icon, host = "Azure Analysis Services", "cloud", ""
    else:
        connector, icon, host = "Analysis Services", "db", ""
    label = connector + (": " + database if database else (": " + server if server else ""))
    return {
        "server": server,
        "database": database,
        "cube": cube,
        "connectionType": ctype,
        "connector": connector,
        "icon": icon,
        "workspace": host,
        "label": label,
        "typeLabel": _LIVE_TYPE_LABELS.get(ctype.lower(), ctype or connector),
        "isDataset": scheme in ("powerbi", "pbiazure", "powerbi-df", "pbidedicated"),
        "connectionString": conn,
    }


def load_model_dir(model_dir: Path, model: Model) -> str | None:
    tmdl = model_dir / "definition"
    bim = model_dir / "model.bim"
    if tmdl.is_dir() and next(tmdl.rglob("*.tmdl"), None) is not None:
        load_tmdl_folder(tmdl, model)
        try:
            model.outline = outline_tmdl(tmdl)
        except Exception as exc:
            warn(f"Could not build the model outline: {exc}")
        try:
            model.bpa_inv = bpa_inventory_tmdl(tmdl)
        except Exception as exc:
            warn(f"Best practice rules could not read this model: {exc}")
        return "TMDL"
    if bim.exists():
        load_bim(bim, model)
        try:
            model.outline = outline_bim(bim)
        except Exception as exc:
            warn(f"Could not build the model outline: {exc}")
        try:
            model.bpa_inv = bpa_inventory_bim(bim)
        except Exception as exc:
            warn(f"Best practice rules could not read this model: {exc}")
        return "model.bim (TMSL)"
    ref = read_model_reference(model_dir)
    if ref:
        model.live_ref = ref
        where = ref["database"] or ref["server"]
        print(
            f"      live connection to {ref['connector']}: {where}"
            + (f" (perspective {ref['cube']})" if ref["cube"] else "")
        )
        return "live connection"
    warn(f"No TMDL folder, model.bim or modelReference.json found in {model_dir}")
    return None
