# SPDX-License-Identifier: Apache-2.0
"""Calculation groups are their own kind of object: in lineage, the details and the checks."""

import shutil

SEP = "␟"


def node(data, ntype, label):
    return next(n for n in data["nodes"] if n["type"] == ntype and n["label"] == label)


def edges(data):
    return {(a, b) for a, b, _ in data["edges"]}


def rule(data, rid, section="health"):
    return next(r for r in data[section] if r["id"] == rid)


def link_labels(data, n, title):
    ids = next(lk["ids"] for lk in n["detail"].get("links", []) if lk["title"] == title)
    by_id = {x["id"]: x["label"] for x in data["nodes"]}
    return sorted(by_id[i] for i in ids)


def test_groups_and_items_have_their_own_types(build, fixtures):
    _, data = build(fixtures / "CalcGroups")
    group = node(data, "calcgroup", "Time Intelligence")
    assert group["prec"] == 10 and group["nitems"] == 4 and group["namecol"] == "Time Calculation"
    items = [
        n["label"] for n in data["nodes"] if n["type"] == "calcitem" and n["table"] == "Time Intelligence"
    ]
    assert items == ["Current", "Last Year", "YTD", "Fixed Target"]
    # no calculation group is left behind as a table, and no item as a measure
    assert not any(
        n["type"] == "table" and n["label"] in ("Time Intelligence", "Currency") for n in data["nodes"]
    )
    assert not any(n["type"] == "measure" and n["label"] == "YTD" for n in data["nodes"])


def test_items_feed_the_group_column_and_the_visuals(build, fixtures):
    _, data = build(fixtures / "CalcGroups")
    e = edges(data)
    group, ytd = node(data, "calcgroup", "Time Intelligence"), node(data, "calcitem", "YTD")
    col = node(data, "column", "Time Calculation")
    matrix = next(n for n in data["nodes"] if n["type"] == "visual" and n["label"].startswith("Matrix"))
    date = next(n for n in data["nodes"] if n["type"] == "column" and n["id"].endswith("Date" + SEP + "Date"))
    assert (group["id"], ytd["id"]) in e and (ytd["id"], col["id"]) in e and (col["id"], matrix["id"]) in e
    assert (date["id"], ytd["id"]) in e  # DATESYTD('Date'[Date])
    assert ytd["used"] and group["used"]


def test_measures_each_item_can_change(build, fixtures):
    _, data = build(fixtures / "CalcGroups")
    # the matrix shows Total Sales by Time Calculation
    assert link_labels(data, node(data, "calcgroup", "Time Intelligence"), "Measures it can change") == [
        "Total Sales"
    ]
    # a Currency slicer reaches every measure on its page;
    # ISSELECTEDMEASURE narrows an item to the measures it names
    currency = node(data, "calcgroup", "Currency")
    assert link_labels(data, currency, "Measures it can change") == ["Sales Growth %", "Total Sales"]
    assert link_labels(data, node(data, "calcitem", "In EUR"), "Measures it can change") == ["Total Sales"]
    total = node(data, "measure", "Total Sales")
    assert link_labels(data, total, "Calculation groups that can change it") == [
        "Currency",
        "Time Intelligence",
    ]


def test_calc_group_checks(build, fixtures, tmp_path):
    _, data = build(fixtures / "CalcGroups")
    assert [i["label"] for i in rule(data, "CALC_ITEMS_IGNORE_THE_MEASURE")["items"]] == ["Fixed Target"]
    assert rule(data, "CALC_GROUPS_SAME_PRECEDENCE")["items"] == []
    assert rule(data, "CALC_GROUPS_NOT_USED_IN_REPORTS")["items"] == []
    rels = [i["label"] for i in rule(data, "ENSURE_TABLES_HAVE_RELATIONSHIPS")["items"]]
    assert "Time Intelligence" not in rels and "Currency" not in rels
    # the sort column of a used column is used too
    assert node(data, "column", "Ordinal")["used"]

    proj = tmp_path / "Same"
    shutil.copytree(fixtures / "CalcGroups", proj)
    tmdl = proj / "CalcGroups.SemanticModel" / "definition" / "tables" / "Currency.tmdl"
    tmdl.write_text(
        tmdl.read_text(encoding="utf-8").replace(
            "\tcalculationGroup\n", "\tcalculationGroup\n\t\tprecedence: 10\n"
        ),
        encoding="utf-8",
    )
    _, data = build(proj)
    assert sorted(i["label"] for i in rule(data, "CALC_GROUPS_SAME_PRECEDENCE")["items"]) == [
        "Currency",
        "Time Intelligence",
    ]


def test_model_view_links_items(build, fixtures):
    _, data = build(fixtures / "CalcGroups")
    outline = data["meta"]["models"][0]["outline"]
    ytd = next(it for it in outline if it["k"] == "calculationItem" and it["n"] == "YTD")
    assert ytd["id"] == node(data, "calcitem", "YTD")["id"] and ytd["l"] == "DAX"
