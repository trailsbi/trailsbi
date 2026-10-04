# SPDX-License-Identifier: Apache-2.0
"""Renders the self-contained HTML page.

The page is assembled from the files in ``web/``: ``page.html`` is the skeleton,
``styles.css`` is inlined into its ``<style>`` and the files in ``web/js/`` are
concatenated, in name order, into its one ``<script>``. Nothing is loaded from
the network when the page opens.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.resources import files

from .brand import FAVICON, LOGO_SVG, LOGO_VB, MARK_SVG, MARK_VB, TAGLINE, VERSION
from .icons import ICONS

_PLACEHOLDER = re.compile(r"__([A-Z]+)__")

# Small projects open in a blink, so the loading splash would only flash.
_SPLASH_NODES = 400
_SPLASH_BYTES = 800_000


def _read(name: str) -> str:
    return files(__package__).joinpath("web").joinpath(name).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def page_template() -> str:
    """The page skeleton with its stylesheet and script inlined."""
    web = files(__package__).joinpath("web")
    scripts = sorted(
        (p for p in web.joinpath("js").iterdir() if p.name.endswith(".js")), key=lambda p: p.name
    )
    texts = (p.read_text(encoding="utf-8") for p in scripts)
    script = "".join(t if t.endswith("\n") else t + "\n" for t in texts)
    return _read("page.html").replace("__STYLES__", _read("styles.css"), 1).replace("__SCRIPT__", script, 1)


def _json_for_script(value) -> str:
    """JSON that is safe inside a <script> element: no "<" can open or close a tag."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def render_html(G, pages, sections, meta, ai_rules=None) -> str:
    """The finished page for one lineage graph and its findings."""
    edges = [[a, b, ", ".join(sorted(r for r in roles if r))] for (a, b), roles in G.edges.items()]
    data = {
        "nodes": list(G.nodes.values()),
        "edges": edges,
        "pages": pages,
        "health": sections,
        "ai": ai_rules or [],
        "meta": meta,
    }
    blob = _json_for_script(data)
    big = len(G.nodes) > _SPLASH_NODES or len(blob) > _SPLASH_BYTES
    values = {
        "TITLE": meta["name"].replace("&", "&amp;").replace("<", "&lt;"),
        "ICONS": _json_for_script(ICONS),
        "FAVICON": FAVICON,
        "MARKVB": MARK_VB,
        "MARK": MARK_SVG,
        "LOGOVB": LOGO_VB,
        "LOGO": LOGO_SVG,
        "TAGLINE": TAGLINE,
        "VERSION": VERSION,
        "BOOT": "" if big else " hidden",
        "DATA": blob,
    }
    # One pass, so text inside a value (a model name, say) is never mistaken for a placeholder.
    return _PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), page_template())
