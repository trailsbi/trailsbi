# SPDX-License-Identifier: Apache-2.0
"""Finds the report and semantic model that make up one Power BI project.

TrailsBI builds one project per run: a ``.pbip`` file, the folder that holds
it, or a ``.Report`` folder. The project's report is read together with the
semantic model it uses, wherever that model sits on disk. A report that is
live-connected to a published model is read on its own, and the published
model is shown as its source.
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
