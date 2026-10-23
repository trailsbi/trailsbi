# SPDX-License-Identifier: Apache-2.0
"""Adds the TrailsBI page to a report (part of ``trailsbi --embed``).

The page holds one TrailsBI visual over the whole page, bound to the Part and Chunk columns of
the TrailsBI table, so nobody has to import the visual, add a page or drag fields. It is hidden
in view mode: report authors see it in Power BI Desktop, report readers do not.

The visual travels inside the report, the way Power BI Desktop saves a visual imported from a
file (a "private" custom visual):

  <Report>/CustomVisuals/<guid>/package.json                        the .pbiviz file's entries,
  <Report>/CustomVisuals/<guid>/resources/<guid>.pbiviz.json        unpacked
  definition/report.json  resourcePackages: {name: <guid>, type: CustomVisual,
                          items: [{name/path: <guid>.pbiviz.json, type: CustomVisualMetadata}]}

Only reports in the PBIR format (a definition folder) are supported. Every file is written as
Power BI Desktop writes it: JSON with two-space indents. A report.json laid out differently is
not rewritten.
"""

from __future__ import annotations

import io
import json
import zipfile
from importlib.resources import files
from pathlib import Path

PAGE = "trailsbi"  # folder and name of the page, and of the visual on it
PAGE_TITLE = "TrailsBI"
WIDTH, HEIGHT = 1280, 720
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/{kind}/{ver}/schema.json"
DEFAULT_VERSIONS = {"page": "2.0.0", "visualContainer": "2.0.0", "pagesMetadata": "1.0.0"}


class PageError(Exception):
    """The page could not be added to this report."""


def bundled_visual():
    """The TrailsBI visual (.pbiviz) that ships with this package (read it with read_bytes();
    inside trailsbi.pyz it is not a file on disk)."""
    return files(__package__).joinpath("visual").joinpath("TrailsBI.pbiviz")


def visual_info(pbiviz) -> dict:
    """guid, version and the package's entries of a .pbiviz file (a path or a package resource)."""
    with zipfile.ZipFile(io.BytesIO(pbiviz.read_bytes())) as z:
        package = json.loads(z.read("package.json").decode("utf-8-sig"))
        entries = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    v = package["visual"]
    return {"guid": v["guid"], "version": v.get("version") or package.get("version", "0"), "entries": entries}


def _version_key(v: str) -> tuple:
    return tuple(int(p) if p.isdigit() else 0 for p in str(v).split("."))


def _dumps(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)  # Desktop ends files without a newline


def _read_json(path: Path, strict: bool = True):
    """The JSON in `path`. With `strict`, refuses a file Desktop did not lay out (so a rewrite
    would change more than what TrailsBI adds)."""
    text = path.read_text(encoding="utf-8-sig")
    data = json.loads(text)
    if strict and json.dumps(data, indent=2, ensure_ascii=False) != text.replace("\r\n", "\n").rstrip("\n"):
        raise PageError(
            f"{path.name} is not laid out the way Power BI Desktop writes it, so TrailsBI will not "
            "rewrite it. Open and save the project in Power BI Desktop, then run again."
        )
    return data


def _write_json(path: Path, value, like: Path | None = None) -> None:
    """Writes JSON as Desktop does, keeping the line ends of `like` (the file being replaced)."""
    text = _dumps(value)
    if like is not None and like.exists():
        old = like.read_bytes()
        if old.endswith(b"\n"):
            text += "\n"
        if b"\r\n" in old:
            text = text.replace("\n", "\r\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def _schema_version(def_dir: Path, kind: str, pattern: str) -> str:
    """The schema version this report already uses for `kind`, so the new files match what
    the user's Power BI Desktop writes; Microsoft's 2025 version when there is none to copy."""
    for f in sorted(def_dir.glob(pattern)):
        try:
            schema = json.loads(f.read_text(encoding="utf-8-sig")).get("$schema", "")
        except (OSError, ValueError):
            continue
        marker = f"/{kind}/"
        if marker in schema:
            return schema.split(marker, 1)[1].split("/", 1)[0]
    return DEFAULT_VERSIONS[kind]


def _install_visual(report_dir: Path, info: dict) -> tuple:
    """Unpacks the visual into CustomVisuals/<guid>/ unless the report has the same or a newer
    version already. Returns (version now in the report, whether it was written)."""
    target = report_dir / "CustomVisuals" / info["guid"]
    current = target / "package.json"
    if current.exists():
        try:
            have = json.loads(current.read_text(encoding="utf-8-sig"))["visual"].get("version", "0")
        except (OSError, ValueError, KeyError):
            have = "0"
        if _version_key(have) >= _version_key(info["version"]):
            return have, False
    for name, data in info["entries"].items():
        out = target / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    return info["version"], True


def _register_visual(report_json: Path, guid: str) -> bool:
    """Adds the visual to report.json's resourcePackages, as Desktop does. True if it changed."""
    data = _read_json(report_json)
    packages = data.setdefault("resourcePackages", [])
    if any(p.get("name") == guid and p.get("type") == "CustomVisual" for p in packages):
        return False
    item = f"{guid}.pbiviz.json"
    packages.append(
        {
            "name": guid,
            "type": "CustomVisual",
            "items": [{"name": item, "path": item, "type": "CustomVisualMetadata"}],
        }
    )
    _write_json(report_json, data, like=report_json)
    return True


def _field(table: str, column: str) -> dict:
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}},
        "queryRef": f"{table}.{column}",
        "nativeQueryRef": column,
    }


def page_files(def_dir: Path, guid: str, table: str) -> dict:
    """page.json and visual.json of the TrailsBI page, as {relative path: JSON value}."""
    page_ver = _schema_version(def_dir, "page", "pages/*/page.json")
    visual_ver = _schema_version(def_dir, "visualContainer", "pages/*/visuals/*/visual.json")
    page = {
        "$schema": SCHEMA.format(kind="page", ver=page_ver),
        "name": PAGE,
        "displayName": PAGE_TITLE,
        "displayOption": "FitToPage",
        "height": HEIGHT,
        "width": WIDTH,
        "visibility": "HiddenInViewMode",
    }
    visual = {
        "$schema": SCHEMA.format(kind="visualContainer", ver=visual_ver),
        "name": PAGE,
        "position": {"x": 0, "y": 0, "z": 0, "height": HEIGHT, "width": WIDTH},
        "visual": {
            "visualType": guid,
            "query": {
                "queryState": {
                    "part": {"projections": [_field(table, "Part")]},
                    "chunk": {"projections": [_field(table, "Chunk")]},
                }
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return {f"pages/{PAGE}/page.json": page, f"pages/{PAGE}/visuals/{PAGE}/visual.json": visual}


def _rebind(page_dir: Path, guid: str, table: str) -> None:
    """Points the TrailsBI visuals on an existing TrailsBI page at the table's current name;
    everything else on the page stays as the author left it."""
    for vf in sorted(page_dir.glob("visuals/*/visual.json")):
        try:
            data = _read_json(vf)
        except (PageError, ValueError):
            continue
        visual = data.get("visual") or {}
        if not str(visual.get("visualType", "")).lower().startswith("trailsbi"):
            continue
        state = (visual.get("query") or {}).get("queryState") or {}
        wanted = {"part": _field(table, "Part"), "chunk": _field(table, "Chunk")}
        changed = False
        for role, field in wanted.items():
            projections = (state.get(role) or {}).get("projections") or []
            if projections and projections[0].get("field") != field["field"]:
                projections[0].update(field)
                changed = True
        if changed:
            _write_json(vf, data, like=vf)


def check(report_dir: Path | None) -> None:
    """Raises PageError when the TrailsBI page cannot be added to this report, before anything
    in the project (the model included) is changed."""
    if report_dir is None:
        raise PageError("this project has no report folder.")
    def_dir = report_dir / "definition"
    if not (def_dir / "pages").is_dir() or not (def_dir / "report.json").exists():
        raise PageError(
            "the report is not saved in the PBIR format (a definition folder). To have it added, in "
            "Power BI Desktop: File, Options and settings, Options, Preview features, turn on 'Store "
            "reports using enhanced metadata format (PBIR)', save the project and run again. Or add "
            "the visual by hand: https://trailsbi.com/#visual"
        )
    _read_json(def_dir / "report.json")
    pages_json = def_dir / "pages" / "pages.json"
    if pages_json.exists():
        _read_json(pages_json)


def add_page(report_dir: Path | None, table: str, pbiviz=None) -> dict:
    """Adds the TrailsBI page and visual to the report at `report_dir`.

    Returns what was done: {"page": "added" | "kept", "visual": version, "visual_written": bool}.
    An existing TrailsBI page is kept as it is (it may have been moved or resized); only the
    visual is brought up to date.
    """
    check(report_dir)
    def_dir = report_dir / "definition"
    info = visual_info(pbiviz or bundled_visual())
    pages_json = def_dir / "pages" / "pages.json"
    pages_meta = _read_json(pages_json) if pages_json.exists() else None

    version, written = _install_visual(report_dir, info)
    _register_visual(def_dir / "report.json", info["guid"])

    page_dir = def_dir / "pages" / PAGE
    if page_dir.exists():
        _rebind(page_dir, info["guid"], table)
        return {"page": "kept", "visual": version, "visual_written": written}
    for rel, value in page_files(def_dir, info["guid"], table).items():
        _write_json(def_dir / rel, value)
    if pages_meta is not None:
        order = pages_meta.setdefault("pageOrder", [])
        if PAGE not in order:
            order.append(PAGE)
            _write_json(pages_json, pages_meta, like=pages_json)
    return {"page": "added", "visual": version, "visual_written": written}
