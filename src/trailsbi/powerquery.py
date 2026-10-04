# SPDX-License-Identifier: Apache-2.0
"""Power Query (M) analysis: steps, data sources and query-to-query references."""

from __future__ import annotations

import re

from .icons import source_icon

_M_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<lc>//[^\n]*)
  | (?P<bc>/\*.*?\*/)
  | (?P<str>"(?:[^"]|"")*")
  | (?P<qid>\#"(?:[^"]|"")*")
  | (?P<id>\#?[^\W\d]\w*(?:\.\w+)*)
  | (?P<num>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
  | (?P<sym>=>|<>|<=|>=|\.\.\.|\.\.|\?\?|.)
""",
    re.S | re.X,
)


def m_tokens(code):
    out = []
    for mt in _M_TOKEN.finditer(code or ""):
        kind = mt.lastgroup
        if kind in ("ws", "lc", "bc"):
            continue
        text = mt.group()
        if kind == "str":
            val = text[1:-1].replace('""', '"')
        elif kind == "qid":
            val = text[2:-1].replace('""', '"')
        else:
            val = text
        out.append((kind, val, mt.start(), mt.end()))
    return out


def m_steps(code, toks):
    """Splits the top-level let ... in block into named steps."""
    if not toks or toks[0][:2] != ("id", "let"):
        return []
    steps, cur, depth = [], [], 0

    def flush(seq):
        if len(seq) >= 2 and seq[0][0] in ("id", "qid") and seq[1][:2] == ("sym", "="):
            body = seq[2:]
            text = code[body[0][2] : body[-1][3]] if body else ""
            steps.append({"name": seq[0][1], "code": text, "tokens": body})

    for tok in toks[1:]:
        kind, val = tok[0], tok[1]
        if kind == "sym" and val in ("(", "[", "{"):
            depth += 1
        elif kind == "sym" and val in (")", "]", "}"):
            depth -= 1
        elif kind == "id" and val == "let":
            depth += 1
        elif kind == "id" and val == "in":
            if depth == 0:
                flush(cur)
                return steps
            depth -= 1
        if depth == 0 and kind == "sym" and val == ",":
            flush(cur)
            cur = []
        else:
            cur.append(tok)
    flush(cur)
    return steps


STEP_LABELS = {
    "table.selectrows": "Filter rows",
    "table.removecolumns": "Remove columns",
    "table.selectcolumns": "Choose columns",
    "table.transformcolumntypes": "Change type",
    "table.renamecolumns": "Rename columns",
    "table.addcolumn": "Add column",
    "table.nestedjoin": "Merge queries",
    "table.join": "Merge queries",
    "table.expandtablecolumn": "Expand columns",
    "table.expandrecordcolumn": "Expand record",
    "table.combine": "Append queries",
    "table.group": "Group by",
    "table.pivot": "Pivot",
    "table.unpivot": "Unpivot",
    "table.unpivotothercolumns": "Unpivot other columns",
    "table.sort": "Sort",
    "table.distinct": "Remove duplicates",
    "table.promoteheaders": "Promote headers",
    "table.demoteheaders": "Demote headers",
    "table.replacevalue": "Replace values",
    "table.filldown": "Fill down",
    "table.fillup": "Fill up",
    "table.skip": "Remove top rows",
    "table.firstn": "Keep top rows",
    "table.lastn": "Keep bottom rows",
    "table.removefirstn": "Remove top rows",
    "table.removelastn": "Remove bottom rows",
    "table.splitcolumn": "Split column",
    "table.transformcolumns": "Transform columns",
    "table.buffer": "Buffer table",
    "table.duplicatecolumn": "Duplicate column",
    "table.reordercolumns": "Reorder columns",
    "table.addindexcolumn": "Add index column",
    "table.replaceerrorvalues": "Replace errors",
    "table.removerowswitherrors": "Remove errors",
    "table.combinecolumns": "Merge columns",
    "table.selectrowswitherrors": "Keep errors",
    "table.transformrows": "Transform rows",
    "table.fromrows": "Build table",
    "table.fromrecords": "Build table",
    "table.fromlist": "Build table",
    "table.removematchingrows": "Remove matching rows",
    "table.addkey": "Add key",
    "table.addjoincolumn": "Merge queries",
    "table.aggregatetablecolumn": "Aggregate",
    "value.nativequery": "Native query",
    "excel.workbook": "Open Excel workbook",
    "csv.document": "Parse CSV",
    "json.document": "Parse JSON",
    "xml.tables": "Parse XML",
    "parquet.document": "Parse Parquet",
    "pdf.tables": "Parse PDF",
    "table.combinecolumnstorecord": "Combine to record",
    "list.generate": "Generate list",
}

SOURCE_FUNCS = {
    "sql.database": "SQL Server",
    "sql.databases": "SQL Server",
    "oracle.database": "Oracle",
    "postgresql.database": "PostgreSQL",
    "mysql.database": "MySQL",
    "snowflake.databases": "Snowflake",
    "googlebigquery.database": "Google BigQuery",
    "databricks.catalogs": "Databricks",
    "databricks.contents": "Databricks",
    "databricksmultiplecloud.catalogs": "Databricks",
    "file.contents": "File",
    "folder.files": "Folder",
    "folder.contents": "Folder",
    "web.contents": "Web",
    "web.page": "Web page",
    "sharepoint.files": "SharePoint",
    "sharepoint.contents": "SharePoint",
    "sharepoint.tables": "SharePoint list",
    "odata.feed": "OData",
    "odbc.datasource": "ODBC",
    "odbc.query": "ODBC",
    "oledb.datasource": "OLE DB",
    "oledb.query": "OLE DB",
    "analysisservices.database": "Analysis Services",
    "analysisservices.databases": "Analysis Services",
    "powerbi.datasets": "Power BI semantic model",
    "powerplatform.datasets": "Power BI semantic model",
    "azurestorage.blobs": "Azure Blob Storage",
    "azurestorage.datalake": "ADLS Gen2",
    "azurestorage.tables": "Azure Table Storage",
    "azuredatalakestorage.contents": "Azure Data Lake",
    "lakehouse.contents": "Fabric Lakehouse",
    "fabric.warehouse": "Fabric Warehouse",
    "powerplatform.dataflows": "Dataflow",
    "powerbi.dataflows": "Dataflow",
    "commondataservice.database": "Dataverse",
    "dataverse.contents": "Dataverse",
    "salesforce.data": "Salesforce",
    "salesforce.reports": "Salesforce",
    "python.execute": "Python script",
    "r.execute": "R script",
    "amazonredshift.database": "Amazon Redshift",
    "saphana.database": "SAP HANA",
    "sapbusinesswarehouse.cubes": "SAP BW",
    "teradata.database": "Teradata",
    "azuredataexplorer.contents": "Azure Data Explorer",
    "kusto.contents": "Azure Data Explorer",
    "exchange.contents": "Exchange",
    "activedirectory.domains": "Active Directory",
    "db2.database": "IBM Db2",
    "sybase.database": "Sybase",
    "informix.database": "Informix",
    "impala.database": "Impala",
    "vertica.database": "Vertica",
    "spark.tables": "Spark",
    "hdfs.files": "HDFS",
    "hdfs.contents": "HDFS",
    "cosmosdb.contents": "Cosmos DB",
    "documentdb.contents": "Cosmos DB",
    "googleanalytics.accounts": "Google Analytics",
    "dynamics365businesscentral.apis": "Business Central",
    "cdm.contents": "Common Data Model",
    "anaplan.contents": "Anaplan",
    "essbase.cubes": "Essbase",
    "dremio.databases": "Dremio",
}

_KEYWORDS_M = {
    "let",
    "in",
    "each",
    "if",
    "then",
    "else",
    "try",
    "otherwise",
    "and",
    "or",
    "not",
    "as",
    "is",
    "meta",
    "type",
    "true",
    "false",
    "null",
    "error",
    "section",
    "shared",
}


def _call_args(toks, j):
    """Token lists of each top-level argument of the call whose name is toks[j]."""
    args, cur, depth = [], [], 0
    k = j + 2
    while k < len(toks):
        kind, val = toks[k][0], toks[k][1]
        if kind == "sym" and val in ("(", "[", "{"):
            depth += 1
        elif kind == "sym" and val in (")", "]", "}"):
            if depth == 0:
                break
            depth -= 1
        elif kind == "id" and val == "let":
            depth += 1
        elif kind == "id" and val == "in" and depth > 0:
            depth -= 1
        if depth == 0 and kind == "sym" and val == ",":
            args.append(cur)
            cur = []
        else:
            cur.append(toks[k])
        k += 1
    if cur:
        args.append(cur)
    return args


def _arg_value(arg, params, used_params):
    parts = []
    for kind, val, _, _ in arg:
        if kind == "str":
            parts.append(val)
        elif kind in ("id", "qid") and val in params:
            used_params.add(val)
            pv = params[val]["value"]
            parts.append(pv if pv is not None else "{" + val + "}")
        elif kind == "sym" and val == "&":
            continue
        else:
            return None
    return "".join(parts) if parts else None


def analyze_m(code: str, self_name: str, query_names: set, params: dict) -> dict:
    toks = m_tokens(code)
    steps = m_steps(code, toks)
    step_names = {s["name"] for s in steps}
    refs, used_params, sources = set(), set(), []
    native = False

    for j, (kind, val, _, _) in enumerate(toks):
        if kind in ("id", "qid"):
            prev = toks[j - 1][1] if j else ""
            nxt = toks[j + 1][1] if j + 1 < len(toks) else ""
            not_a_reference = (
                val in step_names
                or val == self_name
                or (prev == "[" and nxt == "]")  # a record field: [Name]
                or (nxt == "=" and prev in ("[", ","))  # a field being defined: [Name = ...]
                or (kind == "id" and val in _KEYWORDS_M)
            )
            if not_a_reference:
                pass
            elif val in params:
                used_params.add(val)
            elif val in query_names:
                refs.add(val)
        if kind == "id" and j + 1 < len(toks) and toks[j + 1][1] == "(":
            low = val.lower()
            if low == "value.nativequery":
                native = True
            if low in SOURCE_FUNCS:
                vals = []
                for arg in _call_args(toks, j):
                    v = _arg_value(arg, params, used_params)
                    if v:
                        vals.append(v)
                    if len(vals) == 2:
                        break
                sources.append(_make_source(val, SOURCE_FUNCS[low], vals))

    if not sources and re.search(r"Binary\.FromText\s*\(|#table\s*\(", code or ""):
        sources.append(
            {
                "key": "manual",
                "label": "Entered data (inside the file)",
                "name": "Entered data",
                "connector": "Manual table",
                "fn": "",
                "args": [],
                "icon": "manual",
            }
        )

    nav = []
    for mm in re.finditer(r"\{\s*\[([^\[\]]*)\]\s*\}", code or ""):
        fields = dict(re.findall(r'(\w+)\s*=\s*"((?:[^"]|"")*)"', mm.group(1)))
        if "Item" in fields:
            nav.append(".".join(x for x in (fields.get("Schema"), fields["Item"]) if x))
        elif "Name" in fields:
            nav.append(fields["Name"])
        elif "Id" in fields:
            nav.append(fields["Id"])
    nq = re.search(r'\[\s*Query\s*=\s*"((?:[^"]|"")*)"', code or "")
    native_sql = nq.group(1).replace('""', '"') if nq else None
    if not native_sql and native:
        mm = re.search(r'Value\.NativeQuery\s*\([^,]+,\s*"((?:[^"]|"")*)"', code or "", re.S)
        native_sql = mm.group(1).replace('""', '"') if mm else None

    nav_names = [n.split(".")[-1] for n in nav]
    for src in sources:  # AnalysisServices.Databases(url){[Name="Model"]}
        ds = src.get("dataset")
        if ds and ds["model"] == "Unknown semantic model" and nav_names:
            ds["model"] = nav_names[0]
            src["name"] = nav_names[0]
            src["label"] = "Semantic model: " + nav_names[0]
            src["key"] = "dataset|" + nav_names[0].lower()
    step_list = []
    for s in steps:
        step_list.append({"name": s["name"], "label": _step_label(s, query_names), "code": s["code"]})
    return {
        "steps": step_list,
        "sources": sources,
        "refs": refs,
        "params": used_params,
        "nav": list(dict.fromkeys(nav)),
        "native_sql": native_sql,
    }


_PBI_SCHEME = re.compile(r"(?i)^(powerbi|pbiazure|pbidedicated|asazure|powerbi-df)://")


def _dataset_source(fn, vals):
    """A live connection to another Power BI semantic model, if this is one."""
    low = fn.lower()
    if not (low.startswith(("analysisservices.database", "powerbi.datasets", "powerplatform.datasets"))):
        return None
    url = next((v for v in vals if _PBI_SCHEME.match(v or "")), None)
    if low.startswith("analysisservices.database") and not url:
        return None  # a real Analysis Services server, not Power BI
    ws = re.sub(r"(?i)^[a-z-]+://[^/]+(/v1\.0/myorg)?/?", "", url or "").strip("/")
    name = next((v for v in vals if v and not _PBI_SCHEME.match(v)), "")
    return {"key": "dataset|" + (name or ws).lower(), "name": name, "workspace": ws, "fn": fn, "args": vals}


def _make_source(fn, connector, vals):
    ds = _dataset_source(fn, vals)
    if ds:
        name = ds["name"] or "Unknown semantic model"
        return {
            "key": "dataset|" + name.lower(),
            "label": "Semantic model: " + name,
            "name": name,
            "connector": "Power BI semantic model",
            "fn": fn,
            "args": vals,
            "icon": "ws_model",
            "dataset": {"model": name, "workspace": ds["workspace"]},
        }
    display = []
    for i, v in enumerate(vals):
        if connector in ("File", "Folder") and i == 0:
            display.append(re.split(r"[\\/]", v.rstrip("\\/"))[-1] or v)
        elif i == 0 and re.match(r"(?i)^https?://", v):
            display.append(re.sub(r"(?i)^https?://", "", v).rstrip("/"))
        else:
            display.append(v)
    name = " / ".join(display) or connector
    label = connector + (": " + name if display else "")
    key = (fn.lower() + "|" + "|".join(vals)).lower()
    return {
        "key": key,
        "label": label,
        "name": name,
        "connector": connector,
        "fn": fn,
        "args": vals,
        "icon": source_icon(fn),
    }


def _step_label(step, query_names):
    toks = step["tokens"]
    if not toks:
        return "Step"
    fn = None
    for j, (kind, val, _, _) in enumerate(toks):
        if kind == "id" and j + 1 < len(toks) and toks[j + 1][1] == "(" and val not in _KEYWORDS_M:
            fn = val
            break
    if fn is None:
        if len(toks) > 1 and toks[1][1] == "{":
            return "Navigate"
        if len(toks) == 1 and toks[0][0] in ("id", "qid"):
            return "Reference " + toks[0][1]
        return "Custom step"
    low = fn.lower()
    if low in SOURCE_FUNCS:
        return "Source: " + SOURCE_FUNCS[low]
    label = STEP_LABELS.get(low, fn)
    if low == "table.addcolumn":
        names = [v for k, v, _, _ in toks if k == "str"]
        if names:
            label += f' "{names[0]}"'
    if low in ("table.nestedjoin", "table.join", "table.combine", "table.addjoincolumn"):
        others = [v for k, v, _, _ in toks if k in ("id", "qid") and v in query_names]
        if others:
            label += " with " + ", ".join(dict.fromkeys(others))
    return label
