# SPDX-License-Identifier: Apache-2.0
"""End-to-end: build the synthetic projects and check what the page carries."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from trailsbi.cli import main

SRC = Path(__file__).resolve().parents[1] / "src"


def rule(data, rid, section="health"):
    return next(r for r in data[section] if r["id"] == rid)


def labels(r):
    return sorted(i["label"] for i in r["items"])


def test_counts(build, fixtures):
    _, data = build(fixtures / "Shop" / "Shop.pbip")
    c = data["meta"]["counts"]
    assert (c["model"], c["report"]) == (1, 1)
    assert (c["table"], c["page"], c["visual"]) == (3, 2, 3)
    assert data["meta"]["modelFormat"] == "TMDL"
    assert data["meta"]["reportFormat"] == "PBIR"


def test_lineage_runs_from_source_to_page(build, fixtures):
    _, data = build(fixtures / "Shop" / "Shop.pbip")
    nodes = {n["id"]: n for n in data["nodes"]}
    out = {}
    for a, b, _role in data["edges"]:
        out.setdefault(a, set()).add(b)

    def reach(start):
        seen, todo = set(), [start]
        while todo:
            for nxt in out.get(todo.pop(), ()):
                if nxt not in seen:
                    seen.add(nxt)
                    todo.append(nxt)
        return seen

    source = next(n for n in nodes.values() if n["type"] == "source")
    reached = {nodes[x]["label"] for x in reach(source["id"])}
    assert {"Sales", "Amount", "Total Sales", "Sales Growth %", "Overview"} <= reached


def test_findings(build, fixtures):
    _, data = build(fixtures / "Shop" / "Shop.pbip")
    assert labels(rule(data, "MISSING_FIELDS")) == ["Missing Measure"]
    assert labels(rule(data, "MEASURES_NOT_USED_IN_REPORTS")) == ["Unused Measure"]
    assert "prod_name" in labels(rule(data, "AI_TECHNICAL_NAMES", "ai"))
    assert all(r["id"] != "MODELS_WITH_NO_REPORTS" for r in data["health"])


def test_legacy_formats(build, fixtures):
    _, data = build(fixtures / "Legacy" / "Legacy.pbip")
    assert data["meta"]["modelFormat"] == "model.bim (TMSL)"
    assert data["meta"]["reportFormat"] == "PBIR-Legacy"
    visual = next(n for n in data["nodes"] if n["type"] == "visual")
    feeds = {a for a, b, _ in data["edges"] if b == visual["id"]}
    names = {n["label"] for n in data["nodes"] if n["id"] in feeds}
    assert {"Units", "Name"} <= names


def test_page_is_self_contained(build, fixtures):
    out, _ = build(fixtures / "Shop" / "Shop.pbip")
    html = out.read_text(encoding="utf-8")
    assert not re.search(r'<(script|img|iframe)[^>]+src="https?:', html)
    assert not re.search(r'<link[^>]+href="https?:', html)
    assert "fetch(" not in html and "XMLHttpRequest" not in html
    assert "__DATA__" not in html and "__SCRIPT__" not in html


def test_project_defaults_to_the_current_folder(fixtures, tmp_path, monkeypatch, capsys):
    from trailsbi.cli import main

    monkeypatch.chdir(fixtures / "Shop")
    assert main(["-o", str(tmp_path)]) == 0
    capsys.readouterr()
    pages = list(tmp_path.glob("TrailsBI Report - Shop - *.html"))
    assert len(pages) == 1
    assert not list(tmp_path.glob("*.csv"))


def test_same_project_gives_the_same_page(fixtures, tmp_path):
    """Set iteration order changes with the hash seed; the page must not."""
    pages = []
    for seed in ("1", "2"):
        out = tmp_path / f"run{seed}.html"
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(SRC))
        subprocess.run(
            [sys.executable, "-m", "trailsbi", str(fixtures / "Shop"), "-o", str(out)],
            check=True,
            env=env,
            capture_output=True,
        )
        html = out.read_text(encoding="utf-8")
        pages.append(re.sub(r'"generated": "[^"]*"', "", html))
    assert pages[0] == pages[1]


def test_cli_exit_codes(fixtures, tmp_path, capsys):
    assert main([str(fixtures / "Shop"), "-o", str(tmp_path / "a.html")]) == 0
    assert main([str(fixtures / "TwoProjects")]) == 2
    assert "one project at a time" in capsys.readouterr().err


def test_live_connected_report(build, tmp_path):
    proj = tmp_path / "Live"
    defn = proj / "Live.Report" / "definition"
    page = defn / "pages" / "p1"
    (page / "visuals" / "v1").mkdir(parents=True)
    conn = "Data Source=powerbi://api.powerbi.com/v1.0/myorg/Finance;Initial Catalog=Finance Model"
    (proj / "Live.Report" / "definition.pbir").write_text(
        json.dumps({"datasetReference": {"byConnection": {"connectionString": conn}}})
    )
    (proj / "Live.pbip").write_text(json.dumps({"artifacts": [{"report": {"path": "Live.Report"}}]}))
    (defn / "pages" / "pages.json").write_text(json.dumps({"pageOrder": ["p1"]}))
    (page / "page.json").write_text(json.dumps({"name": "p1", "displayName": "Revenue"}))
    field = {"Measure": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "Revenue"}}
    visual = {
        "name": "v1",
        "position": {"x": 0, "y": 0, "width": 100, "height": 100},
        "visual": {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": [{"field": field}]}}},
        },
    }
    (page / "visuals" / "v1" / "visual.json").write_text(json.dumps(visual))
    _, data = build(proj)
    assert data["meta"]["counts"]["model"] == 0
    assert data["meta"]["reports"][0]["external"] == "Finance Model"
    revenue = next(n for n in data["nodes"] if n["label"] == "Revenue" and n["type"] == "measure")
    assert revenue.get("extmodel") == "Finance Model"


def test_names_cannot_break_the_page(build, tmp_path, fixtures):
    import shutil

    proj = tmp_path / "Odd"
    shutil.copytree(fixtures / "Shop", proj)
    tbl = proj / "Shop.SemanticModel" / "definition" / "tables" / "Product.tmdl"
    text = tbl.read_text(encoding="utf-8").replace("column Category", "column '</script><!--__DATA__'")
    tbl.write_text(text, encoding="utf-8")
    out, data = build(proj)
    html = out.read_text(encoding="utf-8")
    assert html.count("</script>") == html.count("<script")
    assert any(n["label"] == "</script><!--__DATA__" for n in data["nodes"])


def test_output_into_a_folder(fixtures, tmp_path, capsys):
    assert main([str(fixtures / "Shop"), "-o", str(tmp_path)]) == 0
    [page] = tmp_path.glob("TrailsBI Report - Shop - *.html")
    assert re.fullmatch(r"TrailsBI Report - Shop - \d{4}-\d{2}-\d{2} \d{2}-\d{2}\.html", page.name)


def test_page_script_is_valid_javascript(tmp_path):
    import shutil

    import pytest

    from trailsbi.render import page_template

    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed")
    m = re.search(r"<script>\n(\(function \(\) \{.*?)</script>", page_template(), re.S)
    js = tmp_path / "page.js"
    js.write_text(m.group(1), encoding="utf-8")
    subprocess.run([node, "--check", str(js)], check=True)
