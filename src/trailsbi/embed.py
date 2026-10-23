# SPDX-License-Identifier: Apache-2.0
"""Writes the TrailsBI page data into the project's semantic model (``trailsbi --embed``).

The TrailsBI visual shows the report inside Power BI. It reads the page data from a
small table in the model, ``TrailsBI``: Part (1, 2, 3 ...) and Chunk (up to 30,000
characters of the data each, under Power BI's text limits). The table is import mode,
hidden, and filled from an M ``#table`` literal, so it needs no data source.

The table carries the annotation ``TrailsBI_Embedded``. That is how a later run finds it
again (even if it was renamed) and how every run leaves it out of the analysis.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .brand import VERSION
from .tmdl import parse_tmdl_text

TABLE = "TrailsBI"
MARKER = "TrailsBI_Embedded"
CHUNK = 30_000
# The TrailsBI visual's type in reports is its GUID: trailsbiE7A4C19D (before 0.9.1: trailsbiVisual064B...)
VISUAL_TYPE_PREFIX = "trailsbi"

_MARKER_TMDL = re.compile(r"^\s*annotation\s+" + MARKER + r"\s*=", re.M)
_TABLE_LINE = re.compile(r"^table\s+(.+?)\s*$", re.M)
_REF_TABLE = re.compile(r"^ref\s+table\s+(.+?)\s*$", re.M)


class EmbedError(Exception):
    """The table could not be written into this project's model."""


# --- recognising the table and visual, so the analysis leaves them out --------------


def is_embedded_tmdl(text: str) -> bool:
    """Whether a TMDL file is the table TrailsBI wrote."""
    return bool(_MARKER_TMDL.search(text))


def is_embedded_bim_table(table: dict) -> bool:
    """Whether a model.bim table is the one TrailsBI wrote."""
    return any(a.get("name") == MARKER for a in table.get("annotations") or [] if isinstance(a, dict))


def is_trailsbi_visual(visual_type) -> bool:
    return str(visual_type or "").lower().startswith(VISUAL_TYPE_PREFIX)


def drop_trailsbi_visuals(report: dict) -> None:
    """Takes TrailsBI visuals out of a loaded report, and pages that held nothing else."""
    pages = []
    for page in report.get("pages", []):
        kept = [v for v in page["visuals"] if not is_trailsbi_visual(v.get("type"))]
        if page["visuals"] and not kept:
            continue
        page["visuals"] = kept
        pages.append(page)
    report["pages"] = pages


# --- the table ---------------------------------------------------------------------


def chunks(data_json: str) -> list:
    """The data in parts of at most CHUNK characters.

    Power BI trims trailing spaces from text when it loads it into the model, so a part
    must never end with whitespace (a space inside a name would vanish at the cut). Each
    cut moves back until the characters on both sides of it are not whitespace.
    """
    parts, i, n = [], 0, len(data_json)
    while i < n:
        j = min(i + CHUNK, n)
        while i + 1 < j < n and (data_json[j - 1].isspace() or data_json[j].isspace()):
            j -= 1
        parts.append(data_json[i:j])
        i = j
    return parts or [""]


def m_text(value: str) -> str:
    """A Power Query (M) text literal. In M, "#(" starts an escape such as #(lf), so a
    literal "#(" is written as "#(#)(" and reads back unchanged."""
    return '"' + value.replace('"', '""').replace("#(", "#(#)(") + '"'


def m_source(parts: list) -> list:
    """The partition's M query, one line per list item."""
    rows = [f"\t\t{{{i}, {m_text(c)}}}" + ("," if i < len(parts) else "") for i, c in enumerate(parts, 1)]
    return [
        "let",
        "\tSource = #table(",
        "\t\ttype table [Part = Int64.Type, Chunk = text],",
        "\t\t{",
        *["\t" + r for r in rows],
        "\t\t}",
        "\t)",
        "in",
        "\tSource",
    ]


def _tmdl_name(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def table_tmdl(name: str, parts: list) -> str:
    query = "\n".join("\t\t\t\t" + ln for ln in m_source(parts))
    return (
        "/// TrailsBI report data for the TrailsBI visual.\n"
        "/// Written by `trailsbi --embed`; run it again to update.\n"
        f"table {_tmdl_name(name)}\n"
        "\tisHidden\n"
        "\n"
        "\tcolumn Part\n"
        "\t\tdataType: int64\n"
        "\t\tformatString: 0\n"
        "\t\tisHidden\n"
        "\t\tsummarizeBy: none\n"
        "\t\tsourceColumn: Part\n"
        "\n"
        "\tcolumn Chunk\n"
        "\t\tdataType: string\n"
        "\t\tisHidden\n"
        "\t\tsummarizeBy: none\n"
        "\t\tsourceColumn: Chunk\n"
        "\n"
        f"\tpartition {_tmdl_name(name)} = m\n"
        "\t\tmode: import\n"
        "\t\tsource =\n"
        f"{query}\n"
        "\n"
        f"\tannotation {MARKER} = {VERSION}\n"
    )


def table_bim(name: str, parts: list) -> dict:
    return {
        "name": name,
        "description": "TrailsBI report data for the TrailsBI visual. Written by `trailsbi --embed`; "
        "run it again to update.",
        "isHidden": True,
        "columns": [
            {
                "name": "Part",
                "dataType": "int64",
                "formatString": "0",
                "isHidden": True,
                "summarizeBy": "none",
                "sourceColumn": "Part",
            },
            {
                "name": "Chunk",
                "dataType": "string",
                "isHidden": True,
                "summarizeBy": "none",
                "sourceColumn": "Chunk",
            },
        ],
        "partitions": [
            {"name": name, "mode": "import", "source": {"type": "m", "expression": m_source(parts)}}
        ],
        "annotations": [{"name": MARKER, "value": VERSION}],
    }


# --- writing it into the project ----------------------------------------------------


def _read(path: Path) -> tuple:
    """(text with \\n line ends, the file's own line end, whether it had a BOM)."""
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), newline, bom


def _write(path: Path, text: str, newline: str = "\n", bom: bool = False) -> None:
    data = text.replace("\n", newline).encode("utf-8")
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)


def _unquote(name: str) -> str:
    name = name.strip()
    if len(name) >= 2 and name[0] == name[-1] == "'":
        return name[1:-1].replace("''", "'")
    return name


_TAKEN = (
    f"The model already has a table called {TABLE} that TrailsBI did not write. Rename it, then run again."
)
_SHAPE = {"part", "chunk"}  # the columns of the table; one called TrailsBI with just these is ours


def _tmdl_columns(text: str) -> set:
    try:
        table = next(o for o in parse_tmdl_text(text) if o["kw"] == "table")
    except (StopIteration, ValueError):
        return set()
    return {c["name"].lower() for c in table["children"] if c["kw"] == "column"}


def _embed_tmdl(def_dir: Path, parts: list) -> tuple:
    tables_dir = def_dir / "tables"
    existing, same_name = None, None
    for f in sorted(tables_dir.glob("*.tmdl")) if tables_dir.is_dir() else []:
        text = _read(f)[0]
        m = _TABLE_LINE.search(text)
        if is_embedded_tmdl(text):
            existing = (f, _unquote(m.group(1)) if m else TABLE)
        elif m and _unquote(m.group(1)).lower() == TABLE.lower():
            same_name = (f, _unquote(m.group(1)), _tmdl_columns(text) == _SHAPE)
    if not existing and same_name:
        if not same_name[2]:
            raise EmbedError(_TAKEN)
        existing = same_name[:2]  # an earlier TrailsBI table without the marker (the preview's to_table)
    if existing:
        path, name = existing
        _, newline, bom = _read(path)
    else:
        path, name, newline, bom = tables_dir / f"{TABLE}.tmdl", TABLE, "\n", False
    tables_dir.mkdir(parents=True, exist_ok=True)
    _write(path, table_tmdl(name, parts), newline, bom)

    # model.tmdl lists the tables in order with `ref table`; add ours at the end.
    model_file = def_dir / "model.tmdl"
    if model_file.exists():
        text, newline, bom = _read(model_file)
        refs = [_unquote(r) for r in _REF_TABLE.findall(text)]
        if refs and name not in refs:
            lines = text.split("\n")
            last = max(i for i, ln in enumerate(lines) if _REF_TABLE.match(ln))
            lines.insert(last + 1, f"ref table {_tmdl_name(name)}")
            _write(model_file, "\n".join(lines), newline, bom)
    return path, existing is None, name


def _embed_bim(bim: Path, parts: list) -> tuple:
    text, newline, bom = _read(bim)
    data = json.loads(text)
    if json.dumps(data, indent=2, ensure_ascii=False) != text.rstrip("\n"):
        raise EmbedError(
            f"{bim.name} is not laid out the way Power BI Desktop writes it, so TrailsBI will not "
            "rewrite it. Open and save the project in Power BI Desktop, then run again."
        )
    tables = data.setdefault("model", {}).setdefault("tables", [])
    at = next((i for i, t in enumerate(tables) if is_embedded_bim_table(t)), None)
    if at is None:
        at = next((i for i, t in enumerate(tables) if str(t.get("name", "")).lower() == TABLE.lower()), None)
        if (
            at is not None
            and {str(c.get("name", "")).lower() for c in tables[at].get("columns") or []} != _SHAPE
        ):
            raise EmbedError(_TAKEN)
    new = at is None
    if new:
        name = TABLE
        tables.append(table_bim(name, parts))
    else:
        name = tables[at].get("name") or TABLE
        tables[at] = table_bim(name, parts)
    tail = text[len(text.rstrip("\n")) :]
    _write(bim, json.dumps(data, indent=2, ensure_ascii=False) + tail, newline, bom)
    return bim, new, name


def adopt(model_dir: Path | None) -> bool:
    """Marks an earlier TrailsBI table that has no marker yet (the visual preview's
    to_table.py wrote one), so this run's analysis leaves it out. True if one was marked."""
    if model_dir is None:
        return False
    tables_dir = model_dir / "definition" / "tables"
    for f in sorted(tables_dir.glob("*.tmdl")) if tables_dir.is_dir() else []:
        text, newline, bom = _read(f)
        m = _TABLE_LINE.search(text)
        if (
            m
            and _unquote(m.group(1)).lower() == TABLE.lower()
            and not is_embedded_tmdl(text)
            and _tmdl_columns(text) == _SHAPE
        ):
            _write(f, text.rstrip("\n") + f"\n\n\tannotation {MARKER} = {VERSION}\n", newline, bom)
            return True
    bim = model_dir / "model.bim"
    if not (model_dir / "definition").is_dir() and bim.exists():
        text, newline, bom = _read(bim)
        data = json.loads(text)
        if json.dumps(data, indent=2, ensure_ascii=False) != text.rstrip("\n"):
            return False  # embed() explains
        for t in (data.get("model") or {}).get("tables") or []:
            cols = {str(c.get("name", "")).lower() for c in t.get("columns") or []}
            if (
                str(t.get("name", "")).lower() == TABLE.lower()
                and not is_embedded_bim_table(t)
                and cols == _SHAPE
            ):
                t.setdefault("annotations", []).append({"name": MARKER, "value": VERSION})
                tail = text[len(text.rstrip("\n")) :]
                _write(bim, json.dumps(data, indent=2, ensure_ascii=False) + tail, newline, bom)
                return True
    return False


def embed(model_dir: Path | None, data_json: str) -> tuple:
    """Writes or replaces the TrailsBI table in the model at `model_dir`.

    Returns (file written, number of chunks, whether the table is new, the table's name).
    """
    if model_dir is None:
        raise EmbedError(
            "This report uses a published semantic model, so there is no model in the project "
            "to write the TrailsBI table into. Run --embed on the project that holds the model."
        )
    parts = chunks(data_json)
    def_dir = model_dir / "definition"
    bim = model_dir / "model.bim"
    if def_dir.is_dir() and next(def_dir.rglob("*.tmdl"), None) is not None:
        path, new, name = _embed_tmdl(def_dir, parts)
    elif bim.exists():
        path, new, name = _embed_bim(bim, parts)
    else:
        raise EmbedError(
            f"No TMDL folder or model.bim in {model_dir.name}, so there is nowhere to write the table."
        )
    return path, len(parts), new, name
