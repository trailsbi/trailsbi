# SPDX-License-Identifier: Apache-2.0
from trailsbi.tmdl import parse_tmdl_text, split_col_ref

TABLE = """/// Orders, one row per line.
table 'Order Lines'
\tlineageTag: 1234

\t/// Sum of the amounts.
\tmeasure 'Total Amount' = SUM('Order Lines'[Amount])
\t\tformatString: #,0

\tmeasure Multi =
\t\t\tVAR x = 1
\t\t\tRETURN x

\tcolumn Amount
\t\tdataType: decimal
\t\tisHidden
\t\tsourceColumn: Amount

\tpartition 'Order Lines' = m
\t\tmode: import
\t\tsource =
\t\t\t\tlet
\t\t\t\t    Source = Csv.Document(File.Contents("orders.csv"))
\t\t\t\tin
\t\t\t\t    Source
"""


def test_table_and_children():
    [table] = parse_tmdl_text(TABLE)
    assert table["kw"] == "table"
    assert table["name"] == "Order Lines"
    assert table["desc"] == "Orders, one row per line."
    kinds = [(c["kw"], c["name"]) for c in table["children"]]
    assert kinds == [
        ("measure", "Total Amount"),
        ("measure", "Multi"),
        ("column", "Amount"),
        ("partition", "Order Lines"),
    ]


def test_measure_expression_and_properties():
    [table] = parse_tmdl_text(TABLE)
    total, multi = table["children"][:2]
    assert total["expr"] == "SUM('Order Lines'[Amount])"
    assert total["props"]["formatString"] == "#,0"
    assert total["desc"] == "Sum of the amounts."
    assert "VAR x = 1" in multi["expr"] and "RETURN x" in multi["expr"]


def test_flag_properties_and_partition_source():
    [table] = parse_tmdl_text(TABLE)
    column, partition = table["children"][2:]
    assert column["props"]["dataType"] == "decimal"
    assert "isHidden" in column["props"]
    assert "Csv.Document" in partition["props"]["source"]


def test_split_col_ref():
    assert split_col_ref("'Dim Customer'.'Customer Key'") == ("Dim Customer", "Customer Key")
    assert split_col_ref("Sales.ProductKey") == ("Sales", "ProductKey")
