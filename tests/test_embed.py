# SPDX-License-Identifier: Apache-2.0
"""trailsbi --embed: the TrailsBI table in the model, for the TrailsBI visual."""

import json
import re
import shutil

from trailsbi.cli import main, run
from trailsbi.embed import CHUNK, MARKER, chunks, m_text
from trailsbi.tmdl import parse_tmdl_text


def copy(fixtures, tmp_path, name):
    shutil.copytree(fixtures / name, tmp_path / name)
    return tmp_path / name


def m_rows(query: str) -> list:
    """(Part, Chunk) rows back out of the #table literal, decoding M text escapes."""
    rows = []
    for part, lit in re.findall(r'\{(\d+), ("(?:[^"]|"")*")\}', query):
        text = lit[1:-1].replace('""', '"').replace("#(#)", "#")
        rows.append((int(part), text))
    return rows


def tmdl_query(path) -> str:
    table = parse_tmdl_text(path.read_text(encoding="utf-8"))[0]
    part = next(c for c in table["children"] if c["kw"] == "partition")
    return part["props"]["source"]


def test_embed_tmdl_writes_a_hidden_table_and_ref(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    assert main([str(proj), "--embed"]) == 0
    out = capsys.readouterr().out
    assert "Added the TrailsBI table" in out
    assert not list(tmp_path.glob("*.html")) and not list(proj.glob("*.html"))  # no page unless asked

    table_file = proj / "Shop.SemanticModel/definition/tables/TrailsBI.tmdl"
    text = table_file.read_text(encoding="utf-8")
    assert f"annotation {MARKER} =" in text and "\tisHidden\n" in text
    model = (proj / "Shop.SemanticModel/definition/model.tmdl").read_text(encoding="utf-8")
    assert model.rstrip().endswith("ref table TrailsBI")


def test_embedded_data_is_the_page_data(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    page = run(proj, output=tmp_path / "page.html", embed_data=True)
    capsys.readouterr()
    html = page.read_text(encoding="utf-8")
    blob = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1)
    rows = m_rows(tmdl_query(proj / "Shop.SemanticModel/definition/tables/TrailsBI.tmdl"))
    assert [p for p, _ in rows] == list(range(1, len(rows) + 1))
    assert "".join(c for _, c in rows) == blob


def test_the_table_is_left_out_of_the_analysis(fixtures, tmp_path, build):
    proj = copy(fixtures, tmp_path, "Shop")
    _, before = build(proj)
    assert main([str(proj), "--embed"]) == 0
    _, after = build(proj)
    assert after["meta"]["counts"] == before["meta"]["counts"]
    assert not any(
        "TrailsBI" in json.dumps(o) for o in after["meta"]["models"][0]["outline"] if o.get("k") != "ref"
    )
    assert not any(n.get("table") == "TrailsBI" or n.get("label") == "TrailsBI" for n in after["nodes"])


def test_running_again_replaces_the_table(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    tables = proj / "Shop.SemanticModel/definition/tables"
    assert main([str(proj), "--embed"]) == 0
    # Power BI Desktop renamed the table (and its file) and wrote Windows line ends
    old = tables / "TrailsBI.tmdl"
    renamed = tables / "Lineage data.tmdl"
    renamed.write_bytes(
        old.read_text(encoding="utf-8")
        .replace("table TrailsBI", "table 'Lineage data'")
        .replace("\n", "\r\n")
        .encode()
    )
    old.unlink()
    model_file = proj / "Shop.SemanticModel/definition/model.tmdl"
    model_file.write_text(
        model_file.read_text(encoding="utf-8").replace("ref table TrailsBI", "ref table 'Lineage data'"),
        encoding="utf-8",
    )
    capsys.readouterr()
    assert main([str(proj), "--embed"]) == 0
    assert "Updated the TrailsBI table" in capsys.readouterr().out
    assert sorted(f.name for f in tables.glob("*.tmdl")) == [
        "Date.tmdl",
        "Lineage data.tmdl",
        "Product.tmdl",
        "Sales.tmdl",
    ]
    raw = renamed.read_bytes()
    assert b"table 'Lineage data'\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")
    model = (proj / "Shop.SemanticModel/definition/model.tmdl").read_text(encoding="utf-8")
    assert model.count("ref table") == 4  # the old ref stays, no second one


def test_embed_model_bim(fixtures, tmp_path, build, capsys):
    proj = copy(fixtures, tmp_path, "Legacy")
    bim = proj / "Legacy.SemanticModel/model.bim"
    _, before = build(proj)
    for _ in range(2):
        assert main([str(proj), "--embed"]) == 0
    capsys.readouterr()
    data = json.loads(bim.read_text(encoding="utf-8"))
    ours = [t for t in data["model"]["tables"] if any(a["name"] == MARKER for a in t.get("annotations", []))]
    assert len(ours) == 1 and ours[0]["name"] == "TrailsBI" and ours[0]["isHidden"]
    query = "\n".join(ours[0]["partitions"][0]["source"]["expression"])
    assert m_rows(query)
    _, after = build(proj)
    assert after["meta"]["counts"] == before["meta"]["counts"]


def test_model_bim_in_another_layout_is_not_rewritten(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Legacy")
    bim = proj / "Legacy.SemanticModel/model.bim"
    bim.write_text(json.dumps(json.loads(bim.read_text(encoding="utf-8")), indent=4), encoding="utf-8")
    before = bim.read_bytes()
    assert main([str(proj), "--embed"]) == 2
    assert "will not rewrite it" in capsys.readouterr().err
    assert bim.read_bytes() == before


def test_a_table_of_the_same_name_is_not_overwritten(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    mine = proj / "Shop.SemanticModel/definition/tables/TrailsBI.tmdl"
    mine.write_text("table TrailsBI\n\n\tcolumn X\n\t\tdataType: string\n", encoding="utf-8")
    assert main([str(proj), "--embed"]) == 2
    assert "did not write" in capsys.readouterr().err
    assert mine.read_text(encoding="utf-8").startswith("table TrailsBI\n\n\tcolumn X")


def test_trailsbi_visual_is_left_out_of_the_report(fixtures, tmp_path, build):
    proj = copy(fixtures, tmp_path, "Shop")
    _, before = build(proj)
    pages = proj / "Shop.Report/definition/pages"
    visual = {
        "name": "trails",
        "position": {"x": 0, "y": 0, "width": 1280, "height": 720},
        "visual": {
            "visualType": "trailsbiVisual064B12C848DC424EB08BF7A4ED6ACBBB",
            "query": {
                "queryState": {
                    "part": {
                        "projections": [
                            {
                                "field": {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Entity": "TrailsBI"}},
                                        "Property": "Part",
                                    }
                                }
                            }
                        ]
                    }
                }
            },
        },
    }
    # on a page of its own, and next to other visuals on an existing page
    (pages / "trails/visuals/trails").mkdir(parents=True)
    (pages / "trails/page.json").write_text(json.dumps({"name": "trails", "displayName": "TrailsBI"}))
    (pages / "trails/visuals/trails/visual.json").write_text(json.dumps(visual))
    (pages / "overview/visuals/trails").mkdir()
    (pages / "overview/visuals/trails/visual.json").write_text(json.dumps(visual))
    _, after = build(proj)
    assert after["meta"]["counts"] == before["meta"]["counts"]
    assert after["health"] == before["health"]  # no "missing field" for TrailsBI[Part]


def test_live_connected_report_cannot_embed(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    pbir = proj / "Shop.Report/definition.pbir"
    pbir.write_text(
        json.dumps(
            {
                "version": "4.0",
                "datasetReference": {
                    "byConnection": {
                        "connectionString": "Data Source=powerbi://api.powerbi.com/v1.0/myorg/WS;"
                        "Initial Catalog=Sales"
                    }
                },
            }
        )
    )
    assert main([str(proj / "Shop.Report"), "--embed"]) == 2
    assert "published semantic model" in capsys.readouterr().err


def test_chunks_and_m_text():
    blob = "a" * (CHUNK * 2 + 5)
    assert [len(c) for c in chunks(blob)] == [CHUNK, CHUNK, 5]
    assert m_text('say "#(lf)"') == '"say ""#(#)(lf)"""'


def test_an_earlier_trailsbi_table_is_taken_over(fixtures, tmp_path, capsys):
    """The visual preview's tools/to_table.py wrote a TrailsBI table with no marker."""
    proj = copy(fixtures, tmp_path, "Shop")
    old = proj / "Shop.SemanticModel/definition/tables/TrailsBI.tmdl"
    old.write_text(
        "table TrailsBI\n\n\tcolumn Part\n\t\tdataType: int64\n\t\tsourceColumn: Part\n\n"
        "\tcolumn Chunk\n\t\tdataType: string\n\t\tsourceColumn: Chunk\n",
        encoding="utf-8",
    )
    assert main([str(proj), "--embed"]) == 0
    assert "Updated the TrailsBI table" in capsys.readouterr().out
    assert f"annotation {MARKER} =" in old.read_text(encoding="utf-8")


def test_first_run_leaves_an_earlier_table_out_of_the_analysis(fixtures, tmp_path, build, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    _, before = build(proj)
    old = proj / "Shop.SemanticModel/definition/tables/TrailsBI.tmdl"
    old.write_text(
        "table TrailsBI\n\n\tcolumn Part\n\t\tdataType: int64\n\t\tsourceColumn: Part\n\n"
        "\tcolumn Chunk\n\t\tdataType: string\n\t\tsourceColumn: Chunk\n",
        encoding="utf-8",
    )
    page = run(proj, output=tmp_path / "first.html", embed_data=True)
    capsys.readouterr()
    first = re.search(
        r'<script id="data" type="application/json">(.*?)</script>', page.read_text("utf-8"), re.S
    )
    assert json.loads(first.group(1))["meta"]["counts"] == before["meta"]["counts"]
