# SPDX-License-Identifier: Apache-2.0
"""Command line entry point: ``trailsbi [PROJECT] [-o OUTPUT] [--open]``."""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
import webbrowser
from collections import defaultdict
from pathlib import Path

from .ai_readiness import ai_readiness
from .brand import PRODUCT, VERSION
from .graph import build_graph, downstream_counts
from .health import health
from .model import Model, load_model_dir, model_diagram
from .project import Project, ProjectError, resolve_project
from .render import render_html
from .report import load_report_dir
from .utils import WARNINGS, warn

_COUNT_WORDS = {
    "model": ("semantic model", "semantic models"),
    "report": ("report", "reports"),
    "source": ("data source", "data sources"),
    "query": ("query/parameter", "queries/parameters"),
    "table": ("table", "tables"),
    "column": ("column", "columns"),
    "measure": ("measure", "measures"),
    "visual": ("visual", "visuals"),
    "page": ("page", "pages"),
}
_SEVERITY_WORDS = {3: ("error", "errors"), 2: ("warning", "warnings"), 1: ("info", "info")}


def _plural(n: int, words: tuple) -> str:
    return f"{n} {words[0] if n == 1 else words[1]}"


def build_parser() -> argparse.ArgumentParser:
    """The command line options."""
    ap = argparse.ArgumentParser(
        prog="trailsbi",
        description=f"{PRODUCT}: follow any field from source to visual. Builds one offline "
        "HTML page with the lineage, model, reports, health and AI readiness of a "
        "Power BI project.",
    )
    ap.add_argument("--version", action="version", version=f"{PRODUCT} {VERSION}")
    ap.add_argument(
        "project",
        nargs="?",
        default=".",
        help="a .pbip file, the folder that holds it, or a .Report folder (default: the current folder)",
    )
    ap.add_argument(
        "-o",
        "--output",
        help='where to write the HTML page (default: "TrailsBI Report - <project> - <date time>.html" '
        "in the current folder)",
    )
    ap.add_argument("--open", action="store_true", help="open the page in your browser")
    return ap


def _load(project: Project):
    """Reads the project's semantic model and report. Returns (models, reports) lists."""
    models, reports = [], []
    model_key = None
    if project.model_dir:
        label, rel = project.label(project.model_dir)
        print(f"  Semantic model: {rel}")
        model = Model()
        fmt = load_model_dir(project.model_dir, model)
        models.append(
            {"key": rel, "name": label, "rel": rel, "model": model, "format": fmt, "dir": project.model_dir}
        )
        model_key = rel
    for note in project.notes:
        warn(note)
    if project.report_dir:
        label, rel = project.label(project.report_dir)
        print(f"  Report:         {rel}")
        report = load_report_dir(project.report_dir)
        if report:
            external = project.external_model
            report.update(
                {
                    "key": rel,
                    "name": label,
                    "rel": rel,
                    "dir": project.report_dir,
                    "model": model_key,
                    "external": external,
                }
            )
            reports.append(report)
    return models, reports


def _summary(counts, graph, sections) -> str:
    lines = [
        "  " + ", ".join(_plural(counts[k], words) for k, words in _COUNT_WORDS.items()),
        f"  {len(graph.edges)} dependencies",
    ]
    tally = defaultdict(int)
    for rule in sections:
        tally[rule["severity"]] += len(rule["items"])
    failing = sum(1 for rule in sections if rule["items"])
    lines.append(
        f"  Health: {failing} of {len(sections)} rules have findings · "
        + ", ".join(_plural(tally[k], _SEVERITY_WORDS[k]) for k in (3, 2, 1))
    )
    missing = next((r for r in sections if r["id"] == "MISSING_FIELDS"), None)
    if missing and missing["items"]:
        lines.append(f"  Fields missing from the semantic model: {len(missing['items'])}")
    return "\n".join(lines)


def default_file_name(name: str, when: _dt.datetime) -> str:
    """'TrailsBI Report - <name> - <date time>.html'; the time uses no characters Windows refuses."""
    return f"TrailsBI Report - {name} - {when:%Y-%m-%d %H-%M}.html"


def _output_path(output, name: str, when: _dt.datetime) -> Path:
    """Where to write the page: the given file, or the default file name in the given folder."""
    default = default_file_name(name, when)
    if not output:
        return Path.cwd() / default
    out = Path(output).expanduser()
    return out / default if out.is_dir() else out


def run(project_path=".", output=None, open_page=False) -> Path:
    """Builds the page for one project and returns where it was written."""
    WARNINGS.clear()
    started = _dt.datetime.now()
    project = resolve_project(project_path)
    print(f"Scanning: {project.name}")
    models, reports = _load(project)

    graph, pages = build_graph(models, reports)
    downstream_counts(graph)
    sections = health(graph, models, reports)
    ai_rules = ai_readiness(graph, models, reports)

    counts = defaultdict(int)
    for node in graph.nodes.values():
        if not node.get("auto") and node.get("icon") != "allpages":  # report-level filters are not a page
            counts[node["type"]] += 1
    counts["model"] = len(models)
    counts["report"] = len(reports)
    meta = {
        "name": project.name,
        "generated": started.strftime("%Y-%m-%d %H:%M"),
        "modelFormat": ", ".join(sorted({m["format"] for m in models if m["format"]})) or "none",
        "reportFormat": ", ".join(sorted({r["format"] for r in reports})) or "none",
        "warnings": list(WARNINGS),
        "counts": counts,
        "models": [
            {
                "key": m["key"],
                "name": m["name"],
                "format": m.get("format"),
                "outline": getattr(m["model"], "outline", []),
                "live": getattr(m["model"], "live_ref", None),
                "liveId": m.get("live_src"),
                "diagram": model_diagram(getattr(m["model"], "bpa_inv", None)),
            }
            for m in models
        ],
        "reports": [
            {
                "key": r["key"],
                "name": r["name"],
                "model": r["model"],
                "external": (r["external"] or {}).get("label"),
            }
            for r in reports
        ],
    }

    out = _output_path(output, project.name, started)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(graph, pages, sections, meta, ai_rules), encoding="utf-8")

    print("\n" + _summary(counts, graph, sections))
    print(f"\nWrote {out}")
    if open_page:
        webbrowser.open(out.resolve().as_uri())
    return out


def main(argv=None) -> int:
    """Runs the command line and returns the exit code.

    0: the page was written. 1: a file could not be read or written.
    2: the path does not lead to exactly one project.
    """
    args = build_parser().parse_args(argv)
    # A Windows console or pipe may not be able to show every character in a
    # project name; print a replacement character rather than stop.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    try:
        run(args.project, args.output, args.open)
    except ProjectError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"\nCould not finish: {exc}", file=sys.stderr)
        return 1
    return 0
