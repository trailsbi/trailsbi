# SPDX-License-Identifier: Apache-2.0
"""AI readiness checks: how well Copilot and data agents will understand the model.

The checks draw on Tabular Editor's "AI readiness and best practices for
semantic models" and Microsoft's Copilot readiness checklist. Everything is
read from the project files: TMDL or model.bim, definition.pbism, the Copilot/
folder that "Prep data for AI" writes in a PBIP project, and the report.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

from .bpa import _on_auto_date, _refs
from .graph import NS_SEP, Graph, cid, id_namespace, mid, tid
from .utils import is_auto_table, read_json, read_text, warn

AI_CATEGORIES = ["Foundation", "Naming", "Descriptions", "Prep data for AI", "What AI can see"]

_FILLER_WORDS = {"the", "a", "an", "of", "for", "in", "is", "this"}

AI_RULES = [
    (
        "AI_QNA_DISABLED",
        "Foundation",
        3,
        "Q&A must be enabled for Copilot",
        "Copilot needs Q&A enabled on the semantic model (settings.qnaEnabled in definition.pbism).",
    ),
    (
        "AI_NO_MEASURES",
        "Foundation",
        3,
        "Model has no explicit measures",
        "Copilot and data agents can't use implicit measures; every metric they should answer needs an explicit DAX measure.",
    ),
    (
        "AI_IMPLICIT_ONLY_COLUMNS",
        "Foundation",
        2,
        "Numeric columns with no explicit measure",
        "These visible numeric columns summarize automatically but no measure uses them, so AI can only reach them through ad hoc DAX.",
    ),
    (
        "AI_REPORT_MEASURES",
        "Foundation",
        2,
        "Measures defined only in reports",
        "Report-level measures don't exist in the semantic model, so Copilot and data agents can't query them. Move them into the model.",
    ),
    (
        "AI_SNOWFLAKE",
        "Foundation",
        2,
        "Tables on both sides of relationships (snowflake)",
        "A star schema is what the language model expects; snowflaked dimensions make it search further for the right field.",
    ),
    (
        "AI_AMBIGUOUS_RELATIONSHIPS",
        "Foundation",
        2,
        "Bi-directional or many-to-many relationships",
        "These can create ambiguous filter paths that lead AI to wrong totals. Keep them only where needed.",
    ),
    (
        "AI_NO_DATE_TABLE",
        "Foundation",
        2,
        "No marked date table",
        "Time questions are answered most reliably with a date table marked as such, with a date key column.",
    ),
    (
        "AI_NO_DEFAULT_LABEL",
        "Foundation",
        1,
        "Dimension tables with no default label column",
        "Set Is Default Label on the column that names each row (for example Product Name) so Copilot knows how to label the table.",
    ),
    (
        "AI_DATE_NO_HIERARCHY",
        "Foundation",
        1,
        "Date table without a hierarchy",
        "A Year > Quarter > Month > Day hierarchy helps AI drill through time consistently.",
    ),
    (
        "AI_SUMMARIZED_IDENTIFIERS",
        "Foundation",
        2,
        "Identifier columns that will be summed",
        "IDs, keys, codes, years and month numbers should have Summarize By set to None so AI doesn't add them up.",
    ),
    (
        "AI_TECHNICAL_NAMES",
        "Naming",
        2,
        "Technical names on visible objects",
        "Copilot reads names literally. snake_case, CamelCase, ALL CAPS and prefixes like dim or fact read as code, not business terms.",
    ),
    (
        "AI_ABBREVIATIONS",
        "Naming",
        1,
        "Abbreviations in visible names",
        "Spell out abbreviations such as Amt, Qty or Cust; the language model can't assume what they mean in your business.",
    ),
    (
        "AI_DUPLICATE_COLUMN_NAMES",
        "Naming",
        2,
        "Same column name in several tables",
        "Visible columns sharing a name make it hard for AI to pick the right one. Rename them, hide one, or describe the difference.",
    ),
    (
        "AI_INCONSISTENT_TI_NAMES",
        "Naming",
        1,
        "Time-intelligence names used both as prefix and suffix",
        "Put YTD, MTD, PY and similar in the same position everywhere (for example always a suffix) so searches for them find every variant.",
    ),
    (
        "AI_NO_MODEL_DESCRIPTION",
        "Descriptions",
        1,
        "Model has no description",
        "A model-level description sets scope and conventions for any agent reading the model.",
    ),
    (
        "AI_TABLE_NO_DESCRIPTION",
        "Descriptions",
        2,
        "Visible tables with no description",
        "Say what each table represents and its grain.",
    ),
    (
        "AI_MEASURE_NO_DESCRIPTION",
        "Descriptions",
        2,
        "Visible measures with no description",
        "Describe what the measure means and when to use it, especially where similar measures exist.",
    ),
    (
        "AI_AMBIGUOUS_NO_DESCRIPTION",
        "Descriptions",
        2,
        "Ambiguous columns with no description",
        "Columns whose names appear in more than one table need a description that tells them apart.",
    ),
    (
        "AI_DESCRIPTION_TOO_LONG",
        "Descriptions",
        2,
        "Descriptions longer than 200 characters",
        "Copilot reads only the first 200 characters. Put usage, disambiguation and units first.",
    ),
    (
        "AI_DESCRIPTION_RESTATES_NAME",
        "Descriptions",
        1,
        "Descriptions that only restate the name",
        "A description should add what the name and DAX don't already say.",
    ),
    (
        "AI_CALC_GROUP_NO_DESCRIPTION",
        "Descriptions",
        2,
        "Calculation groups with no description",
        "Calculation items aren't surfaced to Copilot; the calculation group's description should list the items and how to use them.",
    ),
    (
        "AI_DAX_NO_COMMENTS",
        "Descriptions",
        1,
        "Long measures with no comments",
        "Inline comments explain non-obvious logic to agents reading or editing the DAX.",
    ),
    (
        "AI_NO_INSTRUCTIONS",
        "Prep data for AI",
        2,
        "No AI instructions",
        "AI instructions route ambiguous terms to the right measures and set time, polarity and clarification rules (Copilot/Instructions/instructions.md).",
    ),
    (
        "AI_INSTRUCTIONS_TOO_LONG",
        "Prep data for AI",
        3,
        "AI instructions longer than 10,000 characters",
        "Keep instructions concise; longer instructions exceed the supported size and dilute the context.",
    ),
    (
        "AI_INSTRUCTIONS_UNKNOWN_FIELDS",
        "Prep data for AI",
        2,
        "AI instructions refer to fields that don't exist",
        "Bracketed names in the instructions should match measures or columns in the model.",
    ),
    (
        "AI_NO_SCHEMA",
        "Prep data for AI",
        2,
        "No AI data schema",
        "Without an AI data schema Copilot sees every object. Choose the tables, columns and measures a business user would ask about (Copilot/schema.json).",
    ),
    (
        "AI_NO_VERIFIED_ANSWERS",
        "Prep data for AI",
        1,
        "No verified answers",
        "Verified answers ground the most frequent, important questions in a known-correct visual.",
    ),
    (
        "AI_NO_EXAMPLE_PROMPTS",
        "Prep data for AI",
        1,
        "No example prompts",
        "Example prompts show users what they can ask and give agents a pattern to follow.",
    ),
    (
        "AI_VISIBLE_KEYS",
        "What AI can see",
        2,
        "Visible key and ID columns",
        "Keys and IDs invite meaningless aggregations and wrong field choices. Hide them or leave them out of the AI data schema.",
    ),
    (
        "AI_VISIBLE_SORT_HELPERS",
        "What AI can see",
        2,
        "Visible sort-order helper columns",
        "Columns used only to sort other columns (Month Number and so on) add noise for AI. Hide them.",
    ),
    (
        "AI_HELPER_MEASURES",
        "What AI can see",
        1,
        "Visible helper measures",
        "Measures used only inside other measures are intermediate steps; hide them so AI picks the final measure.",
    ),
    (
        "AI_UNUSED_VISIBLE",
        "What AI can see",
        2,
        "Visible objects nothing uses",
        "Unused tables and columns crowd the schema AI searches and raise the chance of a wrong pick.",
    ),
]

AI_OK_ACRONYMS = {
    "YTD",
    "MTD",
    "QTD",
    "WTD",
    "YOY",
    "MOM",
    "QOQ",
    "WOW",
    "PY",
    "LY",
    "PM",
    "PQ",
    "KPI",
    "ID",
    "USD",
    "EUR",
    "GBP",
    "AED",
    "ROI",
    "CAC",
    "LTV",
    "SKU",
    "VAT",
    "GDP",
    "EMEA",
    "APAC",
    "AMER",
    "US",
    "UK",
    "UAE",
    "EU",
    "CEO",
    "CFO",
    "HR",
    "IT",
    "FY",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "H1",
    "H2",
    "B2B",
    "B2C",
    "ARR",
    "MRR",
    "NPS",
    "EBIT",
    "EBITDA",
    "COGS",
    "GL",
    "AR",
    "AP",
    "P&L",
    "OK",
    "AI",
}
AI_ABBREV = {
    "amt",
    "qty",
    "desc",
    "num",
    "cnt",
    "pct",
    "avg",
    "tot",
    "cust",
    "prod",
    "dt",
    "yr",
    "mth",
    "mo",
    "wk",
    "cat",
    "subcat",
    "addr",
    "acct",
    "bal",
    "val",
    "grp",
    "dept",
    "loc",
    "curr",
    "ccy",
    "dim",
    "fct",
    "cd",
    "nm",
    "nbr",
    "no",
    "rev",
    "exp",
    "inv",
    "ord",
    "trx",
    "txn",
    "prc",
    "disc",
}
TI_TOKENS = {"YTD", "MTD", "QTD", "WTD", "PY", "LY", "YOY", "MOM", "QOQ"}


def _technical(name):
    if "_" in name:
        return "snake_case"
    if re.match(r"(?i)^(dim|fact|fct|tbl|vw|stg|lkp|ref)(?=[A-Z_ ])", name):
        return "technical prefix"
    if " " not in name and re.search(r"[a-z][A-Z]", name) and not re.fullmatch(r"[A-Z]{2,}[a-z]*", name):
        return "CamelCase"
    words = re.findall(r"[A-Za-z]{4,}", name)
    if words and all(w.isupper() for w in words) and not all(w in AI_OK_ACRONYMS for w in words):
        return "ALL CAPS"
    return ""


def _copilot_folder(model_dir):
    info = {"exists": False, "instructions": None, "schema": False, "verified": 0, "examples": 0}
    if not model_dir:
        return info
    cp = model_dir / "Copilot"
    if not cp.is_dir():
        return info
    info["exists"] = True
    ins = cp / "Instructions" / "instructions.md"
    if ins.exists():
        info["instructions"] = read_text(ins)
    info["schema"] = (cp / "schema.json").exists()
    va = cp / "VerifiedAnswers"
    if va.is_dir():
        info["verified"] = sum(1 for f in va.rglob("*") if f.is_file() and f.suffix.lower() == ".json")
    ex = cp / "examplePrompts.json"
    if ex.exists():
        data = read_json(ex)
        if isinstance(data, list):
            info["examples"] = len(data)
        elif isinstance(data, dict):
            info["examples"] = sum(len(v) for v in data.values() if isinstance(v, list)) or (1 if data else 0)
    return info


def _qna_setting(model_dir):
    """True / False from definition.pbism, or None when the file doesn't say."""
    if not model_dir:
        return None
    pb = model_dir / "definition.pbism"
    if not pb.exists():
        return None
    data = read_json(pb) or {}
    st = data.get("settings") or {}
    if "qnaEnabled" in st:
        return bool(st["qnaEnabled"])
    return None


def _report_measures(report_dir):
    """Measures defined in a report (report-level measures), by name."""
    names = []
    if not report_dir:
        return names
    for f in [report_dir / "definition" / "reportExtensions.json"]:
        if f.exists():
            data = read_json(f) or {}
            for ent in data.get("entities") or []:
                for ms in ent.get("measures") or []:
                    names.append((ms.get("name", ""), ent.get("name", "")))
    legacy = report_dir / "report.json"
    if legacy.exists():
        data = read_json(legacy) or {}
        ext = data.get("modelExtensions")
        if isinstance(ext, str):
            try:
                ext = json.loads(ext)
            except ValueError:
                ext = None
        for me in ext or []:
            for ent in (me.get("entities") or []) if isinstance(me, dict) else []:
                for ms in ent.get("measures") or []:
                    names.append((ms.get("name", ""), ent.get("name", "")))
    return names


def ai_evaluate(inv, model_dir, report_dirs, graph_info):
    """graph_info: {'unused': set((table, name)), 'helper_measures': set((table, name))} from the lineage graph."""
    out, skipped = defaultdict(list), set()
    T = [t for t in inv["tables"] if not is_auto_table(t["name"])]
    rels = [
        r for r in inv["relationships"] if not (is_auto_table(r["fromTable"]) or is_auto_table(r["toTable"]))
    ]

    def add(rule, kind, name, table="", note=""):
        if _on_auto_date(kind, name, table):
            return
        out[rule].append({"kind": kind, "name": name, "table": table, "note": note})

    visible_cols = [(t, c) for t in T for c in t["columns"] if not (c["hidden"] or t["hidden"])]
    visible_meas = [(t, m) for t in T for m in t["measures"] if not (m["hidden"] or t["hidden"])]

    def auto(t):
        return is_auto_table(t["name"])

    # ---------------- Foundation ----------------
    qna = _qna_setting(model_dir)
    if qna is None:
        skipped.add("AI_QNA_DISABLED")
    elif not qna:
        add("AI_QNA_DISABLED", "model", inv["model"].get("name") or "Model", note="qnaEnabled is false")
    measures = [(t, m) for t in T for m in t["measures"]]
    if not measures:
        add("AI_NO_MEASURES", "model", inv["model"].get("name") or "Model")
    referenced = set()
    for _t, m in measures:
        qual, bare = _refs(m["expr"])
        referenced |= {(tb, nm) for tb, nm in qual}
        for nm in bare:
            for tt in T:
                if any(c["name"] == nm for c in tt["columns"]):
                    referenced.add((tt["name"], nm))
    for t, c in visible_cols:
        if (
            c["dataType"] in ("int64", "decimal", "double")
            and c["summarizeBy"] != "none"
            and (t["name"], c["name"]) not in referenced
            and not re.search(r"(?i)(id|key|code|year|number)$", c["name"])
        ):
            add(
                "AI_IMPLICIT_ONLY_COLUMNS",
                "column",
                c["name"],
                t["name"],
                "summarizes by " + (c["summarizeBy"] or "default"),
            )
    for rname, rdir in report_dirs:
        for ms, ent in _report_measures(rdir):
            add("AI_REPORT_MEASURES", "measure", ms, ent, "defined in report " + rname)
    for t in T:
        if any(r["fromTable"] == t["name"] for r in rels) and any(r["toTable"] == t["name"] for r in rels):
            add("AI_SNOWFLAKE", "table", t["name"])
    for r in rels:
        m2m = r["fromCard"] == "many" and r["toCard"] == "many"
        if m2m or r["both"]:
            add(
                "AI_AMBIGUOUS_RELATIONSHIPS",
                "relationship",
                f"{r['fromTable']}[{r['fromColumn']}] → {r['toTable']}[{r['toColumn']}]",
                note=", ".join(
                    x for x in ("many-to-many" if m2m else "", "both directions" if r["both"] else "") if x
                ),
            )
    date_tables = [t for t in T if t["dataCategory"].lower() == "time"]
    if not any(any(c["isKey"] and c["dataType"] == "datetime" for c in t["columns"]) for t in date_tables):
        add("AI_NO_DATE_TABLE", "model", inv["model"].get("name") or "Model")
    dims = {r["toTable"] for r in rels if r["toCard"] == "one"}
    for t in T:
        if (
            t["name"] in dims
            and not t["hidden"]
            and t not in date_tables
            and not auto(t)
            and not any(c.get("defaultLabel") for c in t["columns"])
        ):
            add("AI_NO_DEFAULT_LABEL", "table", t["name"])
    for t in date_tables or [t for t in T if re.search(r"(?i)^(date|calendar|dates)$", t["name"])]:
        if not t["hierarchies"] and not auto(t):
            add("AI_DATE_NO_HIERARCHY", "table", t["name"])
    for t, c in visible_cols:
        if (
            c["dataType"] in ("int64", "decimal", "double")
            and c["summarizeBy"] != "none"
            and re.search(
                r"(?i)(\bid\b|id$|key$|code$|\byear\b|month ?(no|number|num)$|zip|postal|\bsk$)", c["name"]
            )
        ):
            add(
                "AI_SUMMARIZED_IDENTIFIERS",
                "column",
                c["name"],
                t["name"],
                "summarizes by " + (c["summarizeBy"] or "default"),
            )

    # ---------------- Naming ----------------
    visible_objs = (
        [("table", t["name"], "") for t in T if not t["hidden"] and not auto(t)]
        + [("column", c["name"], t["name"]) for t, c in visible_cols]
        + [("measure", m["name"], t["name"]) for t, m in visible_meas]
    )
    for kind, name, tname in visible_objs:
        why = _technical(name)
        if why:
            add("AI_TECHNICAL_NAMES", kind, name, tname, why)
        toks = re.findall(r"[A-Za-z]+", name)
        bad = [w for w in toks if w.lower() in AI_ABBREV and w.upper() not in AI_OK_ACRONYMS]
        if bad:
            add("AI_ABBREVIATIONS", kind, name, tname, ", ".join(dict.fromkeys(bad)))
    by_name = defaultdict(list)
    for t, c in visible_cols:
        by_name[c["name"].lower()].append((t, c))
    dup_cols = set()
    for lst in by_name.values():
        if len(lst) > 1:
            for t, c in lst:
                dup_cols.add((t["name"], c["name"]))
                add(
                    "AI_DUPLICATE_COLUMN_NAMES",
                    "column",
                    c["name"],
                    t["name"],
                    "also in " + ", ".join(x[0]["name"] for x in lst if x[0] is not t),
                )
    pos = defaultdict(set)
    for _t, m in measures:
        words = m["name"].split()
        if len(words) < 2:
            continue
        if words[0].upper() in TI_TOKENS:
            pos[words[0].upper()].add("prefix")
        if words[-1].upper() in TI_TOKENS:
            pos[words[-1].upper()].add("suffix")
    mixed = {tok for tok, ps in pos.items() if len(ps) > 1}
    for t, m in measures:
        words = m["name"].split()
        if words and (words[0].upper() in mixed or words[-1].upper() in mixed):
            add("AI_INCONSISTENT_TI_NAMES", "measure", m["name"], t["name"])

    # ---------------- Descriptions ----------------
    if not (inv["model"].get("desc") or "").strip():
        add("AI_NO_MODEL_DESCRIPTION", "model", inv["model"].get("name") or "Model")
    for t in T:
        if not t["hidden"] and not auto(t) and not t["desc"].strip():
            add("AI_TABLE_NO_DESCRIPTION", "table", t["name"])
        if t["calcGroup"] and not t["desc"].strip() and not any(c["desc"].strip() for c in t["columns"]):
            add("AI_CALC_GROUP_NO_DESCRIPTION", "table", t["name"])
    for t, m in visible_meas:
        if not m["desc"].strip():
            add("AI_MEASURE_NO_DESCRIPTION", "measure", m["name"], t["name"])
    for t, c in visible_cols:
        if (t["name"], c["name"]) in dup_cols and not c["desc"].strip():
            add("AI_AMBIGUOUS_NO_DESCRIPTION", "column", c["name"], t["name"])
    described = (
        [("table", t["name"], "", t["desc"]) for t in T]
        + [("column", c["name"], t["name"], c["desc"]) for t in T for c in t["columns"]]
        + [("measure", m["name"], t["name"], m["desc"]) for t in T for m in t["measures"]]
    )

    def norm_words(x):
        return {w for w in re.findall(r"[a-z0-9]+", x.lower()) if w not in _FILLER_WORDS}

    for kind, name, tname, desc in described:
        d = (desc or "").strip()
        if not d:
            continue
        if len(d) > 200:
            add("AI_DESCRIPTION_TOO_LONG", kind, name, tname, f"{len(d)} characters")
        dw, nw = (
            norm_words(d),
            norm_words(name) | norm_words(tname) | {"column", "measure", "table", "value", "field", "total"},
        )
        if dw and dw <= nw:
            add("AI_DESCRIPTION_RESTATES_NAME", kind, name, tname, "“" + d[:60] + "”")
    for t, m in measures:
        e = m["expr"] or ""
        if (len(e) > 250 or len(re.findall(r"(?i)\bVAR\b", e)) >= 3) and not re.search(r"//|--|/\*", e):
            add("AI_DAX_NO_COMMENTS", "measure", m["name"], t["name"], f"{len(e)} characters")

    # ---------------- Prep data for AI ----------------
    cp = _copilot_folder(model_dir)
    ins = (cp["instructions"] or "").strip()
    mname = inv["model"].get("name") or "Model"
    if not ins:
        add(
            "AI_NO_INSTRUCTIONS",
            "model",
            mname,
            note="Copilot folder not found" if not cp["exists"] else "instructions.md is missing or empty",
        )
    else:
        if len(ins) > 10000:
            add("AI_INSTRUCTIONS_TOO_LONG", "model", mname, note=f"{len(ins):,} characters")
        known = (
            {c["name"].lower() for t in T for c in t["columns"]}
            | {m["name"].lower() for t in T for m in t["measures"]}
            | {t["name"].lower() for t in T}
        )
        for ref in dict.fromkeys(re.findall(r"\[([^\]\n]{1,80})\]", ins)):
            if ref.lower() not in known and not ref.startswith("http"):
                add(
                    "AI_INSTRUCTIONS_UNKNOWN_FIELDS",
                    "model",
                    "[" + ref + "]",
                    note="not a measure, column or table",
                )
    if not cp["schema"]:
        add("AI_NO_SCHEMA", "model", mname, note="Copilot/schema.json not found")
    if not cp["verified"]:
        add("AI_NO_VERIFIED_ANSWERS", "model", mname)
    if not cp["examples"]:
        add("AI_NO_EXAMPLE_PROMPTS", "model", mname)

    # ---------------- What AI can see ----------------
    rel_cols = {(r["fromTable"], r["fromColumn"]) for r in rels} | {
        (r["toTable"], r["toColumn"]) for r in rels
    }
    sort_targets = {(t["name"], c["sortBy"]) for t in T for c in t["columns"] if c["sortBy"]}
    for t, c in visible_cols:
        key = (t["name"], c["name"])
        if key in rel_cols or re.search(r"(?i)(\bid\b|id$|key$|\bsk$)", c["name"]):
            add(
                "AI_VISIBLE_KEYS",
                "column",
                c["name"],
                t["name"],
                "relationship column" if key in rel_cols else "",
            )
        if key in sort_targets:
            add("AI_VISIBLE_SORT_HELPERS", "column", c["name"], t["name"])
    for t, m in visible_meas:
        if (t["name"], m["name"]) in graph_info.get("helper_measures", set()) or re.match(
            r"^[_.]", m["name"]
        ):
            add("AI_HELPER_MEASURES", "measure", m["name"], t["name"])
    for kind, name, tname in visible_objs:
        if kind in ("table", "column") and (
            (tname or name, name) if kind == "column" else (name, "")
        ) in graph_info.get("unused", set()):
            add("AI_UNUSED_VISIBLE", kind, name, tname)
    return out, skipped


def ai_readiness(G: Graph, models: list, reports: list) -> list:
    """AI readiness rules for every model, with findings linked to lineage cards."""
    out_edges = defaultdict(list)
    for a, b in G.edges:
        out_edges[a].append(b)
    results = {}
    for m in models:
        inv = getattr(m["model"], "bpa_inv", None)
        if not inv:
            continue
        unused, helpers = set(), set()
        for n in G.nodes.values():
            if n.get("mkey") != m["key"] or n.get("auto"):
                continue
            if n["type"] == "table" and not n.get("used"):
                unused.add((n["label"], ""))
            elif n["type"] == "column" and not n.get("used") and n.get("table"):
                unused.add((n["table"], n["label"]))
            elif n["type"] == "measure" and n.get("table"):
                targets = [G.nodes[x]["type"] for x in out_edges[n["id"]] if x in G.nodes]
                if targets and "visual" not in targets and "page" not in targets and "measure" in targets:
                    helpers.add((n["table"], n["label"]))
        rdirs = [(r["name"], r.get("dir")) for r in reports if r.get("model") == m["key"]]
        try:
            found, skipped = ai_evaluate(
                inv, m.get("dir"), rdirs, {"unused": unused, "helper_measures": helpers}
            )
        except Exception as exc:
            warn(f"AI readiness checks failed on {m['name']}: {exc}")
            continue
        with id_namespace(m["key"] + NS_SEP):
            for lst in found.values():
                for f in lst:
                    cand = None
                    if f["kind"] == "table":
                        cand = tid(f["name"])
                    elif f["kind"] == "column" and f["table"]:
                        cand = cid(f["table"], f["name"])
                    elif f["kind"] == "measure" and f["table"]:
                        cand = mid(f["table"], f["name"])
                    if cand and cand in G.nodes:
                        f["id"] = cand
        results[m["key"]] = (found, skipped)
    rules = []
    for rid, category, severity, name, desc in AI_RULES:
        items, ran = [], False
        for m in models:
            found, skipped = results.get(m["key"], ({}, {rid}))
            if rid not in skipped:
                ran = True
            for f in found.get(rid, []):
                is_model = f["kind"] == "model" and not f["name"].startswith("[")
                items.append(
                    {
                        "id": ("M:" + m["key"]) if is_model else f.get("id", ""),
                        "label": m["name"] if is_model else f["name"],
                        "table": f["table"],
                        "mkey": m["key"],
                        "note": f["note"],
                        "kind": f["kind"],
                    }
                )
        items.sort(key=lambda x: (x["table"].lower(), x["label"].lower()))
        rules.append(
            {
                "id": rid,
                "category": category,
                "severity": severity,
                "name": name,
                "desc": desc,
                "source": "ai",
                "checked": ran and bool(results),
                "items": items,
            }
        )
    return rules
