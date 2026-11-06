# SPDX-License-Identifier: Apache-2.0
"""Function help: only the functions a project uses travel with its page."""

import json
import shutil
import subprocess

import pytest

from trailsbi.dax_functions import DAX_FUNCTIONS, dax_learn_url
from trailsbi.function_help import function_help, m_functions


def test_reference_data():
    assert m_functions()["Table.SelectRows"][0].startswith("Table.SelectRows(table as table")
    assert "#date" in m_functions()
    syntax, desc = DAX_FUNCTIONS["CALCULATE"]
    assert syntax.startswith("CALCULATE(") and desc
    assert all(name == name.upper() and len(v) == 2 for name, v in DAX_FUNCTIONS.items())
    assert dax_learn_url("PERCENTILE.INC") == "https://learn.microsoft.com/dax/percentile-inc-function-dax"


def test_only_used_functions_are_kept():
    data = {
        "nodes": [
            {
                "detail": {
                    "code": [{"title": "DAX", "text": 'calculate(SUM(Sales[Amount]), "IF(") // DIVIDE('}]
                }
            },
            {"detail": {"steps": [{"code": "Table.SelectRows(Source, each [x] > 1)"}]}},
        ],
        "meta": {"models": [{"outline": [{"x": "Text.Upper(a)", "l": "M"}]}]},
    }
    got = function_help(data)
    # names in strings and comments slip into the candidate list harmlessly; the page skips them
    assert {"CALCULATE", "SUM"} <= set(got["dax"])
    assert set(got["m"]) == {"Table.SelectRows", "Text.Upper"}


def test_page_marks_functions_outside_strings_and_comments(build, fixtures, tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed")
    from trailsbi.render import page_template

    script = page_template().split("/* ---------- function help in DAX and Power Query code ----------")[1]
    script = script.split("var fnTip = null")[0]
    harness = tmp_path / "t.js"
    harness.write_text(
        "var D = {fnhelp: {dax: {CALCULATE: [1, 2], SUM: [1, 2], IF: [1, 2]}, m: {'Text.Upper': [1, 2]}}};\n"
        "function h(tag, a, kids) { return '<' + a['data-fn'] + '>'; }\n"
        "/*" + script + "\n"
        "var show = function (t, l) { return [].concat(codeKids(t, l)).join(''); };\n"
        "console.log(JSON.stringify(show('Calculate(SUM(T[IF(x)]), \"SUM(\") -- SUM(\\n+ \\'IF (\\'[a] + IF (1)', 'dax')));\n"
        "console.log(JSON.stringify(show('Text.Upper(#\"Text.Upper\") & MyText.Upper(x) // Text.Upper(', 'm')));\n",
        encoding="utf-8",
    )
    run = subprocess.run([node, str(harness)], capture_output=True, text=True, check=True)
    out = [json.loads(line) for line in run.stdout.splitlines()]
    assert out[0] == "<CALCULATE>(<SUM>(T[IF(x)]), \"SUM(\") -- SUM(\n+ 'IF ('[a] + <IF> (1)"
    assert out[1] == '<Text.Upper>(#"Text.Upper") & MyText.Upper(x) // Text.Upper('
