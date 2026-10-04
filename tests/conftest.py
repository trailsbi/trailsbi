# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures: paths to the synthetic projects and a helper that builds one."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


def page_data(html: str) -> dict:
    """The JSON a generated page carries in its <script id="data"> element."""
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    assert m, "the page has no data block"
    return json.loads(m.group(1))


@pytest.fixture
def build(tmp_path, capsys):
    """Builds a project and returns (path to the page, its data)."""
    from trailsbi.cli import run

    def _build(project, **kw):
        out = run(project, output=tmp_path / "out.html", **kw)
        capsys.readouterr()
        return out, page_data(out.read_text(encoding="utf-8"))

    return _build
