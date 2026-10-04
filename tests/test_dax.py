# SPDX-License-Identifier: Apache-2.0
from trailsbi.dax import dax_clean, dax_refs


def test_qualified_and_bare_references():
    qual, bare, _tables = dax_refs(
        "CALCULATE([Total Sales], SAMEPERIODLASTYEAR('Date'[Date])) + SUM(Sales[Amount])"
    )
    assert ("Date", "Date") in qual
    assert ("Sales", "Amount") in qual
    assert "Total Sales" in bare


def test_comments_and_strings_are_ignored():
    expr = '// [Not A Ref]\n"[Also Not]" & [Real]  /* [Nope] */'
    _qual, bare, _tables = dax_refs(expr)
    assert bare == ["Real"]
    assert "Nope" not in dax_clean(expr)
