# SPDX-License-Identifier: Apache-2.0
import json

import pytest

from trailsbi.project import ProjectError, resolve_project


def test_pbip_file(fixtures):
    p = resolve_project(fixtures / "Shop" / "Shop.pbip")
    assert p.name == "Shop"
    assert p.report_dir.name == "Shop.Report"
    assert p.model_dir.name == "Shop.SemanticModel"
    assert p.external_model is None


def test_folder_with_one_pbip(fixtures):
    p = resolve_project(fixtures / "Shop")
    assert p.report_dir.name == "Shop.Report"


def test_report_folder(fixtures):
    p = resolve_project(fixtures / "TwoProjects" / "Alpha.Report")
    assert p.name == "Alpha"
    assert p.model_dir.name == "Alpha.SemanticModel"


def test_folder_with_several_projects_is_refused(fixtures):
    with pytest.raises(ProjectError) as err:
        resolve_project(fixtures / "TwoProjects")
    msg = str(err.value)
    assert "2 Power BI projects" in msg
    assert "Alpha.pbip" in msg and "Beta.pbip" in msg
    assert "one project at a time" in msg


def test_nested_projects_are_listed(fixtures):
    with pytest.raises(ProjectError) as err:
        resolve_project(fixtures)
    assert "Shop/Shop.pbip" in str(err.value)


def test_semantic_model_alone_is_refused(fixtures):
    with pytest.raises(ProjectError, match="semantic model on its own"):
        resolve_project(fixtures / "Shop" / "Shop.SemanticModel")


def test_missing_path(tmp_path):
    with pytest.raises(ProjectError, match="Not found"):
        resolve_project(tmp_path / "nope.pbip")


def test_other_file_is_refused(fixtures):
    with pytest.raises(ProjectError, match="Not a .pbip file"):
        resolve_project(fixtures / "Shop" / "Shop.Report" / "definition.pbir")


def test_live_connected_report(tmp_path):
    rep = tmp_path / "Live.Report"
    (rep / "definition" / "pages").mkdir(parents=True)
    conn = (
        "Data Source=powerbi://api.powerbi.com/v1.0/myorg/Finance;"
        "Initial Catalog=Finance Model;semanticmodelid=abc"
    )
    (rep / "definition.pbir").write_text(
        json.dumps({"version": "4.0", "datasetReference": {"byConnection": {"connectionString": conn}}})
    )
    (tmp_path / "Live.pbip").write_text(json.dumps({"artifacts": [{"report": {"path": "Live.Report"}}]}))
    p = resolve_project(tmp_path / "Live.pbip")
    assert p.model_dir is None
    assert p.external_model["label"] == "Finance Model"
    assert p.external_model["workspace"] == "Finance"


def _report(folder, name, model=None):
    rep = folder / f"{name}.Report"
    (rep / "definition" / "pages").mkdir(parents=True)
    ref = {"byPath": {"path": f"../{model}.SemanticModel"}} if model else {}
    (rep / "definition.pbir").write_text(json.dumps({"version": "4.0", "datasetReference": ref}))
    return rep


def test_folder_with_one_report_and_no_pbip(tmp_path):
    _report(tmp_path, "Solo")
    (tmp_path / "Solo.SemanticModel").mkdir()
    p = resolve_project(tmp_path)
    assert p.report_dir.name == "Solo.Report"
    assert p.model_dir.name == "Solo.SemanticModel"  # paired by name


def test_folder_with_several_reports_is_refused(tmp_path):
    _report(tmp_path, "A")
    _report(tmp_path, "B")
    with pytest.raises(ProjectError, match="2 Power BI projects"):
        resolve_project(tmp_path)


def test_dataset_folder_is_refused(tmp_path):
    (tmp_path / "Old.Dataset").mkdir()
    with pytest.raises(ProjectError, match="semantic model on its own"):
        resolve_project(tmp_path / "Old.Dataset")


def test_single_nested_pbip_is_found(fixtures, tmp_path):
    import shutil

    shutil.copytree(fixtures / "Shop", tmp_path / "repo" / "reports" / "Shop")
    p = resolve_project(tmp_path / "repo")
    assert p.name == "Shop"


def test_long_lists_are_cut_short(tmp_path):
    for i in range(12):
        (tmp_path / f"P{i:02d}.pbip").write_text("{}")
    with pytest.raises(ProjectError) as err:
        resolve_project(tmp_path)
    assert "12 Power BI projects" in str(err.value)
    assert "...and 2 more" in str(err.value)


def test_pbip_without_report(tmp_path):
    (tmp_path / "Empty.pbip").write_text(json.dumps({"artifacts": []}))
    with pytest.raises(ProjectError, match="does not point to a report"):
        resolve_project(tmp_path / "Empty.pbip")


def test_model_path_that_does_not_exist(tmp_path):
    _report(tmp_path, "Lost", model="Gone")
    p = resolve_project(tmp_path / "Lost.Report")
    assert p.model_dir is None
    assert p.external_model["label"] == "Unknown semantic model"
    assert any("Gone.SemanticModel" in n for n in p.notes)


def test_model_outside_the_project_folder_keeps_paths_out(tmp_path):
    shared = tmp_path / "shared" / "Central.SemanticModel"
    shared.mkdir(parents=True)
    proj = tmp_path / "proj"
    rep = proj / "Thin.Report"
    (rep / "definition" / "pages").mkdir(parents=True)
    ref = {"byPath": {"path": "../../shared/Central.SemanticModel"}}
    (rep / "definition.pbir").write_text(json.dumps({"datasetReference": ref}))
    p = resolve_project(rep)
    assert p.label(p.model_dir) == ("Central", "Central.SemanticModel")
