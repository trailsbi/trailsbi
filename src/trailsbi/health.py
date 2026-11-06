# SPDX-License-Identifier: Apache-2.0
"""The Health view: Best Practice Analyzer results plus lineage checks."""

from __future__ import annotations

from collections import defaultdict, deque

from .bpa import BPA_RULES
from .graph import Graph


def health(G: Graph, models: list, reports: list) -> list:
    """The Health view's rules with their findings.

    Marks every node `used` when a visual or page depends on it, then runs the
    lineage checks and gathers the Best Practice Analyzer results per rule.
    """
    rev = defaultdict(list)
    fwd = defaultdict(list)
    for a, b in G.edges:
        rev[b].append(a)
        fwd[a].append(b)
    used = set()
    dq = deque(n for n, d in G.nodes.items() if d["type"] in ("visual", "page"))
    while dq:
        x = dq.popleft()
        for y in rev[x]:
            if y not in used:
                used.add(y)
                dq.append(y)
    # A column that sorts a used column is used too: without it the sort order breaks.
    for nid in list(used):
        sb = G.nodes[nid].get("sortbyId")
        if sb and sb not in used:
            used.add(sb)
            dq.append(sb)
    while dq:
        x = dq.popleft()
        for y in rev[x]:
            if y not in used:
                used.add(y)
                dq.append(y)
    for n in G.nodes.values():
        if n["type"] not in ("visual", "page"):
            n["used"] = n["id"] in used

    def items(pred, note=None):
        out = []
        for n in G.nodes.values():
            if n.get("auto"):  # generated date tables are not yours to fix
                continue
            if pred(n):
                out.append(
                    {
                        "id": n["id"],
                        "label": n["label"],
                        "table": n.get("table", ""),
                        "mkey": n.get("mkey", ""),
                        "note": note(n) if note else "",
                    }
                )
        return sorted(out, key=lambda x: (x["table"].lower(), x["label"].lower()))

    has_report = any(n["type"] == "visual" for n in G.nodes.values())
    rules = []

    def own(rid, category, severity, name, desc, found):
        rules.append(
            {
                "id": rid,
                "category": category,
                "severity": severity,
                "name": name,
                "desc": desc,
                "source": "lineage",
                "checked": True,
                "items": found,
            }
        )

    own(
        "MISSING_FIELDS",
        "Error Prevention",
        3,
        "Fields missing from the semantic model",
        "Visuals or filters reference these, but the semantic model has no such column or measure. "
        "The visuals will show an error.",
        items(lambda n: n.get("broken"), lambda n: f"{len(fwd[n['id']])} use(s)"),
    )
    if has_report:
        own(
            "MEASURES_NOT_USED_IN_REPORTS",
            "Maintenance",
            2,
            "Measures not used in the report",
            "No visual, filter or other used measure depends on these.",
            items(
                lambda n: (
                    n["type"] == "measure"
                    and n.get("sub") == "measure"
                    and not n.get("used")
                    and not n.get("auto")
                ),
                lambda n: "hidden" if n.get("hidden") else "",
            ),
        )
        own(
            "COLUMNS_NOT_USED_IN_REPORTS",
            "Maintenance",
            2,
            "Columns not used in the report",
            "Not used by visuals, filters or used measures. Removing unused columns shrinks the model. "
            "Relationship keys are flagged; keep them if the relationship filters used tables.",
            items(
                lambda n: (
                    n["type"] == "column"
                    and not n.get("used")
                    and not n.get("auto")
                    and not n.get("broken")
                    and not n.get("external")
                ),
                lambda n: (
                    ("relationship key" if n.get("relkey") else "")
                    + (" · calculated" if n.get("sub") == "calculated" else "")
                ),
            ),
        )
        own(
            "TABLES_NOT_USED_IN_REPORTS",
            "Maintenance",
            2,
            "Tables not used in the report",
            "Nothing on any page depends on these tables.",
            items(lambda n: n["type"] == "table" and not n.get("used") and not n.get("auto")),
        )
        own(
            "CALC_GROUPS_NOT_USED_IN_REPORTS",
            "Maintenance",
            2,
            "Calculation groups not used in the report",
            "No visual, slicer or filter uses the column of these calculation groups, "
            "so they change nothing.",
            items(lambda n: n["type"] == "calcgroup" and not n.get("used")),
        )
    groups_by_model = defaultdict(list)
    for n in G.nodes.values():
        if n["type"] == "calcgroup":
            groups_by_model[n.get("mkey", "")].append(n)
    shared = []
    for groups in groups_by_model.values():
        by_prec = defaultdict(list)
        for g in groups:
            by_prec[g.get("prec", 0)].append(g)
        shared += [g for gs in by_prec.values() if len(gs) > 1 for g in gs]
    shared_ids = {g["id"] for g in shared}
    own(
        "CALC_GROUPS_SAME_PRECEDENCE",
        "Error Prevention",
        2,
        "Calculation groups with the same precedence",
        "When more than one calculation group changes a measure, precedence decides which applies first, "
        "and the order changes the result (a year-to-date of a currency conversion, or the other way round). "
        "Give each group its own precedence.",
        items(lambda n: n["id"] in shared_ids, lambda n: f"precedence {n.get('prec', 0)}"),
    )
    own(
        "CALC_ITEMS_IGNORE_THE_MEASURE",
        "DAX Expressions",
        1,
        "Calculation items that ignore the measure",
        "These items never call SELECTEDMEASURE(), so every measure they apply to shows the same value. "
        "That is rarely intended; check the expression.",
        items(lambda n: n["type"] == "calcitem" and not n.get("selm")),
    )
    own(
        "QUERIES_NOT_REFERENCED",
        "Maintenance",
        1,
        "Queries and parameters not referenced",
        "Power Query items that no table or other query uses.",
        items(lambda n: n["type"] == "query" and not fwd[n["id"]]),
    )

    # Microsoft's Best Practice Analyzer rules
    for rid, category, severity, name, desc in BPA_RULES:
        found, ran = [], False
        for m in models:
            if rid not in m.get("bpa_skipped", set()) and m.get("bpa") is not None:
                ran = True
            for f in m.get("bpa", {}).get(rid, []):
                found.append(
                    {
                        "id": f.get("id", ""),
                        "label": f["name"],
                        "table": f["table"],
                        "mkey": m["key"],
                        "note": f["note"],
                        "kind": f["kind"],
                    }
                )
        found.sort(key=lambda x: (x["table"].lower(), x["label"].lower()))
        rules.append(
            {
                "id": rid,
                "category": category,
                "severity": severity,
                "name": name,
                "desc": desc,
                "source": "bpa",
                "checked": ran,
                "items": found,
            }
        )
    return rules
