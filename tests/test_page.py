# SPDX-License-Identifier: Apache-2.0
"""trailsbi --embed: the TrailsBI page and visual added to the report."""

import io
import json
import shutil
import zipfile

from trailsbi.cli import main
from trailsbi.report_page import PAGE, bundled_visual, visual_info

GUID = visual_info(bundled_visual())["guid"]


def copy(fixtures, tmp_path, name):
    shutil.copytree(fixtures / name, tmp_path / name)
    return tmp_path / name


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_page_and_visual_are_added(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    rep = proj / "Shop.Report"
    assert main([str(proj), "--embed"]) == 0
    assert "Added the TrailsBI page" in capsys.readouterr().out

    # the visual, unpacked the way Desktop saves a visual imported from a file
    vdir = rep / "CustomVisuals" / GUID
    assert read(vdir / "package.json")["visual"]["guid"] == GUID
    assert (vdir / "resources" / f"{GUID}.pbiviz.json").is_file()
    packages = read(rep / "definition/report.json")["resourcePackages"]
    assert packages == [
        {
            "name": GUID,
            "type": "CustomVisual",
            "items": [
                {"name": f"{GUID}.pbiviz.json", "path": f"{GUID}.pbiviz.json", "type": "CustomVisualMetadata"}
            ],
        }
    ]

    page = read(rep / f"definition/pages/{PAGE}/page.json")
    assert page["visibility"] == "HiddenInViewMode" and page["displayName"] == "TrailsBI"
    visual = read(rep / f"definition/pages/{PAGE}/visuals/{PAGE}/visual.json")
    assert visual["visual"]["visualType"] == GUID
    state = visual["visual"]["query"]["queryState"]
    assert state["part"]["projections"][0]["queryRef"] == "TrailsBI.Part"
    assert state["chunk"]["projections"][0]["field"]["Column"]["Property"] == "Chunk"
    assert read(rep / "definition/pages/pages.json")["pageOrder"][-1] == PAGE


def test_the_page_is_left_out_of_the_analysis(fixtures, tmp_path, build):
    proj = copy(fixtures, tmp_path, "Shop")
    _, before = build(proj)
    assert main([str(proj), "--embed"]) == 0
    _, after = build(proj)
    assert after["meta"]["counts"] == before["meta"]["counts"]
    assert after["health"] == before["health"]


def test_running_again_keeps_the_page_and_one_package(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    rep = proj / "Shop.Report"
    assert main([str(proj), "--embed"]) == 0
    page_file = rep / f"definition/pages/{PAGE}/page.json"
    moved = read(page_file)
    moved["displayName"] = "Lineage (dev)"  # the author renamed it in Desktop
    page_file.write_text(json.dumps(moved, indent=2), encoding="utf-8")
    capsys.readouterr()
    assert main([str(proj), "--embed"]) == 0
    assert "already in" in capsys.readouterr().out
    assert read(page_file)["displayName"] == "Lineage (dev)"
    assert len(read(rep / "definition/report.json")["resourcePackages"]) == 1
    assert read(rep / "definition/pages/pages.json")["pageOrder"].count(PAGE) == 1


def test_an_older_visual_in_the_report_is_updated(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    rep = proj / "Shop.Report"
    assert main([str(proj), "--embed"]) == 0
    pkg = rep / "CustomVisuals" / GUID / "package.json"
    old = read(pkg)
    old["visual"]["version"] = "0.0.1.0"
    pkg.write_text(json.dumps(old), encoding="utf-8")
    capsys.readouterr()
    assert main([str(proj), "--embed"]) == 0
    assert "Updated the TrailsBI visual" in capsys.readouterr().out
    assert read(pkg)["visual"]["version"] == visual_info(bundled_visual())["version"]


def test_the_page_uses_the_tables_current_name(fixtures, tmp_path):
    proj = copy(fixtures, tmp_path, "Shop")
    assert main([str(proj), "--embed"]) == 0
    tables = proj / "Shop.SemanticModel/definition/tables"
    text = (
        (tables / "TrailsBI.tmdl")
        .read_text(encoding="utf-8")
        .replace("table TrailsBI", "table 'Lineage data'")
    )
    (tables / "TrailsBI.tmdl").write_text(text, encoding="utf-8")
    assert main([str(proj), "--embed"]) == 0
    visual = read(proj / f"Shop.Report/definition/pages/{PAGE}/visuals/{PAGE}/visual.json")
    proj_ = visual["visual"]["query"]["queryState"]["part"]["projections"][0]
    assert proj_["queryRef"] == "Lineage data.Part"
    assert proj_["field"]["Column"]["Expression"]["SourceRef"]["Entity"] == "Lineage data"


def test_new_files_follow_the_reports_schema_versions(fixtures, tmp_path):
    proj = copy(fixtures, tmp_path, "Shop")
    pj = proj / "Shop.Report/definition/pages/overview/page.json"
    data = read(pj)
    data["$schema"] = (
        "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.3.0/schema.json"
    )
    pj.write_text(json.dumps(data, indent=2), encoding="utf-8")
    assert main([str(proj), "--embed"]) == 0
    assert "/page/1.3.0/" in read(proj / f"Shop.Report/definition/pages/{PAGE}/page.json")["$schema"]


def test_legacy_report_gets_the_table_and_a_reason(fixtures, tmp_path, capsys):
    """An older (non-PBIR) report: the table is written, the page is left out with a reason."""
    proj = copy(fixtures, tmp_path, "Legacy")
    report = proj / "Legacy.Report/report.json"
    before = report.read_bytes()
    assert main([str(proj), "--embed"]) == 0
    out = capsys.readouterr().out
    assert "Added the TrailsBI table" in out and "Did not add the TrailsBI page" in out and "PBIR" in out
    assert report.read_bytes() == before
    assert not (proj / "Legacy.Report/CustomVisuals").exists()


def test_report_json_in_another_layout_is_not_rewritten(fixtures, tmp_path, capsys):
    proj = copy(fixtures, tmp_path, "Shop")
    rep = proj / "Shop.Report"
    rj = rep / "definition/report.json"
    rj.write_text(json.dumps(read(rj), indent=4), encoding="utf-8")
    before = rj.read_bytes()
    assert main([str(proj), "--embed"]) == 0
    out = capsys.readouterr().out
    assert "Did not add the TrailsBI page" in out and "will not rewrite it" in out
    assert rj.read_bytes() == before
    assert not (rep / "CustomVisuals").exists() and not (rep / f"definition/pages/{PAGE}").exists()
    assert (proj / "Shop.SemanticModel/definition/tables/TrailsBI.tmdl").exists()


def test_bundled_visual_is_a_pbiviz():
    with zipfile.ZipFile(io.BytesIO(bundled_visual().read_bytes())) as z:
        names = z.namelist()
    assert "package.json" in names and f"resources/{GUID}.pbiviz.json" in names
    assert len(GUID) <= 20  # Desktop puts it twice in a path that Windows caps at 256 characters
