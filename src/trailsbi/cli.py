# SPDX-License-Identifier: Apache-2.0
"""Command line entry point: ``trailsbi [PROJECT] [-o OUTPUT] [--open] [--embed]``."""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import re
import sys
import webbrowser
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from .ai_readiness import ai_readiness
from .brand import PRODUCT, VERSION
from .embed import EmbedError, adopt, embed
from .graph import build_graph, downstream_counts
from .health import health
from .model import Model, load_model_dir, model_diagram
from .project import Project, ProjectError, Workspace, resolve
from .render import page_data, render_html
from .report import load_report_dir
from .report_page import PageError, add_page
from .report_page import check as check_page
from .utils import WARNINGS, warn
from .workspace import SelectionError, build_items, default_scope, labels, list_lines, select

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
        nargs="*",
        default=["."],
        help="a .pbip file, the folder that holds it, a .Report folder, or a folder with several "
        "projects for a workspace page; give several folders to read workspaces together, such as "
        "one with reports and one with the semantic models they use (default: the current folder)",
    )
    ap.add_argument(
        "-o",
        "--output",
        help='where to write the HTML page (default: "TrailsBI Report - <project> - <date time>.html" '
        "in the current folder)",
    )
    ap.add_argument("--open", action="store_true", help="open the page in your browser")
    ap.add_argument(
        "--embed",
        action="store_true",
        help="show the report inside Power BI: write its data into the project's semantic model as "
        "a hidden TrailsBI table, and add a hidden TrailsBI page to the report with the TrailsBI "
        "visual on it. Close the project in Power BI Desktop first. The HTML page is then written "
        "only when -o or --open is given.",
    )
    sel = ap.add_argument_group(
        "choosing what to build in a workspace folder",
        "Without these the whole folder is built. A name may be the display name, the path inside "
        "the folder or the folder name, with or without the .SemanticModel / .Report suffix, and "
        "may use * wildcards. Repeat a flag or separate names with commas.",
    )
    sel.add_argument(
        "-w",
        "--workspace",
        action="append",
        metavar="NAME",
        help="build the reports and models of this workspace",
    )
    sel.add_argument("-m", "--model", action="append", metavar="NAME", help="build this semantic model")
    sel.add_argument("-r", "--report", action="append", metavar="NAME", help="build this report")
    sel.add_argument(
        "--with-reports", action="store_true", help="also build every report on the chosen semantic models"
    )
    sel.add_argument(
        "--include",
        metavar="FILE",
        help='a JSON file naming what to build, {"models": [...], "reports": [...]}: '
        "the same file the page's Scope menu saves",
    )
    sel.add_argument(
        "--list", action="store_true", help="list the semantic models and reports in the folder, then stop"
    )
    sel.add_argument(
        "--split",
        action="store_true",
        help="write one page per semantic model with the reports that use it, into the folder -o names",
    )
    return ap


def _load(target):
    """Reads the semantic models and reports of a project or workspace. Returns (models, reports)."""
    if isinstance(target, Project):
        model_dirs = [target.model_dir] if target.model_dir else []
        items = [(target.report_dir, target.model_dir, target.external_model)] if target.report_dir else []
    else:
        model_dirs, items = target.models, target.reports
    workspace = isinstance(target, Workspace)
    models, reports, key_of = [], [], {}
    for model_dir in model_dirs:
        label, rel = target.label(model_dir)
        print(f"  Semantic model: {rel}")
        model = Model()
        try:
            fmt = load_model_dir(model_dir, model)
        except Exception as exc:  # one broken model should not stop a whole workspace
            if not workspace:
                raise
            warn(f"Could not read the semantic model {rel}: {exc}")
            continue
        models.append(
            {
                "key": rel,
                "name": label,
                "rel": rel,
                "model": model,
                "format": fmt,
                "dir": model_dir,
                "space": target.space_of(model_dir) if workspace else "",
            }
        )
        key_of[model_dir] = rel
    for note in target.notes:
        warn(note)
    for report_dir, model_dir, published in items:
        external = published
        label, rel = target.label(report_dir)
        model_key = key_of.get(model_dir) if model_dir else None
        if model_dir and not model_key:  # its model was left out of the build (or could not be read)
            external = {
                "label": target.label(model_dir)[0],
                "workspace": target.space_of(model_dir) if workspace else "",
                "id": "",
            }
        uses = f" (uses {target.label(model_dir)[0]})" if workspace and model_key else ""
        if workspace and not model_key and external:
            uses = f" (live: {external.get('label')})"
        print(f"  Report:         {rel}{uses}")
        try:
            report = load_report_dir(report_dir)
        except Exception as exc:
            if not workspace:
                raise
            warn(f"Could not read the report {rel}: {exc}")
            continue
        if report:
            report.update(
                {
                    "key": rel,
                    "name": label,
                    "rel": rel,
                    "dir": report_dir,
                    "model": model_key,
                    "external": None if model_key else external,
                    "space": target.space_of(report_dir) if workspace else "",
                }
            )
            reports.append(report)
    return models, reports


def _expand(targets: list) -> list:
    """Folder names with * or ?, which the Windows command prompt passes on as typed."""
    out = []
    for t in targets:
        hits = sorted(p for p in glob.glob(t) if Path(p).is_dir()) if any(c in t for c in "*?") else []
        out += hits or [t]
    return out


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


def run(
    project_path=".",
    output=None,
    open_page=False,
    embed_data=False,
    models=None,
    reports=None,
    include=None,
    with_reports=False,
    list_only=False,
    workspaces=None,
    split=False,
) -> Path | None:
    """Builds the page for one project and returns where it was written.

    With `embed_data`, also writes the page data into the project's semantic model and adds the
    TrailsBI page and visual to the report (when the report can take them; otherwise says why).
    The HTML page itself is then written only when `output` or `open_page` asks for it.
    """
    WARNINGS.clear()
    started = _dt.datetime.now()
    project = resolve(project_path)
    workspace = isinstance(project, Workspace)
    chosen = False
    if workspace:
        project.names = labels(project.models, project.rel)
        project.names.update(labels([r for r, _m, _p in project.reports], project.rel))
        rlabels = {r: project.names[r] for r, _m, _p in project.reports}
        mlabels = {m: project.names[m] for m in project.models}
        if list_only:
            print(f"Workspace: {project.name}")
            print("\n".join(list_lines(project, mlabels, rlabels)))
            return None
        try:
            chosen = select(project, mlabels, rlabels, models, reports, include, with_reports, workspaces)
        except SelectionError as exc:
            raise ProjectError(str(exc)) from exc
    elif list_only or models or reports or include:
        if list_only:
            print(f"{project.name} is one project:")
            if project.model_dir:
                print(f"  Semantic model: {project.label(project.model_dir)[0]}")
            if project.report_dir:
                print(f"  Report:         {project.label(project.report_dir)[0]}")
            return None
        warn("--model, --report and --include choose within a workspace folder; this is one project.")
    if split and not workspace:
        warn("--split makes one page per semantic model in a workspace folder; this is one project.")
        split = False
    if split and embed_data:
        raise ProjectError("--split and --embed do not go together: --embed works on one report at a time.")
    if workspace and embed_data:
        raise ProjectError(
            f"{project.name} holds {len(project.reports)} reports and "
            f"{len(project.models)} semantic models.\n"
            "--embed adds TrailsBI to one report at a time: run it on that report's .pbip file or folder."
        )
    no_page = None
    if embed_data:
        try:
            check_page(project.report_dir)  # before anything in the project changes
        except PageError as exc:
            no_page = str(exc)
        adopt(project.model_dir)  # an unmarked TrailsBI table from the preview: leave it out from now on
    if split:
        return _split(project, chosen, started, output, open_page)
    return _build(project, workspace, chosen, started, output, open_page, embed_data, no_page)


def _groups(ws: Workspace) -> list:
    """(name, model folders, report entries) for each page --split writes: a semantic model with
    the reports that use it, then the reports on each model the folders do not hold."""
    out = []
    for m in ws.models:
        out.append((ws.label(m)[0], [m], [r for r in ws.reports if r[1] == m]))
    published = defaultdict(list)
    for r in ws.reports:
        if r[1] is None:
            published[(r[2] or {}).get("label") or "Unknown semantic model"].append(r)
    for label, rs in sorted(published.items()):
        out.append((f"{label} (published)", [], rs))
    return out


def _split(project: Workspace, chosen, started, output, open_page) -> Path:
    """Writes one page per semantic model and its reports, into one folder; returns the folder."""
    if output and Path(output).suffix.lower() in (".html", ".htm"):
        raise ProjectError("With --split, -o is the folder to write the pages into, not an .html file.")
    folder = (
        Path(output).expanduser() if output else Path.cwd() / default_file_name(project.name, started)[:-5]
    )
    folder.mkdir(parents=True, exist_ok=True)
    groups = _groups(project)
    print(
        f"Splitting {project.name} into {len(groups)} pages, one per semantic model with its reports"
        + (" (as chosen)" if chosen else "")
    )
    for note in project.notes:
        warn(note)
    used = set()
    for name, ms, rs in groups:
        dirs = ms + [r[0] for r in rs]
        spaces = [sp for sp in project.spaces if any(project.space_of(d) == sp[0] for d in dirs)]
        sub = replace(project, name=name, models=ms, reports=rs, notes=[], spaces=spaces)
        stem = _safe_name(name)
        n = 2
        while stem.lower() in used:
            stem = f"{_safe_name(name)} ({n})"
            n += 1
        used.add(stem.lower())
        print("\n" + "-" * 60)
        several = len(ms) + len(rs) > 2 or len(rs) > 1  # else an ordinary one-report page
        _build(sub, several, chosen, started, folder / f"{stem}.html", False, False, None, scope_all=True)
    print(f"\nWrote {len(groups)} pages to {folder}")
    if open_page:
        webbrowser.open(folder.resolve().as_uri())
    return folder


def _safe_name(name: str) -> str:
    """A page name as a file name Windows accepts."""
    return re.sub(r'[\\/:*?"<>|]+', "-", name).strip(" .-") or "page"


def _build(
    project, workspace, chosen, started, output, open_page, embed_data, no_page, scope_all=False
) -> Path | None:
    """Reads the chosen reports and models and writes the page (or, with embed_data, the table)."""
    WARNINGS.clear()
    if workspace:
        print(
            f"Scanning workspace: {project.name} "
            + (f"[{', '.join(sp[0] for sp in project.spaces)}] " if len(project.spaces) > 1 else "")
            + f"({len(project.reports)} reports, {len(project.models)} semantic models"
            + (", as chosen" if chosen else "")
            + ")"
        )
    else:
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
        "workspace": workspace,
        "spaces": [sp[0] for sp in project.spaces] if workspace and len(project.spaces) > 1 else [],
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
                "space": m.get("space") or "",
            }
            for m in models
        ],
        "reports": [
            {
                "key": r["key"],
                "name": r["name"],
                "model": r["model"],
                "external": (r["external"] or {}).get("label"),
                "space": r.get("space") or "",
            }
            for r in reports
        ],
    }
    extra = None
    if workspace:
        meta["scope"] = default_scope(graph, models, reports, chosen or scope_all)
        items, item_edges = build_items(graph, models, reports)
        extra = {"items": items, "itemEdges": item_edges}

    blob = page_data(graph, pages, sections, meta, ai_rules, extra)
    print("\n" + _summary(counts, graph, sections))
    if workspace and not meta["scope"]["all"]:
        print("  The workspace is large, so the page opens on one semantic model. Use Scope to pick others.")

    if embed_data:
        path, n, new, table = embed(project.model_dir, blob)
        label, rel = project.label(project.model_dir)
        print(
            f"\n{'Added' if new else 'Updated'} the TrailsBI table in {rel} "
            f"({n} {'part' if n == 1 else 'parts'}, {len(blob):,} characters): {path.name}"
        )
        print(
            "  Open the project in Power BI Desktop and refresh the TrailsBI table (Home > Refresh).\n"
            "  It holds this report's names, DAX and data source addresses: anyone who can see the\n"
            "  model can read them through the TrailsBI visual."
        )
        if no_page:
            print(f"\nDid not add the TrailsBI page to the report: {no_page}")
        else:
            done = add_page(project.report_dir, table)
            _, rrel = project.label(project.report_dir)
            if done["page"] == "added":
                print(
                    f"Added the TrailsBI page (hidden in view mode) to {rrel}, "
                    f"with the TrailsBI visual {done['visual']}"
                )
            else:
                print(f"The TrailsBI page is already in {rrel}; left as it is")
                if done["visual_written"]:
                    print(f"  Updated the TrailsBI visual in the report to {done['visual']}")
        if not (output or open_page):
            return None

    out = _output_path(output, project.name, started)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(graph, pages, sections, meta, ai_rules, blob), encoding="utf-8")
    print(f"\nWrote {out}")
    if open_page:
        webbrowser.open(out.resolve().as_uri())
    return out


def main(argv=None) -> int:
    """Runs the command line and returns the exit code.

    0: the page was written (or, with --embed, the table). 1: a file could not be read or written.
    2: the path does not lead to exactly one project, or --embed could not write the table.
    """
    args = build_parser().parse_args(argv)
    # A Windows console or pipe may not be able to show every character in a
    # project name; print a replacement character rather than stop.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    try:
        run(
            _expand(args.project),
            args.output,
            args.open,
            args.embed,
            models=args.model,
            reports=args.report,
            include=args.include,
            with_reports=args.with_reports,
            workspaces=args.workspace,
            split=args.split,
            list_only=args.list,
        )
    except (ProjectError, EmbedError, PageError) as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"\nCould not finish: {exc}", file=sys.stderr)
        return 1
    return 0
