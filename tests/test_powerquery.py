# SPDX-License-Identifier: Apache-2.0
from trailsbi.powerquery import analyze_m

CODE = """let
    Source = Sql.Database(ServerName, "Shop"),
    dbo_Sales = Source{[Schema="dbo",Item="Sales"]}[Data],
    Joined = Table.NestedJoin(dbo_Sales, {"Key"}, Products, {"Key"}, "P")
in
    Joined"""


def analyze():
    params = {"ServerName": {"value": '"sql.contoso.com"'}}
    return analyze_m(CODE, "Sales", {"Sales", "Products", "ServerName"}, params)


def test_steps():
    names = [s["name"] for s in analyze()["steps"]]
    assert names == ["Source", "dbo_Sales", "Joined"]


def test_source_parameter_and_reference():
    a = analyze()
    assert [s["fn"] for s in a["sources"]] == ["Sql.Database"]
    assert "ServerName" in a["params"]
    assert a["refs"] == {"Products"}
