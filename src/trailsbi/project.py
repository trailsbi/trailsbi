# SPDX-License-Identifier: Apache-2.0
"""Finds the reports and semantic models TrailsBI reads.

A run covers one project (a ``.pbip`` file, the folder that holds it, or a
``.Report`` folder) or a whole workspace: a folder with several projects, such
as a Git folder a Power BI or Fabric workspace syncs to. Each report is read
together with the semantic model it uses, wherever that model sits on disk. A
report that is live-connected to a published model uses the workspace's own
copy of that model when the folder has it, and is otherwise read on its own,
with the published model shown as its source.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .model import connection_parts
from .utils import read_json

ITEM_SUFFIX = re.compile(r"\.(Report|SemanticModel|Dataset)$", re.I)
_SKIP_DIRS = {".git", ".github", ".vs", ".vscode", "node_modules", "__pycache__"}
_SEARCH_DEPTH = 4  # how far below the given folder to look for a .pbip
_WORKSPACE_DEPTH = 6  # how far below a workspace folder to look for reports and models
_LIST_LIMIT = 10  # projects listed when a folder holds several


class ProjectError(Exception):
    """The path does not lead to exactly one Power BI project."""


@dataclass
class Project:
    """One report and the semantic model it uses."""

    name: str
    root: Path  # the folder the project lives in
    report_dir: Path | None = None
    model_dir: Path | None = None  # None when the model is published elsewhere
    external_model: dict | None = None  # what is known about a published model
    notes: list = field(default_factory=list)  # things worth telling the user

    def label(self, item_dir: Path) -> tuple:
        """(display name, path relative to the project folder) for a report or model folder."""
        try:
            rel = item_dir.relative_to(self.root).as_posix()
        except ValueError:  # outside the project folder: keep the full path out of the page
            rel = item_dir.name
        return ITEM_SUFFIX.sub("", item_dir.name), rel


def item_name(item_dir: Path) -> str:
    """Folder name without the .Report / .SemanticModel suffix."""
    return ITEM_SUFFIX.sub("", item_dir.name)


def _published_model(ref: dict) -> dict:
    """What a byConnection reference says about the published model a report uses."""
    parts = connection_parts(ref.get("connectionString") or "")
    name = parts.get("initial catalog")
    server = parts.get("data source", "")
    ws = server.rsplit("/", 1)[-1] if server.startswith("powerbi://") else ""
    ident = parts.get("semanticmodelid") or ref.get("pbiModelDatabaseName") or ""
    label = name or (f"Semantic model {ident[:8]}…" if ident else "Published semantic model")
    return {
        "label": label,
        "workspace": ws,
        "id": ident,
        "server": "" if server.startswith("powerbi://") else server,
        "cube": parts.get("cube", ""),
    }


def _unknown_model() -> dict:
    return {"label": "Unknown semantic model", "workspace": "", "id": ""}


def _from_report(report_dir: Path, name: str, root: Path) -> Project:
    """The project around a report folder: the report plus the model it is bound to."""
    project = Project(name=name, root=root, report_dir=report_dir)
    pbir = report_dir / "definition.pbir"
    ref = ((read_json(pbir) or {}).get("datasetReference") or {}) if pbir.exists() else {}

    by_path = (ref.get("byPath") or {}).get("path")
    if by_path:
        model_dir = (report_dir / by_path).resolve()
        if model_dir.is_dir():
            project.model_dir = model_dir
            return project
        project.notes.append(f"{report_dir.name} points to {by_path}, which was not found.")
    if ref.get("byConnection"):
        project.external_model = _published_model(ref["byConnection"])
        return project

    # No usable reference: a model with the same name next to the report.
    twin = report_dir.parent / f"{item_name(report_dir)}.SemanticModel"
    if twin.is_dir():
        project.model_dir = twin.resolve()
    else:
        project.notes.append(f"{report_dir.name}: could not tell which semantic model it uses.")
        project.external_model = _unknown_model()
    return project


def _from_pbip(pbip: Path) -> Project:
    root = pbip.parent
    reports = []
    for artifact in (read_json(pbip) or {}).get("artifacts", []):
        path = (artifact.get("report") or {}).get("path")
        if path and (root / path).is_dir():
            reports.append((root / path).resolve())
    if not reports and (root / f"{pbip.stem}.Report").is_dir():
        reports.append((root / f"{pbip.stem}.Report").resolve())
    if not reports:
        raise ProjectError(f"{pbip.name} does not point to a report folder that exists.")
    return _from_report(reports[0], pbip.stem, root)


def _find_pbips(folder: Path, depth: int = _SEARCH_DEPTH) -> list:
    """Every .pbip file at most `depth` folders below `folder`."""
    found = []
    base = len(folder.parts)
    for dirpath, dirnames, filenames in os.walk(folder):
        here = Path(dirpath)
        found += [here / f for f in sorted(filenames) if f.lower().endswith(".pbip")]
        dirnames[:] = [
            d
            for d in sorted(dirnames)
            if d not in _SKIP_DIRS
            and not d.startswith(".")
            and not ITEM_SUFFIX.search(d)
            and len(here.parts) - base < depth
        ]
    return found


def _too_many(folder: Path, found: list) -> ProjectError:
    shown = "\n".join(f"  {p.relative_to(folder).as_posix()}" for p in found[:_LIST_LIMIT])
    more = f"\n  ...and {len(found) - _LIST_LIMIT} more" if len(found) > _LIST_LIMIT else ""
    return ProjectError(
        f"This folder holds {len(found)} Power BI projects:\n{shown}{more}\n\n"
        "TrailsBI builds one project at a time. Run it on the one you want, for example:\n"
        f'  trailsbi "{found[0]}"\n\n'
        "Workspace lineage is coming soon."
    )


def resolve_project(target) -> Project:
    """The one project that `target` (a .pbip file, its folder or a .Report folder) names.

    Raises ProjectError when the path leads to no project or to several.
    """
    path = Path(target).expanduser().resolve()
    if not path.exists():
        raise ProjectError(f"Not found: {path}")

    if path.is_file():
        if path.suffix.lower() != ".pbip":
            raise ProjectError(
                f"Not a .pbip file: {path}\nPoint TrailsBI at a .pbip file or the folder that holds it."
            )
        return _from_pbip(path)

    low = path.name.lower()
    if low.endswith(".report"):
        return _from_report(path, item_name(path), path.parent)
    if low.endswith((".semanticmodel", ".dataset")):
        raise ProjectError(
            f"{path.name} is a semantic model on its own. Point TrailsBI at the .pbip file, "
            "or the .Report folder, of the report that uses it."
        )

    pbips = sorted(f for f in path.iterdir() if f.is_file() and f.suffix.lower() == ".pbip")
    if len(pbips) == 1:
        return _from_pbip(pbips[0])
    if len(pbips) > 1:
        raise _too_many(path, pbips)

    reports = sorted(d for d in path.iterdir() if d.is_dir() and d.name.lower().endswith(".report"))
    if len(reports) == 1:
        return _from_report(reports[0].resolve(), item_name(reports[0]), path)
    if len(reports) > 1:
        raise _too_many(path, reports)

    deeper = _find_pbips(path)
    if len(deeper) == 1:
        return _from_pbip(deeper[0])
    if len(deeper) > 1:
        raise _too_many(path, deeper)
    raise ProjectError(f"No Power BI project (.pbip) found in {path}")


# ---------------------------------------------------------------- workspaces


@dataclass
class Workspace:
    """Every report and semantic model in a folder.

    reports: (report folder, model folder or None, published model or None) for each report.
    models: every semantic model folder, including those no report here uses.
    """

    name: str
    root: Path
    models: list = field(default_factory=list)
    reports: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    names: dict = field(default_factory=dict)  # {folder: (display name, path)}, set by the CLI

    def label(self, item_dir: Path) -> tuple:
        if item_dir in self.names:
            return self.names[item_dir]
        try:
            rel = item_dir.relative_to(self.root).as_posix()
        except ValueError:
            rel = item_dir.name
        return display_name(item_dir), rel


def display_name(item_dir: Path) -> str:
    """The name Power BI shows for a report or model: the .platform file's, else the folder's."""
    plat = item_dir / ".platform"
    meta = ((read_json(plat) or {}).get("metadata") or {}) if plat.exists() else {}
    return (meta.get("displayName") or "").strip() or item_name(item_dir)


def _find_items(folder: Path, depth: int = _WORKSPACE_DEPTH) -> tuple:
    """(report folders, model folders) at most `depth` folders below `folder`."""
    reports, models = [], []
    base = len(folder.parts)
    for dirpath, dirnames, _files in os.walk(folder):
        here = Path(dirpath)
        keep = []
        for d in sorted(dirnames):
            low = d.lower()
            if low.endswith(".report"):
                reports.append((here / d).resolve())
            elif low.endswith((".semanticmodel", ".dataset")):
                models.append((here / d).resolve())
            elif d not in _SKIP_DIRS and not d.startswith(".") and len(here.parts) - base < depth:
                keep.append(d)
        dirnames[:] = keep
    return reports, models


def _bind(report_dir: Path, models: list, by_name: dict, notes: list) -> tuple:
    """(model folder or None, published model or None) for one report in a workspace."""
    pbir = report_dir / "definition.pbir"
    ref = ((read_json(pbir) or {}).get("datasetReference") or {}) if pbir.exists() else {}
    by_path = (ref.get("byPath") or {}).get("path")
    if by_path:
        model_dir = (report_dir / by_path).resolve()
        if model_dir.is_dir():
            return model_dir, None
        notes.append(f"{report_dir.name} points to {by_path}, which was not found.")
    if ref.get("byConnection"):
        pub = _published_model(ref["byConnection"])
        parts = connection_parts(ref["byConnection"].get("connectionString") or "")
        name = (parts.get("initial catalog") or ref["byConnection"].get("name") or "").strip().lower()
        cands = by_name.get(name, []) if name else []
        if cands:
            # the copy in the report's own folder first, then the nearest one
            near = sorted(cands, key=lambda m: (m.parent != report_dir.parent, len(m.parts)))
            return near[0], None
        return None, pub
    twin = report_dir.parent / f"{item_name(report_dir)}.SemanticModel"
    if twin.is_dir():
        return twin.resolve(), None
    notes.append(f"{report_dir.name}: could not tell which semantic model it uses.")
    return None, _unknown_model()


def find_workspace(folder: Path) -> Workspace | None:
    """The workspace in `folder` when it holds more than one report or model; None otherwise."""
    reports, models = _find_items(folder)
    if len(reports) + len(models) <= 1:
        return None
    ws = Workspace(name=folder.name or str(folder), root=folder)
    by_name: dict = {}
    for m in models:
        by_name.setdefault(display_name(m).lower(), []).append(m)
    bound = []
    for r in reports:
        model_dir, pub = _bind(r, models, by_name, ws.notes)
        bound.append((r, model_dir, pub))
        if model_dir and model_dir not in models:  # a model outside the folder that a report points to
            models.append(model_dir)
    ws.models = models
    ws.reports = bound
    if len(reports) == 1 and len(models) == 1 and bound[0][1] == models[0]:
        return None  # one ordinary project
    if len(reports) == 1 and not models:
        return None
    return ws


def resolve(target):
    """A Project, or a Workspace when `target` is a folder with several reports or models."""
    path = Path(target).expanduser().resolve()
    if path.is_dir() and path.name.lower().endswith((".semanticmodel", ".dataset")):
        return Workspace(name=item_name(path), root=path.parent, models=[path])  # a model on its own
    if path.is_dir() and not ITEM_SUFFIX.search(path.name):
        ws = find_workspace(path)
        if ws:
            return ws
    return resolve_project(target)
