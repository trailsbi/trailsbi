# SPDX-License-Identifier: Apache-2.0
"""Builds the lineage graph: sources -> queries -> tables -> columns -> measures -> visuals -> pages."""

from __future__ import annotations

import re
from collections import defaultdict
from contextlib import contextmanager

from .bpa import bpa_evaluate
from .dax import dax_refs
from .icons import visual_icon
from .powerquery import analyze_m
from .report import pretty_visual
from .utils import is_auto_table, warn

SEP = "\u241f"


NS_SEP = "\u241e"
# Node ids carry the key of the semantic model (or the published model) they
# belong to. Set it with id_namespace() while building that model's nodes.
_NS = [""]


@contextmanager
def id_namespace(prefix: str):
    """Node ids made inside the block start with `prefix`."""
    old = _NS[0]
    _NS[0] = prefix
    try:
        yield
    finally:
        _NS[0] = old


def tid(t):
    return "t:" + _NS[0] + t


def cid(t, c):
    return f"c:{_NS[0]}{t}{SEP}{c}"


def mid(t, m):
    return f"m:{_NS[0]}{t}{SEP}{m}"


def qid(n):
    return "q:" + _NS[0] + n


def pid_(n):
    return "p:" + _NS[0] + n


class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}

    def node(self, nid, ntype, label, **kw):
        if nid not in self.nodes:
            self.nodes[nid] = {"id": nid, "type": ntype, "label": label}
        self.nodes[nid].update({k: v for k, v in kw.items() if v not in (None, "", False)})
        return self.nodes[nid]

    def edge(self, a, b, role=""):
        if a != b and a in self.nodes and b in self.nodes:
            self.edges.setdefault((a, b), set()).add(role)


class Resolver:
    def __init__(self, model):
        self.model = model
        self.tables = {n.lower(): n for n in model.tables}
        self.measures, self.cols = {}, {}
        self.col_by_name = defaultdict(list)
        for t in model.tables.values():
            for c in t["columns"]:
                self.cols[(t["name"].lower(), c.lower())] = (t["name"], c)
                self.col_by_name[c.lower()].append((t["name"], c))
            for m, md in t["measures"].items():
                if not md.get("calc_item"):
                    self.measures[m.lower()] = (t["name"], m)

    def table(self, name):
        return self.tables.get((name or "").lower())

    def column(self, table, col):
        tt = self.table(table)
        return self.cols.get((tt.lower(), (col or "").lower())) if tt else None

    def dax(self, expr, home=None):
        qual, bare, tbls = dax_refs(expr)
        deps = set()
        for t, n in qual:
            c = self.column(t, n)
            if c:
                deps.add(cid(*c))
            elif self.table(t) and n.lower() in self.measures:
                deps.add(mid(*self.measures[n.lower()]))
        for n in bare:
            low = n.lower()
            if low in self.measures:
                deps.add(mid(*self.measures[low]))
            elif home and (home.lower(), low) in self.cols:
                deps.add(cid(*self.cols[(home.lower(), low)]))
            elif len(self.col_by_name[low]) == 1:
                deps.add(cid(*self.col_by_name[low][0]))
        for t in tbls:
            tt = self.table(t)
            if tt:
                deps.add(tid(tt))
        return deps


def _build_model_part(G, model):
    R = Resolver(model)
    params = {n: e for n, e in model.expressions.items() if e["is_param"]}
    queries = {n: e for n, e in model.expressions.items() if not e["is_param"]}

    # --- node ids for M references (queries and M-based tables share a namespace)
    m_names = {n: qid(n) for n in queries}
    for tname, t in model.tables.items():
        if any(p["kind"] == "m" for p in t["partitions"]):
            m_names.setdefault(tname, tid(tname))

    param_ids = {}
    for n, e in params.items():
        param_ids[n] = "p:" + n + SEP + (e["value"] or "")
        G.node(
            param_ids[n],
            "query",
            n,
            sub="parameter",
            icon="parameter",
            value=e["value"] or "",
            detail={
                "props": [["Kind", "Parameter"], ["Current value", e["value"] or "(unknown)"]]
                + ([["Group", e["group"]]] if e["group"] else []),
                "code": [{"title": "Definition (M)", "text": e["code"]}],
            },
        )
    m_analysis = {}
    for n, e in queries.items():
        a = analyze_m(e["code"], n, m_names, params)
        m_analysis[qid(n)] = a
        props = [["Kind", "Power Query query (not a model table)"]]
        if e["group"]:
            props.append(["Group", e["group"]])
        if a["nav"]:
            props.append(["Source objects", ", ".join(a["nav"])])
        code = [{"title": "Power Query (M)", "text": e["code"]}]
        if a["native_sql"]:
            code.append({"title": "Native SQL", "text": a["native_sql"]})
        G.node(
            qid(n),
            "query",
            n,
            sub="query",
            icon="query",
            fn=(a["sources"][0]["fn"] if a["sources"] else ""),
            nsteps=len(a["steps"]),
            objects=", ".join(a["nav"]),
            detail={"props": props, "steps": a["steps"], "code": code},
        )

    # --- tables, columns, measures
    rel_by_table = defaultdict(list)
    for r in model.relationships:
        arrow = "↔" if (r["cross"] or "").lower() == "bothdirections" else "→"
        txt = (
            f"{r['from_table']}[{r['from_col']}] ({r['from_card']}) {arrow} "
            f"{r['to_table']}[{r['to_col']}] ({r['to_card']})" + ("" if r["active"] else "  · inactive")
        )
        rel_by_table[r["from_table"]].append(txt)
        rel_by_table[r["to_table"]].append(txt)
    rel_cols = {(r["from_table"], r["from_col"]) for r in model.relationships} | {
        (r["to_table"], r["to_col"]) for r in model.relationships
    }

    table_m, field_param_tables = {}, {}
    for tname, t in model.tables.items():
        parts = t["partitions"]
        kinds = {p["kind"] for p in parts}
        mode = next((p["mode"] for p in parts if p["mode"]), None)
        dax_src = " ".join(p["source"] or "" for p in parts if p["kind"] == "calculated")
        is_field_param = bool(re.search(r"(?i)\bNAMEOF\s*\(", dax_src))
        if t["calc_group"] or "calculationgroup" in kinds:
            sub, kind_label = "calcgroup", "Calculation group"
        elif is_field_param:
            sub, kind_label = "fieldparam", "Field parameter"
        elif "calculated" in kinds:
            sub, kind_label = "calculated", "Calculated table (DAX)"
        elif "entity" in kinds:
            sub, kind_label = "entity", "Direct Lake / entity table"
        elif "m" in kinds:
            sub, kind_label = "m", "Power Query table"
        else:
            sub, kind_label = "", "Table"
        auto = is_auto_table(tname)
        props = [["Type", kind_label]]
        if mode:
            props.append(["Storage mode", mode])
        ncalc = sum(1 for c in t["columns"].values() if c["expr"])
        props.append(["Columns", f"{len(t['columns'])} ({ncalc} calculated)"])
        props.append(["Measures", str(len(t["measures"]))])
        code, steps, nav = [], [], []
        for i, p in enumerate(parts):
            if p["kind"] == "m" and p["source"]:
                a = analyze_m(p["source"], tname, m_names, params)
                if i == 0 or tname not in table_m:
                    table_m[tname] = a
                    steps = a["steps"]
                else:
                    table_m[tname]["sources"] += a["sources"]
                    table_m[tname]["refs"] |= a["refs"]
                    table_m[tname]["params"] |= a["params"]
                nav += a["nav"]
                title = "Power Query (M)" + (f" · partition {p['name']}" if len(parts) > 1 else "")
                code.append({"title": title, "text": p["source"]})
                if a["native_sql"]:
                    code.append({"title": "Native SQL", "text": a["native_sql"]})
            elif p["kind"] == "calculated" and p["source"]:
                code.append({"title": "DAX table expression", "text": p["source"]})
            elif p["kind"] == "entity":
                nav.append(".".join(x for x in (p["schema"], p["entity"]) if x))
        if nav:
            props.append(["Source objects", ", ".join(dict.fromkeys(nav))])
        if t["hidden"]:
            props.append(["Hidden", "Yes"])
        if t["description"]:
            props.append(["Description", t["description"]])
        for r in model.rls:
            if r["table"] == tname:
                code.append({"title": f"Row-level security · {r['role']}", "text": r["expr"]})
        lists = []
        if rel_by_table[tname]:
            lists.append({"title": "Relationships", "items": rel_by_table[tname]})
        G.node(
            tid(tname),
            "table",
            tname,
            sub=sub,
            hidden=t["hidden"],
            auto=auto,
            icon="fieldparam" if sub == "fieldparam" else ("calctable" if sub == "calculated" else "table"),
            mode=(mode or ("DAX table" if sub == "calculated" else "")),
            detail={"props": props, "steps": steps, "code": code, "lists": lists},
        )

        if sub == "fieldparam":
            field_param_tables[tname] = tid(tname)
            continue  # its columns are an implementation detail
        for cname, c in t["columns"].items():
            calc = bool(c["expr"])
            cprops = [["Table", tname], ["Kind", "Calculated column (DAX)" if calc else "Data column"]]
            for label, key in (
                ("Data type", "dataType"),
                ("Source column", "source"),
                ("Sort by", "sortBy"),
                ("Format", "format"),
                ("Display folder", "folder"),
            ):
                if c.get(key):
                    cprops.append([label, c[key]])
            if (tname, cname) in rel_cols:
                cprops.append(["Relationship key", "Yes"])
            if c["hidden"]:
                cprops.append(["Hidden", "Yes"])
            G.node(
                cid(tname, cname),
                "column",
                cname,
                sub="calculated" if calc else "data",
                icon="calccolumn" if calc else "column",
                dtype=c["dataType"] or "",
                table=tname,
                hidden=c["hidden"],
                auto=auto,
                relkey=(tname, cname) in rel_cols,
                detail={"props": cprops, "code": [{"title": "DAX", "text": c["expr"]}] if calc else []},
            )

        for mname, md in t["measures"].items():
            mprops = [["Table", tname], ["Kind", "Calculation item" if md["calc_item"] else "Measure"]]
            for label, key in (("Format", "format"), ("Display folder", "folder")):
                if md.get(key):
                    mprops.append([label, md[key]])
            if md["hidden"]:
                mprops.append(["Hidden", "Yes"])
            mcode = [{"title": "DAX", "text": md["expr"]}]
            if md.get("fsExpr"):
                mcode.append({"title": "Dynamic format string", "text": md["fsExpr"]})
            G.node(
                mid(tname, mname),
                "measure",
                mname,
                table=tname,
                icon="calcitem" if md["calc_item"] else "measure",
                sub="calcitem" if md["calc_item"] else "measure",
                hidden=md["hidden"],
                auto=auto,
                detail={"props": mprops, "code": mcode},
            )

    # --- M edges: sources, parameters, query references
    def wire_m(target, a):
        for s in a["sources"]:
            sid = "s:" + s["key"]
            sprops = [["Connector", s["connector"]]]
            if s["fn"]:
                sprops.append(["Function", s["fn"]])
            for i, v in enumerate(s["args"]):
                sprops.append([("Server / path", "Database / option")[min(i, 1)], v])
            if s.get("dataset"):
                sprops = [["Connector", s["connector"]], ["Semantic model", s["dataset"]["model"]]]
                if s["dataset"]["workspace"]:
                    sprops.append(["Workspace", s["dataset"]["workspace"]])
            G.node(
                sid,
                "source",
                s["label"],
                sub=s["connector"],
                icon=s["icon"],
                name=s["name"],
                detail={"props": sprops},
                dataset=s.get("dataset"),
            )
            G.edge(sid, target, "source")
        for pn in a["params"]:
            G.edge(param_ids.get(pn, pid_(pn)), target, "parameter")
        for rn in a["refs"]:
            G.edge(m_names[rn], target, "reference")

    for qid_, a in m_analysis.items():
        wire_m(qid_, a)
    for tname, a in table_m.items():
        wire_m(tid(tname), a)
    for tname, t in model.tables.items():
        for p in t["partitions"]:
            es = p["expressionSource"]
            if es and qid(es) in G.nodes:
                G.edge(qid(es), tid(tname), "direct lake")

    # --- DAX edges
    for tname, t in model.tables.items():
        for p in t["partitions"]:
            if p["kind"] == "calculated" and p["source"]:
                for dep in R.dax(p["source"], tname):
                    if dep != tid(tname) and not dep.startswith(f"c:{tname}{SEP}"):
                        G.edge(dep, tid(tname), "DAX")
        for cname, c in t["columns"].items():
            me = cid(tname, cname)
            G.edge(tid(tname), me, "contains")
            if c["expr"]:
                for dep in R.dax(c["expr"], tname):
                    G.edge(dep, me, "DAX")
            if c.get("sortBy"):
                sb = R.column(tname, c["sortBy"])
                if sb and cid(*sb) in G.nodes:
                    G.nodes[me]["sortby"] = sb[1]
                    G.nodes[me]["sortbyId"] = cid(*sb)
        for mname, md in t["measures"].items():
            me = mid(tname, mname)
            for dep in R.dax(md["expr"], tname) | R.dax(md.get("fsExpr") or "", tname):
                G.edge(dep, me, "DAX")
            # A measure lives in its home table: deleting the table deletes the measure,
            # so the table owns it in lineage too (a measures-only table is not empty).
            G.edge(tid(tname), me, "contains" if md["calc_item"] else "home")
    return R, field_param_tables, list(param_ids.values())


def _build_report_part(G, rep, model, R, page_rows, field_params):
    """Adds pages, visuals and filters of one report. model/R are None when the
    report uses a published semantic model rather than one in the project."""
    model_loaded = bool(model and model.tables)
    live = getattr(model, "live_ref", None) if model else None
    ext_where = (
        ("In " + (live["database"] or live["server"]) + ", which this semantic model connects to live")
        if live
        else "In the published semantic model the report connects to"
    )
    rkey = rep["key"]
    ext = rep.get("external")

    def field_node(kind, ent, prop):
        if R is None:
            if kind == "level":
                prop, kind = prop[1], "column"
            xid = f"x:{kind}:{_NS[0]}{ent}{SEP}{prop}"
            n = G.node(
                xid,
                kind,
                prop,
                table=ent,
                external=True,
                sub="external",
                icon="measure" if kind == "measure" else "column",
                extmodel=ext["label"],
                detail={
                    "props": [
                        ["Table", ent],
                        ["Kind", kind.title()],
                        ["Semantic model", ext["label"] + " (published)"],
                    ]
                },
            )
            n.setdefault("rkeys", [])
            if rkey not in n["rkeys"]:
                n["rkeys"].append(rkey)
            return xid
        if kind == "level":
            hname, level = prop
            tt = R.table(ent)
            col = None
            if tt:
                for hn, levels in model.tables[tt]["hierarchies"].items():
                    if hn.lower() == (hname or "").lower():
                        col = next((c for ln, c in levels if ln == level), None)
            prop, kind = (col or level), "column"
        tt = R.table(ent)
        if tt and tt in field_params:
            return field_params[tt]
        if kind == "column":
            c = R.column(ent, prop)
            if c:
                return cid(*c)
        if (prop or "").lower() in R.measures:
            return mid(*R.measures[prop.lower()])
        if kind == "measure" and R.table(ent):
            md = model.tables[R.table(ent)]["measures"]
            hit = next((m for m in md if m.lower() == (prop or "").lower()), None)
            if hit:
                return mid(R.table(ent), hit)
        xid = f"x:{kind}:{_NS[0]}{ent}{SEP}{prop}"
        G.node(
            xid,
            kind,
            prop,
            table=ent,
            broken=model_loaded,
            external=not model_loaded,
            icon="measure" if kind == "measure" else "column",
            sub="missing" if model_loaded else "external",
            detail={
                "props": [
                    ["Table", ent],
                    ["Kind", kind.title()],
                    ["Status", "Not found in the semantic model" if model_loaded else ext_where],
                ]
            },
        )
        n = G.nodes[xid]
        n["mkey"] = rep["model"]
        n.setdefault("rkeys", [])
        if rkey not in n["rkeys"]:
            n["rkeys"].append(rkey)
        return xid

    if rep["filters"]:
        rid = f"pg:{rkey}{SEP}__report__"
        G.node(
            rid,
            "page",
            "All pages (report filters)",
            order=-1,
            sub="report",
            icon="allpages",
            detail={"props": [["Kind", "Report-level filters"]]},
        )
        for kind, ent, prop, _role in rep["filters"]:
            G.edge(field_node(kind, ent, prop), rid, "Filter")
    for page in sorted(rep["pages"], key=lambda p: p["order"]):
        pid = f"pg:{rkey}{SEP}{page['id']}"
        plabel = page["name"]
        data_visuals = [v for v in page["visuals"] if v["fields"]]
        pprops = [["Visuals", f"{len(page['visuals'])} ({len(data_visuals)} use data)"]]
        if page["kind"]:
            pprops.append(["Page type", page["kind"]])
        if page["hidden"]:
            pprops.append(["Hidden", "Yes"])
        G.node(
            pid,
            "page",
            plabel,
            order=page["order"],
            hidden=page["hidden"],
            icon="page",
            detail={"props": pprops},
        )
        prow = {
            "id": pid,
            "label": plabel,
            "name": page["name"],
            "rkey": rkey,
            "hidden": page["hidden"],
            "kind": page["kind"],
            "visuals": [],
            "filters": [],
            "other": 0,
            "width": page["width"],
            "height": page["height"],
            "layout": [],
        }
        for kind, ent, prop, _role in sorted(page["filters"], key=str):
            fid = field_node(kind, ent, prop)
            G.edge(fid, pid, "Page filter")
            prow["filters"].append(fid)
        counter = defaultdict(int)
        for v in sorted(page["visuals"], key=lambda v: (v["y"], v["x"])):
            box = {
                "x": round(v["x"], 1),
                "y": round(v["y"], 1),
                "w": round(v["w"], 1),
                "h": round(v["h"], 1),
                "z": v["z"],
                "hidden": v["hidden"],
                "type": pretty_visual(v["type"]),
                "icon": visual_icon(v["type"]),
            }
            if not v["fields"]:
                prow["other"] += 1
                box.update({"id": None, "label": v["title"] or box["type"]})
                prow["layout"].append(box)
                continue
            vtype = pretty_visual(v["type"])
            counter[vtype] += 1
            label = v["title"] or f"{vtype} {counter[vtype]}"
            vid = f"v:{rkey}{SEP}{page['id']}{SEP}{v['id']}"
            fields = []
            for kind, ent, prop, role in sorted(v["fields"], key=str):
                fields.append({"role": role, "id": field_node(kind, ent, prop)})
            G.node(
                vid,
                "visual",
                label,
                page=plabel,
                order=page["order"],
                icon=visual_icon(v["type"]),
                hidden=v["hidden"],
                vtype=vtype,
                pos=v["y"],
                detail={
                    "props": [
                        ["Page", plabel],
                        ["Visual type", vtype],
                        ["Title", v["title"] or "(none)"],
                        ["Position", f"x {v['x']:.0f}, y {v['y']:.0f}"],
                        ["Size", f"{v['w']:.0f} × {v['h']:.0f}"],
                        ["Visual id", v["id"]],
                    ]
                    + ([["Hidden", "Yes"]] if v["hidden"] else []),
                    "fields": fields,
                },
            )
            for f in fields:
                G.edge(f["id"], vid, f["role"])
            G.edge(vid, pid, "on page")
            prow["visuals"].append(vid)
            G.nodes[pid]["nvis"] = len(prow["visuals"])
            box.update({"id": vid, "label": label})
            prow["layout"].append(box)
        page_rows.append(prow)


def _live_source(G, m):
    """The one node a live-connected semantic model contributes: the model it
    points at. There is no TMDL to read, so nothing else about it is known."""
    ref = m["model"].live_ref
    sid = "s:live|" + (ref["server"] + "|" + ref["database"]).lower()
    props = [["Connector", ref["connector"]], ["Server", ref["server"] or "—"]]
    if ref["database"]:
        props.append(["Database", ref["database"]])
    if ref["cube"]:
        props.append(["Perspective", ref["cube"]])
    if ref["workspace"]:
        props.append(["Workspace", ref["workspace"]])
    if ref["connectionType"]:
        props.append(["Connection", ref["typeLabel"]])
    G.node(
        sid,
        "source",
        ref["label"],
        sub=ref["connector"],
        icon=ref["icon"],
        name=ref["database"] or ref["server"],
        live=1,
        detail={
            "props": props,
            "note": f"{m['name']} is a live connection to this model, so its tables, "
            "columns and measures are defined there rather than in the project. "
            "Only the fields the reports ask for can be listed here.",
        },
        dataset=(
            {"model": ref["database"], "workspace": ref["workspace"]}
            if ref["isDataset"] and ref["database"]
            else None
        ),
    )
    n = G.nodes[sid]
    n.setdefault("mkeys", [])
    if m["key"] not in n["mkeys"]:
        n["mkeys"].append(m["key"])
    return sid


def build_graph(models: list, reports: list) -> tuple:
    """models: dicts with key, name, model. reports: dicts from the report
    loaders plus key, name, model (model key or None) and external."""
    G = Graph()
    by_key = {}
    for m in models:
        with id_namespace(m["key"] + NS_SEP):
            before = set(G.nodes)
            R, fps, pids = _build_model_part(G, m["model"])
            by_key[m["key"]] = (m["model"], R, fps)
            m["live_src"] = _live_source(G, m) if getattr(m["model"], "live_ref", None) else None
            for it in getattr(m["model"], "outline", []):
                k, n, tb = it["k"], it["n"], it.get("tb")
                cands = []
                if k == "table":
                    cands = [tid(n)]
                elif k == "column" and tb:
                    cands = [cid(tb, n), tid(tb)]
                elif k == "measure" and tb:
                    cands = [mid(tb, n)]
                elif k == "expression":
                    cands = [qid(n)] + [pid for pid in pids if pid.startswith("p:" + n + SEP)]
                nid = next((c for c in cands if c in G.nodes), None)
                if nid:
                    it["id"] = nid
            m["bpa"] = {}
            m["bpa_skipped"] = set()
            if getattr(m["model"], "bpa_inv", None):
                try:
                    found, skipped = bpa_evaluate(m["model"].bpa_inv)
                except Exception as exc:
                    warn(f"Best practice rules failed on {m['name']}: {exc}")
                    found, skipped = {}, set()
                for _rule, lst in found.items():
                    for f in lst:
                        cand = None
                        if f["kind"] == "table":
                            cand = tid(f["name"])
                        elif f["kind"] == "column" and f["table"]:
                            cand = cid(f["table"], f["name"])
                        elif f["kind"] == "measure" and f["table"]:
                            cand = mid(f["table"], f["name"])
                        elif f["kind"] in ("partition", "tablePermission", "calculationItem") and f["table"]:
                            cand = tid(f["table"])
                        if cand and cand in G.nodes:
                            f["id"] = cand
                m["bpa"], m["bpa_skipped"] = found, skipped
            for nid in set(G.nodes) - before:
                n = G.nodes[nid]
                if n["type"] == "source" or n.get("sub") == "parameter":
                    continue  # data sources and parameters are listed per model in mkeys
                n["mkey"], n["model"] = m["key"], m["name"]
            for pid in pids:  # a parameter belongs to every model that defines it
                n = G.nodes[pid]
                n.setdefault("mkeys", [])
                if m["key"] not in n["mkeys"]:
                    n["mkeys"].append(m["key"])
            for a, b in G.edges:
                na = G.nodes[a]
                if (na["type"] == "source" or na.get("sub") == "parameter") and G.nodes[b].get("mkey") == m[
                    "key"
                ]:
                    na.setdefault("mkeys", [])
                    if m["key"] not in na["mkeys"]:
                        na["mkeys"].append(m["key"])
    page_rows = []
    for rep in reports:
        model, R, fps = by_key.get(rep["model"], (None, None, {}))
        prefix = (rep["model"] + NS_SEP) if rep["model"] else f"ext{NS_SEP}{rep['external']['label']}{NS_SEP}"
        before = set(G.nodes)
        with id_namespace(prefix):
            _build_report_part(G, rep, model, R, page_rows, fps)
        for nid in set(G.nodes) - before:
            n = G.nodes[nid]
            if n.get("mkey") and not n.get("model"):
                n["model"] = next((m["name"] for m in models if m["key"] == n["mkey"]), "")
            if n["type"] in ("visual", "page"):
                n["rkey"], n["report"] = rep["key"], rep["name"]
    # A live-connected model has no tables of its own, so the only fields known
    # about it are the ones the reports ask for. Hang those off its source node
    # so the map still reads source -> field -> visual -> page.
    for m in models:
        sid = m.get("live_src")
        if not sid:
            continue
        for nid, n in G.nodes.items():
            if n.get("external") and n.get("mkey") == m["key"] and n["type"] in ("column", "measure"):
                G.edge(sid, nid, "live connection")
    for (a, _b), roles in G.edges.items():
        if G.nodes[a]["type"] in ("column", "measure") and any("filter" in r.lower() for r in roles):
            G.nodes[a]["filtered"] = True
    # Some edges come from sets, whose order changes between runs. A fixed order
    # makes the same project give the same page every time.
    G.edges = dict(sorted(G.edges.items()))
    return G, page_rows


def downstream_counts(G: Graph) -> None:
    """Per node: what depends on it (by type, plus totals) and how much feeds it."""
    out, inn = defaultdict(list), defaultdict(list)
    for a, b in G.edges:
        out[a].append(b)
        inn[b].append(a)
    order, seen, stack = [], set(), []
    for nid in G.nodes:
        if nid in seen:
            continue
        stack.append((nid, False))
        while stack:
            cur, done = stack.pop()
            if done:
                order.append(cur)
                continue
            if cur in seen:
                continue
            seen.add(cur)
            stack.append((cur, True))
            for nxt in out.get(cur, ()):
                if nxt not in seen:
                    stack.append((nxt, False))
    desc = {}
    for nid in order:  # children are finished first
        s = set()
        for nxt in out.get(nid, ()):
            s.add(nxt)
            s |= desc.get(nxt, set())
        desc[nid] = s
    anc = {}
    for nid in reversed(order):  # parents are finished first
        a = set()
        for prev in inn.get(nid, ()):
            a.add(prev)
            a |= anc.get(prev, set())
        anc[nid] = a
    for nid, n in G.nodes.items():
        c = defaultdict(int)
        for d in desc.get(nid, ()):
            c[G.nodes[d]["type"]] += 1
        n["down"] = [c["column"], c["measure"], c["visual"], c["query"], c["table"]]
        n["nup"] = len(anc.get(nid, ()))
        n["ndown"] = len(desc.get(nid, ()))
