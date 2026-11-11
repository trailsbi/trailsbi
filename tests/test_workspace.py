# SPDX-License-Identifier: Apache-2.0
"""Workspace lineage: a folder with several reports and semantic models builds one page."""

from __future__ import annotations

import json
import shutil

import pytest

from trailsbi.cli import main
from trailsbi.project import Project, Workspace, resolve


def _workspace(fixtures, tmp_path):
    """A Git-folder-like workspace built from the Shop fixture:

    Shop.Report        -> Shop.SemanticModel (byPath)
    Thin/Sales Review  -> "Shop" by connection, held in this folder; adds report measures
    Thin/Margin Check  -> "Shop" by connection; repeats one of those report measures
    Thin/Finance       -> "Finance Model" by connection, which this folder does not hold
    Spare.SemanticModel   no report uses it
    """
    ws = tmp_path / "Workspace"
    shutil.copytree(fixtures / "Shop", ws / "Shop")
    shutil.copytree(fixtures / "Shop" / "Shop.SemanticModel", ws / "Spare" / "Spare.SemanticModel")
    report = fixtures / "Shop" / "Shop.Report"

    def thin(name, catalog, measures=None):
        dst = ws / "Thin" / f"{name}.Report"
        shutil.copytree(report, dst)
        conn = (
            'Data Source="powerbi://api.powerbi.com/v1.0/myorg/Sales";'
            f'Initial Catalog="{catalog}";semanticmodelid=0f6e3c1a'
        )
        (dst / "definition.pbir").write_text(
            json.dumps({"version": "4.0", "datasetReference": {"byConnection": {"connectionString": conn}}})
        )
        if measures:
            ext = {"name": "extension", "entities": [{"name": "Sales", "measures": measures}]}
            (dst / "definition" / "reportExtensions.json").write_text(json.dumps(ext))

    big = {"name": "Big Orders", "expression": "CALCULATE([Total Sales], Sales[Amount] > 100)"}
    thin("Sales Review", "Shop", [big, {"name": "Only Here", "expression": "1"}])
    thin("Margin Check", "Shop", [big])
    thin("Finance", "Finance Model")
    return ws


def test_folder_with_several_projects_is_a_workspace(fixtures):
    ws = resolve(fixtures / "TwoProjects")
    assert isinstance(ws, Workspace)
    assert [m.name for m in ws.models] == ["Alpha.SemanticModel", "Beta.SemanticModel"]
    assert [(r.name, m.name) for r, m, _ in ws.reports] == [
        ("Alpha.Report", "Alpha.SemanticModel"),
        ("Beta.Report", "Beta.SemanticModel"),
    ]


def test_one_project_stays_a_project(fixtures):
    assert isinstance(resolve(fixtures / "Shop"), Project)
    assert isinstance(resolve(fixtures / "Shop" / "Shop.Report"), Project)


def test_reports_bind_to_models_in_the_folder(fixtures, tmp_path):
    ws = resolve(_workspace(fixtures, tmp_path))
    bound = {r.name: (m.name if m else None, (pub or {}).get("label")) for r, m, pub in ws.reports}
    assert bound["Shop.Report"] == ("Shop.SemanticModel", None)
    assert bound["Sales Review.Report"] == ("Shop.SemanticModel", None)  # live, but the folder has it
    assert bound["Margin Check.Report"] == ("Shop.SemanticModel", None)
    assert bound["Finance.Report"] == (None, "Finance Model")
    assert sorted(m.name for m in ws.models) == ["Shop.SemanticModel", "Spare.SemanticModel"]


def test_workspace_page(fixtures, tmp_path, build):
    _, data = build(_workspace(fixtures, tmp_path))
    meta = data["meta"]
    assert meta["workspace"] is True
    assert len(meta["reports"]) == 4 and len(meta["models"]) == 2
    shop = next(m["key"] for m in meta["models"] if m["name"] == "Shop")
    uses = {r["name"]: (r["model"], r["external"]) for r in meta["reports"]}
    assert uses["Sales Review"] == (shop, None) and uses["Finance"] == (None, "Finance Model")

    nodes = {n["id"]: n for n in data["nodes"]}
    # one copy of each model table, shared by every report on it
    sales = [
        n for n in nodes.values() if n["type"] == "table" and n["label"] == "Sales" and n.get("mkey") == shop
    ]
    assert len(sales) == 1
    edges = {(e[0], e[1]) for e in data["edges"]}
    reports_on_sales = {
        nodes[b]["rkey"].split("/")[-1]
        for a, b in edges
        if nodes[a].get("mkey") == shop and nodes[b]["type"] == "visual"
    }
    assert {"Shop.Report", "Sales Review.Report", "Margin Check.Report"} <= reports_on_sales
    # the published model the folder lacks is still shown from what its report uses
    assert any(n.get("extmodel") == "Finance Model" for n in nodes.values())

    rules = {r["id"]: r for r in data["health"]}
    spare = rules["WS_MODELS_WITHOUT_REPORTS"]["items"]
    assert [i["label"] for i in spare] == ["Spare"]
    rep = rules["WS_REPEATED_REPORT_MEASURES"]["items"]
    assert [i["label"] for i in rep] == ["Big Orders"] and "2 reports" in rep[0]["note"]
    # a model no report uses is not flagged column by column
    spare_key = spare[0]["mkey"]
    for rid in ("COLUMNS_NOT_USED_IN_REPORTS", "MEASURES_NOT_USED_IN_REPORTS", "TABLES_NOT_USED_IN_REPORTS"):
        assert not any(i["mkey"] == spare_key for i in rules[rid]["items"]), rid


def test_embed_refuses_a_workspace(fixtures, tmp_path, capsys):
    assert main([str(_workspace(fixtures, tmp_path)), "--embed"]) == 2
    assert "one report at a time" in capsys.readouterr().err


@pytest.mark.parametrize(
    "conn,expect",
    [
        ("Data Source=x;Initial Catalog=y", {"data source": "x", "initial catalog": "y"}),
        ('Data Source="a;b";Initial Catalog="M ""1"""', {"data source": "a;b", "initial catalog": 'M "1"'}),
        ("Provider=MSOLAP;Data Source='q=1'", {"provider": "MSOLAP", "data source": "q=1"}),
    ],
)
def test_connection_strings_with_quotes(conn, expect):
    from trailsbi.model import connection_parts

    assert connection_parts(conn) == expect


# ---------------------------------------------------------------- choosing what to build


def _names(data):
    meta = data["meta"]
    return sorted(m["name"] for m in meta["models"]), sorted(r["name"] for r in meta["reports"])


def test_list_prints_names_and_builds_nothing(fixtures, tmp_path, capsys):
    out = tmp_path / "list.html"
    assert main([str(_workspace(fixtures, tmp_path)), "--list", "-o", str(out)]) == 0
    text = capsys.readouterr().out
    assert "2 semantic models" in text and "4 reports" in text
    assert "Finance   [Thin/Finance.Report]   -> Finance Model (published)" in text
    assert not out.exists()


def test_model_alone_and_with_its_reports(fixtures, tmp_path, build):
    ws = _workspace(fixtures, tmp_path)
    _, data = build(ws, models=["spare"])
    assert _names(data) == (["Spare"], [])
    _, data = build(ws, models=["Shop.SemanticModel"], with_reports=True)
    assert _names(data) == (["Shop"], ["Margin Check", "Sales Review", "Shop"])
    assert data["meta"]["scope"]["all"] is True  # what was asked for is what the page opens on


def test_report_without_its_model_reads_it_as_published(fixtures, tmp_path, build):
    _, data = build(_workspace(fixtures, tmp_path), reports=["Thin/Sales*"])
    models, reports = _names(data)
    assert (models, reports) == ([], ["Sales Review"])
    assert data["meta"]["reports"][0]["external"] == "Shop"


def test_include_file_from_the_scope_menu(fixtures, tmp_path, build):
    ws = _workspace(fixtures, tmp_path)
    _, data = build(ws)
    keys = {r["name"]: r["key"] for r in data["meta"]["reports"]}
    mkeys = {m["name"]: m["key"] for m in data["meta"]["models"]}
    inc = tmp_path / "scope.json"
    inc.write_text(
        json.dumps({"models": [mkeys["Shop"]], "reports": [keys["Margin Check"], keys["Finance"]]})
    )
    _, data = build(ws, include=str(inc))
    assert _names(data) == (["Shop"], ["Finance", "Margin Check"])


def test_bad_selection_fails_cleanly(fixtures, tmp_path, capsys):
    ws = str(_workspace(fixtures, tmp_path))
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2]")
    assert main([ws, "--include", str(bad), "-o", str(tmp_path / "x.html")]) == 2
    assert "selection file" in capsys.readouterr().err
    assert main([ws, "--model", "Nope*", "-o", str(tmp_path / "x.html")]) == 2
    assert "--list" in capsys.readouterr().err


def test_same_display_name_is_told_apart_by_path(tmp_path):
    from trailsbi.workspace import labels

    a = tmp_path / "Sales" / "Report.Report"
    b = tmp_path / "Finance" / "Report.Report"
    c = tmp_path / "Other.Report"
    for d in (a, b, c):
        d.mkdir(parents=True)
    got = labels([a, b, c], tmp_path)
    assert got[a] == ("Sales/Report", "Sales/Report.Report")
    assert got[b] == ("Finance/Report", "Finance/Report.Report")
    assert got[c] == ("Other", "Other.Report")


def test_one_model_folder_builds_just_that_model(fixtures):
    ws = resolve(fixtures / "Shop" / "Shop.SemanticModel")
    assert [m.name for m in ws.models] == ["Shop.SemanticModel"] and ws.reports == []


def test_items_and_default_scope(fixtures, tmp_path, build):
    from trailsbi.workspace import default_scope

    _, data = build(_workspace(fixtures, tmp_path))
    items = {i["id"]: i for i in data["items"]}
    kinds = sorted(i["kind"] for i in items.values())
    assert kinds.count("model") == 2 and kinds.count("report") == 4 and kinds.count("external") == 1
    edges = {tuple(e) for e in data["itemEdges"]}
    finance = next(i for i in items.values() if i["kind"] == "report" and i["label"] == "Finance")
    assert (finance["external"], finance["id"]) in edges
    review = next(i for i in items.values() if i["label"] == "Sales Review")
    assert any(c[0] == "rmeasure" and c[2] == 2 for c in review["counts"])

    class G:
        nodes = {i: {} for i in range(10)}

    models = [{"key": "a", "name": "A"}, {"key": "b", "name": "B"}]
    reports = [{"key": "r1", "model": "b"}, {"key": "r2", "model": "b"}, {"key": "r3", "model": "a"}]
    assert default_scope(G, models, reports, False, limit=100)["all"] is True
    small = default_scope(G, models, reports, False, limit=5)
    assert small == {"models": ["b"], "reports": ["r1", "r2"], "all": False}
    assert default_scope(G, models, reports, True, limit=5)["all"] is True


# ---------------------------------------------------------------- several workspaces


def _spaces(fixtures, tmp_path):
    """Reports in one workspace, their semantic model in two others (a Dev and a Prod copy):

    Datasets/Prod/Shop.SemanticModel
    Datasets/Dev/Shop.SemanticModel
    Elsewhere/Reports/Prod View.Report  -> "Shop" in the workspace Prod
    Elsewhere/Reports/Dev View.Report   -> "Shop" in the workspace "Dev" (URL-encoded name)
    """
    model = fixtures / "Shop" / "Shop.SemanticModel"
    for ws in ("Prod", "Dev"):
        shutil.copytree(model, tmp_path / "Datasets" / ws / "Shop.SemanticModel")
    reports = tmp_path / "Elsewhere" / "Reports"
    for name, ws in (("Prod View", "Prod"), ("Dev View", "Dev")):
        dst = reports / f"{name}.Report"
        shutil.copytree(fixtures / "Shop" / "Shop.Report", dst)
        conn = f'Data Source="powerbi://api.powerbi.com/v1.0/myorg/{ws}";Initial Catalog="Shop"'
        (dst / "definition.pbir").write_text(
            json.dumps({"version": "4.0", "datasetReference": {"byConnection": {"connectionString": conn}}})
        )
    return tmp_path / "Datasets", reports


def test_several_folders_read_together(fixtures, tmp_path):
    datasets, reports = _spaces(fixtures, tmp_path)
    ws = resolve([str(datasets / "Prod"), str(datasets / "Dev"), str(reports)])
    assert [sp[0] for sp in ws.spaces] == ["Prod", "Dev", "Reports"]
    bound = {r.name: (m.parent.name if m else None) for r, m, _p in ws.reports}
    assert bound == {"Prod View.Report": "Prod", "Dev View.Report": "Dev"}  # the copy the connection names
    assert ws.rel(reports / "Dev View.Report") == "Reports/Dev View.Report"
    assert ws.space_of(datasets / "Dev" / "Shop.SemanticModel") == "Dev"


def test_one_folder_still_binds_by_workspace_name(fixtures, tmp_path):
    _spaces(fixtures, tmp_path)
    ws = resolve(tmp_path)
    assert len(ws.spaces) == 1  # not Git checkouts: one workspace
    bound = {r.name: m.parent.name for r, m, _p in ws.reports}
    assert bound == {"Prod View.Report": "Prod", "Dev View.Report": "Dev"}


def test_git_checkouts_are_workspaces(fixtures, tmp_path):
    datasets, _ = _spaces(fixtures, tmp_path)
    for ws in ("Prod", "Dev"):
        (datasets / ws / ".git").mkdir()
    assert sorted(sp[0] for sp in resolve(datasets).spaces) == ["Dev", "Prod"]


def test_page_and_selection_by_workspace(fixtures, tmp_path, build, capsys):
    datasets, reports = _spaces(fixtures, tmp_path)
    folders = [str(datasets / "Prod"), str(datasets / "Dev"), str(reports)]
    _, data = build(folders)
    assert data["meta"]["spaces"] == ["Prod", "Dev", "Reports"]
    assert data["meta"]["name"] == "Multiple Workspaces"
    spaces = {r["name"]: r["space"] for r in data["meta"]["reports"]}
    assert spaces == {"Prod View": "Reports", "Dev View": "Reports"}
    model_items = [i for i in data["items"] if i["kind"] == "model"]
    assert sorted(i["space"] for i in model_items) == ["Dev", "Prod"]
    assert all(i["props"][0][0] == "Workspace" for i in model_items)
    _, data = build(folders, workspaces=["prod"], with_reports=True)
    assert [m["space"] for m in data["meta"]["models"]] == ["Prod"]
    assert [r["name"] for r in data["meta"]["reports"]] == ["Prod View"]
    assert main([*folders, "--list"]) == 0
    text = capsys.readouterr().out
    assert "Workspace Reports:" in text and "-> Dev/Shop (in Dev)" in text


def test_wildcard_folders(fixtures, tmp_path):
    from trailsbi.cli import _expand

    datasets, reports = _spaces(fixtures, tmp_path)
    got = _expand([str(datasets / "*"), str(reports)])
    assert sorted(got[:2]) == sorted([str(datasets / "Dev"), str(datasets / "Prod")]) and got[2] == str(
        reports
    )


def test_file_among_several_folders_is_refused(fixtures, tmp_path, capsys):
    datasets, reports = _spaces(fixtures, tmp_path)
    pbir = reports / "Dev View.Report" / "definition.pbir"
    assert main([str(datasets), str(pbir), "-o", str(tmp_path / "x.html")]) == 2
    assert "is not a folder" in capsys.readouterr().err
