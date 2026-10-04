# SPDX-License-Identifier: Apache-2.0
"""Best Practice Analyzer rules, evaluated directly from the model files.

The rules follow Microsoft's Best Practice Analyzer rule set
(microsoft/Analysis-Services, BestPracticeRules/BPARules.json). Rules that need
VertiPaq Analyzer statistics run only when those annotations are present in
the model.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .tmdl import parse_tmdl_text, split_col_ref
from .utils import as_text, is_auto_table, read_json, read_text, unquote

BPA_CATEGORIES = [
    "Performance",
    "DAX Expressions",
    "Error Prevention",
    "Maintenance",
    "Naming Conventions",
    "Formatting",
]

# (id, category, severity 1=info 2=warning 3=error, name, description)
BPA_RULES = [
    (
        "AVOID_FLOATING_POINT_DATA_TYPES",
        "Performance",
        2,
        "Do not use floating point data types",
        "Double can cause unpredictable round-off errors and slower performance. Use Int64 or Decimal where appropriate.",
    ),
    (
        "ISAVAILABLEINMDX_FALSE_NONATTRIBUTE_COLUMNS",
        "Performance",
        2,
        "Set IsAvailableInMdx to false on non-attribute columns",
        "Hidden columns not used for sorting or in hierarchies don't need attribute hierarchies; turning them off saves memory and processing time.",
    ),
    (
        "AVOID_BI-DIRECTIONAL_RELATIONSHIPS_AGAINST_HIGH-CARDINALITY_COLUMNS",
        "Performance",
        2,
        "Avoid bi-directional relationships against high-cardinality columns",
        "Bi-directional relationships on columns with more than 100,000 distinct values are slow. Needs VertiPaq Analyzer statistics.",
    ),
    (
        "REDUCE_USAGE_OF_LONG-LENGTH_COLUMNS_WITH_HIGH_CARDINALITY",
        "Performance",
        2,
        "Reduce usage of long-length columns with high cardinality",
        "Long text columns with many unique values bloat the model and slow queries. Needs VertiPaq Analyzer statistics.",
    ),
    (
        "SPLIT_DATE_AND_TIME",
        "Performance",
        2,
        "Split date and time",
        "Date-time columns with times other than midnight have high cardinality; split the time into its own column. Needs VertiPaq Analyzer statistics.",
    ),
    (
        "LARGE_TABLES_SHOULD_BE_PARTITIONED",
        "Performance",
        2,
        "Large tables should be partitioned",
        "Tables over 25 million rows with a single partition should be partitioned. Needs VertiPaq Analyzer statistics.",
    ),
    (
        "REDUCE_USAGE_OF_CALCULATED_COLUMNS_THAT_USE_THE_RELATED_FUNCTION",
        "Performance",
        2,
        "Reduce usage of calculated columns that use the RELATED function",
        "Calculated columns compress worse than data columns; ones using RELATED are often easy to move upstream.",
    ),
    (
        "SNOWFLAKE_SCHEMA_ARCHITECTURE",
        "Performance",
        2,
        "Consider a star-schema instead of a snowflake architecture",
        "These tables sit on both sides of relationships, which suggests a snowflake. A star schema is usually optimal.",
    ),
    (
        "MODEL_SHOULD_HAVE_A_DATE_TABLE",
        "Performance",
        2,
        "Model should have a date table",
        "No table is marked as a date table with a date key column.",
    ),
    (
        "DATE/CALENDAR_TABLES_SHOULD_BE_MARKED_AS_A_DATE_TABLE",
        "Performance",
        2,
        "Date/calendar tables should be marked as a date table",
        "Tables named like dates or calendars should be marked as a date table with a date key column.",
    ),
    (
        "REMOVE_AUTO-DATE_TABLE",
        "Performance",
        2,
        "Remove auto-date table",
        "Auto date/time tables use memory; turn the option off in Power BI Desktop.",
    ),
    (
        "AVOID_EXCESSIVE_BI-DIRECTIONAL_OR_MANY-TO-MANY_RELATIONSHIPS",
        "Performance",
        2,
        "Avoid excessive bi-directional or many-to-many relationships",
        "More than 30% of the relationships are bi-directional or many-to-many.",
    ),
    (
        "LIMIT_ROW_LEVEL_SECURITY_(RLS)_LOGIC",
        "Performance",
        2,
        "Limit row level security (RLS) logic",
        "RLS filters using RIGHT, LEFT, UPPER, LOWER or FIND can often be simplified or moved upstream.",
    ),
    (
        "MODEL_USING_DIRECT_QUERY_AND_NO_AGGREGATIONS",
        "Performance",
        1,
        "Consider using aggregations if using Direct Query in Power BI",
        "The model uses DirectQuery tables but defines no aggregations.",
    ),
    (
        "MINIMIZE_POWER_QUERY_TRANSFORMATIONS",
        "Performance",
        2,
        "Minimize Power Query transformations",
        "Joins, grouping, pivoting, sorting and native queries in Power Query slow refresh; push them to the source where possible.",
    ),
    (
        "AVOID_USING_MANY-TO-MANY_RELATIONSHIPS_ON_TABLES_USED_FOR_DYNAMIC_ROW_LEVEL_SECURITY",
        "Performance",
        3,
        "Avoid using many-to-many relationships on tables used for dynamic row level security",
        "Many-to-many relationships on tables with RLS can seriously degrade query performance.",
    ),
    (
        "UNPIVOT_PIVOTED_(MONTH)_DATA",
        "Performance",
        2,
        "Unpivot pivoted (month) data",
        "Numeric columns for January to June suggest pivoted data; unpivot it.",
    ),
    (
        "MANY-TO-MANY_RELATIONSHIPS_SHOULD_BE_SINGLE-DIRECTION",
        "Performance",
        2,
        "Many-to-many relationships should be single-direction",
        "Bi-directional many-to-many relationships are expensive.",
    ),
    (
        "REDUCE_USAGE_OF_CALCULATED_TABLES",
        "Performance",
        2,
        "Reduce usage of calculated tables",
        "Calculated table logic is better placed in the data warehouse.",
    ),
    (
        "REMOVE_REDUNDANT_COLUMNS_IN_RELATED_TABLES",
        "Performance",
        2,
        "Remove redundant columns in related tables",
        "A related table already has a column with the same name.",
    ),
    (
        "MEASURES_USING_TIME_INTELLIGENCE_AND_MODEL_IS_USING_DIRECT_QUERY",
        "Performance",
        2,
        "Measures using time intelligence and model is using Direct Query",
        "Time intelligence functions don't perform well with DirectQuery.",
    ),
    (
        "REDUCE_NUMBER_OF_CALCULATED_COLUMNS",
        "Performance",
        2,
        "Reduce number of calculated columns",
        "The model has more than five calculated columns; they compress worse and slow processing.",
    ),
    (
        "CHECK_IF_BI-DIRECTIONAL_AND_MANY-TO-MANY_RELATIONSHIPS_ARE_VALID",
        "Performance",
        1,
        "Check if bi-directional and many-to-many relationships are valid",
        "Make sure these relationships are needed and work as intended.",
    ),
    (
        "CHECK_IF_DYNAMIC_ROW_LEVEL_SECURITY_(RLS)_IS_NECESSARY",
        "Performance",
        1,
        "Check if dynamic row level security (RLS) is necessary",
        "Dynamic RLS using USERNAME or USERPRINCIPALNAME adds memory and performance overhead.",
    ),
    (
        "DAX_COLUMNS_FULLY_QUALIFIED",
        "DAX Expressions",
        3,
        "Column references should be fully qualified",
        "Write column references as 'Table'[Column] so they can't be confused with measures.",
    ),
    (
        "DAX_MEASURES_UNQUALIFIED",
        "DAX Expressions",
        3,
        "Measure references should be unqualified",
        "Write measure references as [Measure], without the table name.",
    ),
    (
        "AVOID_DUPLICATE_MEASURES",
        "DAX Expressions",
        2,
        "No two measures should have the same definition",
        "Measures with identical DAX are redundant.",
    ),
    (
        "USE_THE_TREATAS_FUNCTION_INSTEAD_OF_INTERSECT",
        "DAX Expressions",
        2,
        "Use the TREATAS function instead of INTERSECT for virtual relationships",
        "TREATAS is more efficient than INTERSECT.",
    ),
    (
        "USE_THE_DIVIDE_FUNCTION_FOR_DIVISION",
        "DAX Expressions",
        2,
        "Use the DIVIDE function for division",
        "DIVIDE handles divide-by-zero; the / operator does not.",
    ),
    (
        "AVOID_USING_THE_IFERROR_FUNCTION",
        "DAX Expressions",
        2,
        "Avoid using the IFERROR function",
        "IFERROR can degrade performance; use DIVIDE for divide-by-zero cases.",
    ),
    (
        "MEASURES_SHOULD_NOT_BE_DIRECT_REFERENCES_OF_OTHER_MEASURES",
        "DAX Expressions",
        2,
        "Measures should not be direct references of other measures",
        "A measure that only returns another measure is a duplicate.",
    ),
    (
        "FILTER_COLUMN_VALUES",
        "DAX Expressions",
        2,
        "Filter column values with proper syntax",
        "Use 'Table'[Column] = \"Value\" or KEEPFILTERS instead of FILTER('Table', ...) as a CALCULATE argument.",
    ),
    (
        "FILTER_MEASURE_VALUES_BY_COLUMNS",
        "DAX Expressions",
        2,
        "Filter measure values by columns, not tables",
        "Use FILTER(VALUES('Table'[Column]), [Measure] > x) instead of filtering the whole table.",
    ),
    (
        "INACTIVE_RELATIONSHIPS_THAT_ARE_NEVER_ACTIVATED",
        "DAX Expressions",
        2,
        "Inactive relationships that are never activated",
        "No measure activates these relationships with USERELATIONSHIP.",
    ),
    (
        "AVOID_USING_'1-(X/Y)'_SYNTAX",
        "DAX Expressions",
        2,
        "Avoid using '1-(x/y)' syntax",
        "Rewrite 1 - x/y percentages with DIVIDE for better performance.",
    ),
    (
        "EVALUATEANDLOG_SHOULD_NOT_BE_USED_IN_PRODUCTION_MODELS",
        "DAX Expressions",
        1,
        "The EVALUATEANDLOG function should not be used in production models",
        "EVALUATEANDLOG is meant for development only.",
    ),
    (
        "DATA_COLUMNS_MUST_HAVE_A_SOURCE_COLUMN",
        "Error Prevention",
        3,
        "Data columns must have a source column",
        "A data column without a source column fails when the model is processed.",
    ),
    (
        "EXPRESSION_RELIANT_OBJECTS_MUST_HAVE_AN_EXPRESSION",
        "Error Prevention",
        3,
        "Expression-reliant objects must have an expression",
        "Measures, calculated columns and calculation items without an expression show no values.",
    ),
    (
        "AVOID_STRUCTURED_DATA_SOURCES_WITH_PROVIDER_PARTITIONS",
        "Error Prevention",
        2,
        "Avoid structured data sources with provider partitions",
        "Power BI doesn't support legacy partitions on structured data sources.",
    ),
    (
        "AVOID_THE_USERELATIONSHIP_FUNCTION_AND_RLS_AGAINST_THE_SAME_TABLE",
        "Error Prevention",
        3,
        "Avoid the USERELATIONSHIP function and RLS against the same table",
        "USERELATIONSHIP fails on tables that also have RLS.",
    ),
    (
        "RELATIONSHIP_COLUMNS_SAME_DATA_TYPE",
        "Error Prevention",
        3,
        "Relationship columns should be of the same data type",
        "Relationship columns with different data types can cause errors.",
    ),
    (
        "AVOID_INVALID_NAME_CHARACTERS",
        "Error Prevention",
        3,
        "Avoid invalid characters in names",
        "Control characters in names make deployment fail.",
    ),
    (
        "AVOID_INVALID_DESCRIPTION_CHARACTERS",
        "Error Prevention",
        3,
        "Avoid invalid characters in descriptions",
        "Control characters in descriptions make deployment fail.",
    ),
    (
        "SET_ISAVAILABLEINMDX_TO_TRUE_ON_NECESSARY_COLUMNS",
        "Error Prevention",
        3,
        "Set IsAvailableInMdx to true on necessary columns",
        "Columns used for sorting or in hierarchies need attribute hierarchies.",
    ),
    (
        "UNNECESSARY_COLUMNS",
        "Maintenance",
        2,
        "Remove unnecessary columns",
        "Hidden columns not referenced by DAX, relationships, hierarchies, sort-by or RLS.",
    ),
    (
        "UNNECESSARY_MEASURES",
        "Maintenance",
        2,
        "Remove unnecessary measures",
        "Hidden measures not referenced by any DAX expression.",
    ),
    (
        "FIX_REFERENTIAL_INTEGRITY_VIOLATIONS",
        "Maintenance",
        2,
        "Fix referential integrity violations",
        "Values on the many side have no match on the one side. Needs VertiPaq Analyzer statistics.",
    ),
    (
        "REMOVE_DATA_SOURCES_NOT_REFERENCED_BY_ANY_PARTITIONS",
        "Maintenance",
        1,
        "Remove data sources not referenced by any partitions",
        "No partition or query uses these data sources.",
    ),
    (
        "REMOVE_ROLES_WITH_NO_MEMBERS",
        "Maintenance",
        1,
        "Remove roles with no members",
        "Roles with no members in the files. In Power BI, members are often assigned in the service instead.",
    ),
    (
        "ENSURE_TABLES_HAVE_RELATIONSHIPS",
        "Maintenance",
        1,
        "Ensure tables have relationships",
        "These tables aren't connected to any other table.",
    ),
    (
        "OBJECTS_WITH_NO_DESCRIPTION",
        "Maintenance",
        1,
        "Visible objects with no description",
        "Descriptions show on hover in the field list and help build a data dictionary.",
    ),
    (
        "PERSPECTIVES_WITH_NO_OBJECTS",
        "Maintenance",
        1,
        "Perspectives with no objects",
        "Perspectives with no tables are unnecessary.",
    ),
    (
        "CALCULATION_GROUPS_WITH_NO_CALCULATION_ITEMS",
        "Maintenance",
        2,
        "Calculation groups with no calculation items",
        "A calculation group does nothing without calculation items.",
    ),
    (
        "PARTITION_NAME_SHOULD_MATCH_TABLE_NAME_FOR_SINGLE_PARTITION_TABLES",
        "Naming Conventions",
        1,
        "Partition name should match table name for single partition tables",
        "Name a single partition after its table.",
    ),
    (
        "SPECIAL_CHARS_IN_OBJECT_NAMES",
        "Naming Conventions",
        2,
        "Object names must not contain special characters",
        "Tabs and line breaks in names.",
    ),
    (
        "TRIM_OBJECT_NAMES",
        "Naming Conventions",
        1,
        "Trim object names",
        "Names with leading or trailing spaces.",
    ),
    (
        "FORMAT_FLAG_COLUMNS_AS_YES/NO_VALUE_STRINGS",
        "Formatting",
        1,
        "Format flag columns as Yes/No value strings",
        "Flags read better as Yes/No than 0/1.",
    ),
    (
        "OBJECTS_SHOULD_NOT_START_OR_END_WITH_A_SPACE",
        "Formatting",
        3,
        "Objects should not start or end with a space",
        "Names with leading or trailing spaces.",
    ),
    (
        "DATECOLUMN_FORMATSTRING",
        "Formatting",
        1,
        'Provide format string for "Date" columns',
        "Date columns should use the mm/dd/yyyy format.",
    ),
    (
        "MONTHCOLUMN_FORMATSTRING",
        "Formatting",
        1,
        'Provide format string for "Month" columns',
        "Month date columns should use the MMMM yyyy format.",
    ),
    (
        "PROVIDE_FORMAT_STRING_FOR_MEASURES",
        "Formatting",
        3,
        "Provide format string for measures",
        "Visible measures should have a format string.",
    ),
    (
        "NUMERIC_COLUMN_SUMMARIZE_BY",
        "Formatting",
        3,
        "Do not summarize numeric columns",
        "Set SummarizeBy to None on visible numeric columns and use measures instead.",
    ),
    (
        "PERCENTAGE_FORMATTING",
        "Formatting",
        2,
        "Percentages should be formatted with thousands separators and 1 decimal",
        "Use #,0.0%;-#,0.0%;#,0.0% for percentages.",
    ),
    (
        "INTEGER_FORMATTING",
        "Formatting",
        2,
        "Whole numbers should be formatted with thousands separators and no decimals",
        "Use #,0 for whole-number measures.",
    ),
    (
        "RELATIONSHIP_COLUMNS_SHOULD_BE_OF_INTEGER_DATA_TYPE",
        "Formatting",
        1,
        "Relationship columns should be of integer data type",
        "Integer keys make the best relationships.",
    ),
    (
        "ADD_DATA_CATEGORY_FOR_COLUMNS",
        "Formatting",
        1,
        "Add data category for columns",
        "Country, city, continent, latitude and longitude columns should have a data category.",
    ),
    (
        "HIDE_FOREIGN_KEYS",
        "Formatting",
        2,
        "Hide foreign keys",
        "Columns on the many side of a relationship should be hidden.",
    ),
    (
        "MARK_PRIMARY_KEYS",
        "Formatting",
        1,
        "Mark primary keys",
        "Columns on the one side of a relationship should be marked as keys.",
    ),
    (
        "HIDE_FACT_TABLE_COLUMNS",
        "Formatting",
        2,
        "Hide fact table columns",
        "Numeric columns aggregated by measures should be hidden.",
    ),
    (
        "FIRST_LETTER_OF_OBJECTS_MUST_BE_CAPITALIZED",
        "Formatting",
        1,
        "First letter of objects must be capitalized",
        "Names should start with a capital letter.",
    ),
    (
        "MONTH_(AS_A_STRING)_MUST_BE_SORTED",
        "Formatting",
        2,
        "Month (as a string) must be sorted",
        "Text month columns need a sort-by column, or they sort alphabetically.",
    ),
]
BPA_STATS_RULES = {
    "AVOID_BI-DIRECTIONAL_RELATIONSHIPS_AGAINST_HIGH-CARDINALITY_COLUMNS",
    "REDUCE_USAGE_OF_LONG-LENGTH_COLUMNS_WITH_HIGH_CARDINALITY",
    "SPLIT_DATE_AND_TIME",
    "LARGE_TABLES_SHOULD_BE_PARTITIONED",
    "FIX_REFERENTIAL_INTEGRITY_VIOLATIONS",
}


def _flag(props, key, default=False):
    v = props.get(key, default)
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() == "true"


def _ann_tmdl(o):
    return {
        c["name"]: (c.get("expr") or "").strip().strip('"') for c in o["children"] if c["kw"] == "annotation"
    }


def bpa_inventory_tmdl(def_dir: Path) -> dict:
    inv = {
        "model": {},
        "tables": [],
        "relationships": [],
        "roles": [],
        "perspectives": [],
        "dataSources": [],
        "expressions": [],
    }
    for f in sorted(def_dir.rglob("*.tmdl")):
        if f.parent.name.lower() == "cultures":
            continue
        try:
            roots = parse_tmdl_text(read_text(f))
        except Exception:
            continue
        for o in roots:
            kw, p = o["kw"], o["props"]
            if kw == "model":
                inv["model"] = {
                    "name": o["name"],
                    "dsVersion": str(p.get("defaultPowerBIDataSourceVersion") or ""),
                    "desc": o.get("desc") or "",
                }
            elif kw == "table":
                parts = [c for c in o["children"] if c["kw"] == "partition"]
                is_calc = any((c.get("rest") or "").lower() == "calculated" for c in parts)
                t = {
                    "name": o["name"],
                    "hidden": _flag(p, "isHidden"),
                    "desc": o.get("desc") or "",
                    "dataCategory": str(p.get("dataCategory") or ""),
                    "ann": _ann_tmdl(o),
                    "isCalc": is_calc,
                    "calcGroup": bool(p.get("calculationGroup"))
                    or any(c["kw"] == "calculationItem" for c in o["children"]),
                    "calcItems": [],
                    "partitions": [],
                    "columns": [],
                    "measures": [],
                    "hierarchies": [],
                }
                for c in o["children"]:
                    cp = c["props"]
                    if c["kw"] == "partition":
                        t["partitions"].append(
                            {
                                "name": c["name"],
                                "type": (c.get("rest") or "").lower(),
                                "query": str(cp.get("source") or cp.get("query") or ""),
                                "mode": str(cp.get("mode") or "").lower(),
                                "dataSource": str(cp.get("dataSource") or ""),
                            }
                        )
                    elif c["kw"] == "column":
                        expr = c.get("expr") or ""
                        t["columns"].append(
                            {
                                "name": c["name"],
                                "type": "calculated"
                                if expr
                                else ("calculatedTableColumn" if is_calc else "data"),
                                "dataType": str(cp.get("dataType") or "").lower(),
                                "hidden": _flag(cp, "isHidden"),
                                "isKey": _flag(cp, "isKey"),
                                "mdx": _flag(cp, "isAvailableInMdx", True),
                                "sourceColumn": str(cp.get("sourceColumn") or ""),
                                "expr": expr,
                                "summarizeBy": str(cp.get("summarizeBy") or "").lower(),
                                "formatString": str(cp.get("formatString") or "").strip('"'),
                                "dataCategory": str(cp.get("dataCategory") or ""),
                                "sortBy": unquote(str(cp.get("sortByColumn") or "")),
                                "desc": c.get("desc") or "",
                                "ann": _ann_tmdl(c),
                                "defaultLabel": _flag(cp, "isDefaultLabel"),
                                "alternateOf": any(x["kw"] == "alternateOf" for x in c["children"])
                                or "alternateOf" in cp,
                            }
                        )
                    elif c["kw"] == "measure":
                        t["measures"].append(
                            {
                                "name": c["name"],
                                "expr": c.get("expr") or "",
                                "formatString": str(cp.get("formatString") or "").strip('"'),
                                "fsExpr": str(cp.get("formatStringDefinition") or ""),
                                "hidden": _flag(cp, "isHidden"),
                                "desc": c.get("desc") or "",
                            }
                        )
                    elif c["kw"] == "hierarchy":
                        t["hierarchies"].append(
                            {
                                "name": c["name"],
                                "desc": c.get("desc") or "",
                                "levels": [
                                    {
                                        "name": lv["name"],
                                        "column": unquote(str(lv["props"].get("column") or "")),
                                    }
                                    for lv in c["children"]
                                    if lv["kw"] == "level"
                                ],
                            }
                        )
                    elif c["kw"] == "calculationItem":
                        t["calcItems"].append(
                            {"name": c["name"], "expr": c.get("expr") or "", "desc": c.get("desc") or ""}
                        )
                inv["tables"].append(t)
            elif kw == "relationship":
                ft, fc = split_col_ref(str(p.get("fromColumn") or ""))
                tt, tc = split_col_ref(str(p.get("toColumn") or ""))
                inv["relationships"].append(
                    {
                        "name": o["name"],
                        "fromTable": ft,
                        "fromColumn": fc,
                        "toTable": tt,
                        "toColumn": tc,
                        "fromCard": str(p.get("fromCardinality") or "many").lower(),
                        "toCard": str(p.get("toCardinality") or "one").lower(),
                        "both": str(p.get("crossFilteringBehavior") or "").lower() == "bothdirections",
                        "active": _flag(p, "isActive", True),
                        "ann": _ann_tmdl(o),
                    }
                )
            elif kw == "role":
                inv["roles"].append(
                    {
                        "name": o["name"],
                        "desc": o.get("desc") or "",
                        "members": sum(1 for c in o["children"] if c["kw"] in ("member", "roleMembership")),
                        "perms": [
                            {"table": c["name"], "expr": c.get("expr") or ""}
                            for c in o["children"]
                            if c["kw"] == "tablePermission"
                        ],
                    }
                )
            elif kw == "perspective":
                inv["perspectives"].append(
                    {
                        "name": o["name"],
                        "tables": sum(1 for c in o["children"] if c["kw"] == "perspectiveTable"),
                    }
                )
            elif kw == "dataSource":
                inv["dataSources"].append(
                    {"name": o["name"], "type": str(p.get("type") or "provider").lower()}
                )
            elif kw == "expression":
                inv["expressions"].append({"name": o["name"], "expr": o.get("expr") or ""})
    return inv


def bpa_inventory_bim(path: Path) -> dict:
    data = read_json(path) or {}
    mdl = data.get("model") or {}
    inv = {
        "model": {
            "name": mdl.get("name") or "Model",
            "dsVersion": str(mdl.get("defaultPowerBIDataSourceVersion") or ""),
            "desc": as_text(mdl.get("description")) or "",
        },
        "tables": [],
        "relationships": [],
        "roles": [],
        "perspectives": [],
        "dataSources": [],
        "expressions": [],
    }

    def ann(o):
        return {a.get("name", ""): str(a.get("value", "")) for a in (o.get("annotations") or [])}

    for t in mdl.get("tables") or []:
        parts = t.get("partitions") or []
        is_calc = any((p.get("source") or {}).get("type") == "calculated" for p in parts)
        cg = t.get("calculationGroup")
        tt = {
            "name": t.get("name", ""),
            "hidden": bool(t.get("isHidden")),
            "desc": as_text(t.get("description")) or "",
            "dataCategory": t.get("dataCategory") or "",
            "ann": ann(t),
            "isCalc": is_calc,
            "calcGroup": bool(cg),
            "calcItems": [
                {
                    "name": ci.get("name", ""),
                    "expr": as_text(ci.get("expression")) or "",
                    "desc": as_text(ci.get("description")) or "",
                }
                for ci in (cg or {}).get("calculationItems") or []
            ],
            "partitions": [
                {
                    "name": p.get("name", ""),
                    "type": ((p.get("source") or {}).get("type") or "").lower(),
                    "query": as_text(
                        (p.get("source") or {}).get("expression") or (p.get("source") or {}).get("query")
                    )
                    or "",
                    "mode": str(p.get("mode") or "").lower(),
                    "dataSource": (p.get("source") or {}).get("dataSource") or "",
                }
                for p in parts
            ],
            "columns": [],
            "measures": [],
            "hierarchies": [],
        }
        for c in t.get("columns") or []:
            expr = as_text(c.get("expression")) or ""
            ctype = c.get("type") or (
                "calculated" if expr else ("calculatedTableColumn" if is_calc else "data")
            )
            if ctype == "rowNumber":
                continue
            tt["columns"].append(
                {
                    "name": c.get("name", ""),
                    "type": ctype,
                    "dataType": str(c.get("dataType") or "").lower(),
                    "hidden": bool(c.get("isHidden")),
                    "isKey": bool(c.get("isKey")),
                    "mdx": c.get("isAvailableInMdx", True) is not False,
                    "sourceColumn": c.get("sourceColumn") or "",
                    "expr": expr,
                    "summarizeBy": str(c.get("summarizeBy") or "").lower(),
                    "formatString": c.get("formatString") or "",
                    "dataCategory": c.get("dataCategory") or "",
                    "sortBy": c.get("sortByColumn") or "",
                    "desc": as_text(c.get("description")) or "",
                    "ann": ann(c),
                    "alternateOf": bool(c.get("alternateOf")),
                    "defaultLabel": bool(c.get("isDefaultLabel")),
                }
            )
        for m in t.get("measures") or []:
            tt["measures"].append(
                {
                    "name": m.get("name", ""),
                    "expr": as_text(m.get("expression")) or "",
                    "formatString": m.get("formatString") or "",
                    "fsExpr": as_text((m.get("formatStringDefinition") or {}).get("expression")) or "",
                    "hidden": bool(m.get("isHidden")),
                    "desc": as_text(m.get("description")) or "",
                }
            )
        for h in t.get("hierarchies") or []:
            tt["hierarchies"].append(
                {
                    "name": h.get("name", ""),
                    "desc": as_text(h.get("description")) or "",
                    "levels": [
                        {"name": lv.get("name", ""), "column": lv.get("column", "")}
                        for lv in h.get("levels") or []
                    ],
                }
            )
        inv["tables"].append(tt)
    for r in mdl.get("relationships") or []:
        inv["relationships"].append(
            {
                "name": r.get("name", ""),
                "fromTable": r.get("fromTable", ""),
                "fromColumn": r.get("fromColumn", ""),
                "toTable": r.get("toTable", ""),
                "toColumn": r.get("toColumn", ""),
                "fromCard": str(r.get("fromCardinality") or "many").lower(),
                "toCard": str(r.get("toCardinality") or "one").lower(),
                "both": str(r.get("crossFilteringBehavior") or "").lower() == "bothdirections",
                "active": r.get("isActive", True) is not False,
                "ann": ann(r),
            }
        )
    for ro in mdl.get("roles") or []:
        inv["roles"].append(
            {
                "name": ro.get("name", ""),
                "desc": as_text(ro.get("description")) or "",
                "members": len(ro.get("members") or []),
                "perms": [
                    {"table": tp.get("name", ""), "expr": as_text(tp.get("filterExpression")) or ""}
                    for tp in ro.get("tablePermissions") or []
                ],
            }
        )
    for pe in mdl.get("perspectives") or []:
        inv["perspectives"].append({"name": pe.get("name", ""), "tables": len(pe.get("tables") or [])})
    for ds in mdl.get("dataSources") or []:
        inv["dataSources"].append(
            {"name": ds.get("name", ""), "type": str(ds.get("type") or "provider").lower()}
        )
    for ex in mdl.get("expressions") or []:
        inv["expressions"].append({"name": ex.get("name", ""), "expr": as_text(ex.get("expression")) or ""})
    return inv


def _dax_clean(expr):
    """Drop comments so rule patterns only see code."""
    e = re.sub(r"/\*.*?\*/", " ", expr or "", flags=re.S)
    return re.sub(r"(?m)(//|--).*$", " ", e)


_QREF = re.compile(r"('(?:[^']|'')+'|[A-Za-z_][\w.]*)\s*\[([^\]]+)\]")
_BREF = re.compile(r"(?<![\w'\]])\[([^\]]+)\]")
TI_FUNCS = (
    "CLOSINGBALANCEMONTH|CLOSINGBALANCEQUARTER|CLOSINGBALANCEYEAR|DATEADD|DATESBETWEEN|DATESINPERIOD|DATESMTD|"
    "DATESQTD|DATESYTD|ENDOFMONTH|ENDOFQUARTER|ENDOFYEAR|FIRSTDATE|FIRSTNONBLANK|FIRSTNONBLANKVALUE|LASTDATE|"
    "LASTNONBLANK|LASTNONBLANKVALUE|NEXTDAY|NEXTMONTH|NEXTQUARTER|NEXTYEAR|OPENINGBALANCEMONTH|"
    "OPENINGBALANCEQUARTER|OPENINGBALANCEYEAR|PARALLELPERIOD|PREVIOUSDAY|PREVIOUSMONTH|PREVIOUSQUARTER|"
    "PREVIOUSYEAR|SAMEPERIODLASTYEAR|STARTOFMONTH|STARTOFQUARTER|STARTOFYEAR|TOTALMTD|TOTALQTD|TOTALYTD"
)


def _refs(expr):
    """Qualified (table, name) and unqualified names referenced by a DAX expression."""
    e = _dax_clean(expr)
    e = re.sub(r'"(?:[^"]|"")*"', '""', e)  # ignore text inside strings
    qual = [(unquote(m.group(1)), m.group(2)) for m in _QREF.finditer(e)]
    spans = [m.span() for m in _QREF.finditer(e)]
    bare = []
    for m in _BREF.finditer(e):
        if not any(a <= m.start() < b for a, b in spans):
            bare.append(m.group(1))
    return qual, bare


_AUTO_DATE_IN_TEXT = re.compile(r"(?:LocalDateTable_|DateTableTemplate_)")
# Power BI generates these tables and you cannot edit them, so Microsoft's rules
# leave them out - except the one that tells you to turn the feature off.
BPA_AUTO_DATE_RULES = {"REMOVE_AUTO-DATE_TABLE"}


def _on_auto_date(kind, name, table):
    """True when a finding is about a generated date table rather than your model."""
    if table:
        return is_auto_table(table)
    if kind in ("table", "partition"):
        return is_auto_table(name)
    if kind == "relationship":
        return bool(_AUTO_DATE_IN_TEXT.search(name))
    return False


def bpa_evaluate(inv: dict) -> tuple:
    """Runs every rule. Returns {rule_id: [finding, ...]} and the set of rules that could not run."""
    out = defaultdict(list)
    skipped = set()
    # Generated date tables are left out of every rule, including the counts the
    # model-wide rules add up; the auto-date rule below reads them separately.
    auto_tables = [t for t in inv["tables"] if is_auto_table(t["name"])]
    T = [t for t in inv["tables"] if not is_auto_table(t["name"])]
    rels = [
        r for r in inv["relationships"] if not (is_auto_table(r["fromTable"]) or is_auto_table(r["toTable"]))
    ]
    cols_by_table = {t["name"]: {c["name"]: c for c in t["columns"]} for t in T}
    measure_names = {m["name"] for t in T for m in t["measures"]}
    all_cols = [(t, c) for t in T for c in t["columns"]]
    all_meas = [(t, m) for t in T for m in t["measures"]]
    rls = defaultdict(list)  # table -> RLS expressions
    for ro in inv["roles"]:
        for pm in ro["perms"]:
            if pm["expr"]:
                rls[pm["table"]].append(pm["expr"])
    rel_cols = set()
    for r in rels:
        rel_cols.add((r["fromTable"], r["fromColumn"]))
        rel_cols.add((r["toTable"], r["toColumn"]))
    sort_targets = {(t["name"], c["sortBy"]) for t, c in all_cols if c["sortBy"]}
    hier_cols = {(t["name"], lv["column"]) for t in T for h in t["hierarchies"] for lv in h["levels"]}
    any_stats = (
        any(
            (
                "Vertipaq_Cardinality" in c["ann"]
                or "LongLengthRowCount" in c["ann"]
                or "DateTimeWithHourMinSec" in c["ann"]
            )
            for t, c in all_cols
        )
        or any("Vertipaq_RowCount" in t["ann"] for t in T)
        or any("Vertipaq_RIViolationInvalidRows" in r["ann"] for r in rels)
    )
    if not any_stats:
        skipped |= BPA_STATS_RULES

    def add(rule, kind, name, table="", note=""):
        if rule not in BPA_AUTO_DATE_RULES and _on_auto_date(kind, name, table):
            return
        out[rule].append({"kind": kind, "name": name, "table": table, "note": note})

    def rel_label(r):
        return f"{r['fromTable']}[{r['fromColumn']}] → {r['toTable']}[{r['toColumn']}]"

    for t in auto_tables:  # the one rule that is about them
        if t["isCalc"]:
            add("REMOVE_AUTO-DATE_TABLE", "table", t["name"])

    # DAX expressions to scan, with what owns them
    dax_objs = (
        [("measure", t["name"], m["name"], m["expr"]) for t, m in all_meas]
        + [("column", t["name"], c["name"], c["expr"]) for t, c in all_cols if c["type"] == "calculated"]
        + [("calculationItem", t["name"], ci["name"], ci["expr"]) for t in T for ci in t["calcItems"]]
        + [
            ("tablePermission", pm["table"], ro["name"], pm["expr"])
            for ro in inv["roles"]
            for pm in ro["perms"]
        ]
        + [
            ("table", t["name"], t["name"], p["query"])
            for t in T
            for p in t["partitions"]
            if p["type"] == "calculated"
        ]
    )
    ref_cols, ref_meas = set(), set()
    for _kind, _tname, _name, expr in dax_objs:
        qual, bare = _refs(expr)
        for tb, nm in qual:
            if nm in cols_by_table.get(tb, {}):
                ref_cols.add((tb, nm))
            elif nm in measure_names:
                ref_meas.add(nm)
        for nm in bare:
            if nm in measure_names:
                ref_meas.add(nm)
            for tb, cs in cols_by_table.items():
                if nm in cs:
                    ref_cols.add((tb, nm))
    dq = any(p["mode"] == "directquery" for t in T for p in t["partitions"])

    # ---------------- Performance ----------------
    for t, c in all_cols:
        if c["dataType"] == "double":
            add("AVOID_FLOATING_POINT_DATA_TYPES", "column", c["name"], t["name"])
        if (
            c["mdx"]
            and (c["hidden"] or t["hidden"])
            and (t["name"], c["name"]) not in sort_targets
            and (t["name"], c["name"]) not in hier_cols
            and not c["sortBy"]
        ):
            add("ISAVAILABLEINMDX_FALSE_NONATTRIBUTE_COLUMNS", "column", c["name"], t["name"])
        if any_stats:
            try:
                card = int(float(c["ann"].get("Vertipaq_Cardinality", "0") or 0))
            except ValueError:
                card = 0
            if card > 100000 and any(
                r["both"]
                and (t["name"], c["name"])
                in {(r["fromTable"], r["fromColumn"]), (r["toTable"], r["toColumn"])}
                for r in rels
            ):
                add(
                    "AVOID_BI-DIRECTIONAL_RELATIONSHIPS_AGAINST_HIGH-CARDINALITY_COLUMNS",
                    "column",
                    c["name"],
                    t["name"],
                    f"{card:,} distinct values",
                )
            try:
                if int(float(c["ann"].get("LongLengthRowCount", "0") or 0)) > 500000:
                    add(
                        "REDUCE_USAGE_OF_LONG-LENGTH_COLUMNS_WITH_HIGH_CARDINALITY",
                        "column",
                        c["name"],
                        t["name"],
                    )
                if int(float(c["ann"].get("DateTimeWithHourMinSec", "0") or 0)) > 0:
                    add("SPLIT_DATE_AND_TIME", "column", c["name"], t["name"])
            except ValueError:
                pass
        if c["type"] == "calculated" and re.search(r"(?i)RELATED\s*\(", _dax_clean(c["expr"])):
            add(
                "REDUCE_USAGE_OF_CALCULATED_COLUMNS_THAT_USE_THE_RELATED_FUNCTION",
                "column",
                c["name"],
                t["name"],
            )
    for t in T:
        tn = t["name"]
        if any_stats:
            try:
                if (
                    int(float(t["ann"].get("Vertipaq_RowCount", "0") or 0)) > 25000000
                    and len(t["partitions"]) == 1
                ):
                    add("LARGE_TABLES_SHOULD_BE_PARTITIONED", "table", tn)
            except ValueError:
                pass
        if any(r["fromTable"] == tn for r in rels) and any(r["toTable"] == tn for r in rels):
            add("SNOWFLAKE_SCHEMA_ARCHITECTURE", "table", tn)
        date_key = any(c["isKey"] and c["dataType"] == "datetime" for c in t["columns"])
        if ("DATE" in tn.upper() or "CALENDAR" in tn.upper()) and (
            t["dataCategory"].lower() != "time" or not date_key
        ):
            add("DATE/CALENDAR_TABLES_SHOULD_BE_MARKED_AS_A_DATE_TABLE", "table", tn)
        if any(
            re.search(r"(?i)(RIGHT|LEFT|UPPER|LOWER|FIND)\s*\(", e.replace(" ", "")) for e in rls.get(tn, [])
        ):
            add("LIMIT_ROW_LEVEL_SECURITY_(RLS)_LOGIC", "table", tn)
        for p in t["partitions"]:
            if p["type"] == "m" and re.search(
                r"Table\.(Combine|Join|NestedJoin|AddColumn|Group|Sort|Pivot|Unpivot|"
                r"UnpivotOtherColumns|Distinct)\(|\[Query=\"SELECT|Value\.NativeQuery|"
                r"OleDb\.Query|Odbc\.Query",
                p["query"],
            ):
                add("MINIMIZE_POWER_QUERY_TRANSFORMATIONS", "partition", p["name"], tn)
            if p["type"] == "query" and any(
                d["name"] == p["dataSource"] and d["type"] == "structured" for d in inv["dataSources"]
            ):
                add("AVOID_STRUCTURED_DATA_SOURCES_WITH_PROVIDER_PARTITIONS", "partition", p["name"], tn)
        if rls.get(tn) and any(
            r["fromCard"] == "many" and r["toCard"] == "many" and tn in (r["fromTable"], r["toTable"])
            for r in rels
        ):
            add(
                "AVOID_USING_MANY-TO-MANY_RELATIONSHIPS_ON_TABLES_USED_FOR_DYNAMIC_ROW_LEVEL_SECURITY",
                "table",
                tn,
            )
        numeric = [c["name"].upper() for c in t["columns"] if c["dataType"] in ("int64", "decimal", "double")]
        if all(any(mo in n for n in numeric) for mo in ("JAN", "FEB", "MAR", "APR", "MAY", "JUN")):
            add("UNPIVOT_PIVOTED_(MONTH)_DATA", "table", tn)
        if t["isCalc"]:
            add("REDUCE_USAGE_OF_CALCULATED_TABLES", "table", tn)
    if not any(
        t["dataCategory"].lower() == "time"
        and any(c["isKey"] and c["dataType"] == "datetime" for c in t["columns"])
        for t in T
    ):
        add("MODEL_SHOULD_HAVE_A_DATE_TABLE", "model", inv["model"].get("name") or "Model")
    if rels:
        heavy = sum(1 for r in rels if r["both"]) + sum(
            1 for r in rels if r["fromCard"] == "many" and r["toCard"] == "many"
        )
        if heavy / max(len(rels), 1) > 0.3:
            add(
                "AVOID_EXCESSIVE_BI-DIRECTIONAL_OR_MANY-TO-MANY_RELATIONSHIPS",
                "model",
                inv["model"].get("name") or "Model",
                note=f"{heavy} of {len(rels)} relationships",
            )
    if (
        dq
        and not any(c["alternateOf"] for t, c in all_cols)
        and inv["model"].get("dsVersion", "").lower() == "powerbi_v3"
    ):
        add("MODEL_USING_DIRECT_QUERY_AND_NO_AGGREGATIONS", "model", inv["model"].get("name") or "Model")
    for r in rels:
        m2m = r["fromCard"] == "many" and r["toCard"] == "many"
        if m2m and r["both"]:
            add("MANY-TO-MANY_RELATIONSHIPS_SHOULD_BE_SINGLE-DIRECTION", "relationship", rel_label(r))
        if m2m or r["both"]:
            add(
                "CHECK_IF_BI-DIRECTIONAL_AND_MANY-TO-MANY_RELATIONSHIPS_ARE_VALID",
                "relationship",
                rel_label(r),
                note=("many-to-many" if m2m else "")
                + (" · " if m2m and r["both"] else "")
                + ("both directions" if r["both"] else ""),
            )
        if any_stats:
            try:
                if int(float(r["ann"].get("Vertipaq_RIViolationInvalidRows", "0") or 0)) > 0:
                    add("FIX_REFERENTIAL_INTEGRITY_VIOLATIONS", "relationship", rel_label(r))
            except ValueError:
                pass
    related = defaultdict(set)  # table -> tables it points at
    for r in rels:
        related[r["fromTable"]].add(r["toTable"])
    for t, c in all_cols:
        if (t["name"], c["name"]) in rel_cols:
            continue
        if any(c["name"] in cols_by_table.get(o, {}) for o in related.get(t["name"], ())):
            add("REMOVE_REDUNDANT_COLUMNS_IN_RELATED_TABLES", "column", c["name"], t["name"])
    for t, m in all_meas:
        if dq and re.search(r"(?:" + TI_FUNCS + r")\s*\(", _dax_clean(m["expr"])):
            add(
                "MEASURES_USING_TIME_INTELLIGENCE_AND_MODEL_IS_USING_DIRECT_QUERY",
                "measure",
                m["name"],
                t["name"],
            )
    calc_cols = sum(1 for t, c in all_cols if c["type"] == "calculated")
    if calc_cols > 5:
        add(
            "REDUCE_NUMBER_OF_CALCULATED_COLUMNS",
            "model",
            inv["model"].get("name") or "Model",
            note=f"{calc_cols} calculated columns",
        )
    for ro in inv["roles"]:
        for pm in ro["perms"]:
            if re.search(r"(?i)USERNAME\(|USERPRINCIPALNAME\(", pm["expr"]):
                add(
                    "CHECK_IF_DYNAMIC_ROW_LEVEL_SECURITY_(RLS)_IS_NECESSARY",
                    "tablePermission",
                    pm["table"],
                    note="role " + ro["name"],
                )

    # ---------------- DAX Expressions ----------------
    col_names = {n for cs in cols_by_table.values() for n in cs}

    def norm(e):
        return re.sub(r"\s+", "", e or "")

    seen_defs = defaultdict(list)
    for t, m in all_meas:
        if m["expr"].strip():
            seen_defs[norm(m["expr"])].append((t["name"], m["name"]))
    for kind, tname, name, expr in dax_objs:
        if kind == "table" or not expr:
            continue
        qual, bare = _refs(expr)
        clean = _dax_clean(expr)
        if kind in ("measure", "tablePermission", "calculationItem") and any(
            b in col_names and b not in measure_names for b in bare
        ):
            add(
                "DAX_COLUMNS_FULLY_QUALIFIED",
                kind,
                name,
                tname,
                ", ".join(sorted({"[" + b + "]" for b in bare if b in col_names and b not in measure_names})),
            )
        if kind in ("measure", "column", "calculationItem") and any(
            nm in measure_names and nm not in cols_by_table.get(tb, {}) for tb, nm in qual
        ):
            add("DAX_MEASURES_UNQUALIFIED", kind, name, tname)
        if kind in ("measure", "calculationItem") and re.search(r"(?i)INTERSECT\s*\(", clean):
            add("USE_THE_TREATAS_FUNCTION_INSTEAD_OF_INTERSECT", kind, name, tname)
        if kind in ("measure", "column", "calculationItem"):
            if re.search(r"[\])]\s*/(?![/*])", clean):
                add("USE_THE_DIVIDE_FUNCTION_FOR_DIVISION", kind, name, tname)
            if re.search(
                r"(?i)CALCULATE\s*\(\s*[^,]+,\s*FILTER\s*\(\s*'*[A-Za-z0-9 _]+'*\s*,\s*'*[A-Za-z0-9 _]+'*\[[A-Za-z0-9 _]+\]",
                clean,
            ) or re.search(
                r"(?i)CALCULATETABLE\s*\([^,]*,\s*FILTER\s*\(\s*'*[A-Za-z0-9 _]+'*,\s*'*[A-Za-z0-9 _]+'*\[[A-Za-z0-9 _]+\]",
                clean,
            ):
                add("FILTER_COLUMN_VALUES", kind, name, tname)
            if re.search(
                r"(?i)CALCULATE\s*\(\s*[^,]+,\s*FILTER\s*\(\s*'*[A-Za-z0-9 _]+'*\s*,\s*\[[^\]]+\]", clean
            ) or re.search(r"(?i)CALCULATETABLE\s*\([^,]*,\s*FILTER\s*\(\s*'*[A-Za-z0-9 _]+'*,\s*\[", clean):
                add("FILTER_MEASURE_VALUES_BY_COLUMNS", kind, name, tname)
            if re.search(
                r"[0-9]+\s*[-+]\s*[(]*\s*(?i:SUM)\s*\(\s*'*[A-Za-z0-9 _]+'*\s*\[[A-Za-z0-9 _]+\]\s*\)\s*/",
                clean,
            ) or re.search(r"[0-9]+\s*[-+]\s*(?i:DIVIDE)\s*\(", clean):
                add("AVOID_USING_'1-(X/Y)'_SYNTAX", kind, name, tname)
        if kind in ("measure", "column") and re.search(r"(?i)IFERROR\s*\(", clean):
            add("AVOID_USING_THE_IFERROR_FUNCTION", kind, name, tname)
        if kind == "measure":
            if len(seen_defs.get(norm(expr), [])) > 1:
                others = [n for tb, n in seen_defs[norm(expr)] if n != name]
                add("AVOID_DUPLICATE_MEASURES", kind, name, tname, "same as " + ", ".join(others))
            if (
                re.fullmatch(r"\s*\[([^\]]+)\]\s*", clean)
                and re.fullmatch(r"\s*\[([^\]]+)\]\s*", clean).group(1) in measure_names
            ):
                add("MEASURES_SHOULD_NOT_BE_DIRECT_REFERENCES_OF_OTHER_MEASURES", kind, name, tname)
            if re.search(r"(?i)EVALUATEANDLOG\s*\(", clean):
                add("EVALUATEANDLOG_SHOULD_NOT_BE_USED_IN_PRODUCTION_MODELS", kind, name, tname)
    all_dax = (
        "\n".join(_dax_clean(m["expr"]) for t, m in all_meas)
        + "\n"
        + "\n".join(_dax_clean(ci["expr"]) for t in T for ci in t["calcItems"])
    )
    for r in rels:
        if r["active"]:
            continue
        pat = (
            r"(?i)USERELATIONSHIP\s*\(\s*'*"
            + re.escape(r["fromTable"])
            + r"'*\["
            + re.escape(r["fromColumn"])
            + r"\]\s*,\s*'*"
            + re.escape(r["toTable"])
            + r"'*\["
            + re.escape(r["toColumn"])
            + r"\]"
        )
        pat2 = (
            r"(?i)USERELATIONSHIP\s*\(\s*'*"
            + re.escape(r["toTable"])
            + r"'*\["
            + re.escape(r["toColumn"])
            + r"\]\s*,\s*'*"
            + re.escape(r["fromTable"])
            + r"'*\["
            + re.escape(r["fromColumn"])
            + r"\]"
        )
        if not re.search(pat, all_dax) and not re.search(pat2, all_dax):
            add("INACTIVE_RELATIONSHIPS_THAT_ARE_NEVER_ACTIVATED", "relationship", rel_label(r))

    # ---------------- Error Prevention ----------------
    for t, c in all_cols:
        if c["type"] == "data" and not c["sourceColumn"].strip() and not t["calcGroup"]:
            add("DATA_COLUMNS_MUST_HAVE_A_SOURCE_COLUMN", "column", c["name"], t["name"])
        if c["type"] == "calculated" and not c["expr"].strip():
            add("EXPRESSION_RELIANT_OBJECTS_MUST_HAVE_AN_EXPRESSION", "column", c["name"], t["name"])
        if not c["mdx"] and (
            (t["name"], c["name"]) in sort_targets or (t["name"], c["name"]) in hier_cols or c["sortBy"]
        ):
            add("SET_ISAVAILABLEINMDX_TO_TRUE_ON_NECESSARY_COLUMNS", "column", c["name"], t["name"])
    for t, m in all_meas:
        if not m["expr"].strip():
            add("EXPRESSION_RELIANT_OBJECTS_MUST_HAVE_AN_EXPRESSION", "measure", m["name"], t["name"])
    for t in T:
        for ci in t["calcItems"]:
            if not ci["expr"].strip():
                add(
                    "EXPRESSION_RELIANT_OBJECTS_MUST_HAVE_AN_EXPRESSION",
                    "calculationItem",
                    ci["name"],
                    t["name"],
                )
        if rls.get(t["name"]) and re.search(
            r"(?i)USERELATIONSHIP\s*\(\s*.+?(?=])\]\s*,\s*'*" + re.escape(t["name"]) + r"'*\[", all_dax
        ):
            add("AVOID_THE_USERELATIONSHIP_FUNCTION_AND_RLS_AGAINST_THE_SAME_TABLE", "table", t["name"])
    for r in rels:
        a = cols_by_table.get(r["fromTable"], {}).get(r["fromColumn"])
        b = cols_by_table.get(r["toTable"], {}).get(r["toColumn"])
        if a and b and a["dataType"] and b["dataType"] and a["dataType"] != b["dataType"]:
            add(
                "RELATIONSHIP_COLUMNS_SAME_DATA_TYPE",
                "relationship",
                rel_label(r),
                note=f"{a['dataType']} vs {b['dataType']}",
            )

    def ctrl(sv):
        return any((ord(ch) < 32 and ch not in "\t\n\r") or ord(ch) == 127 for ch in sv or "")

    named = (
        [("table", t["name"], "", t["desc"]) for t in T]
        + [("column", c["name"], t["name"], c["desc"]) for t, c in all_cols]
        + [("measure", m["name"], t["name"], m["desc"]) for t, m in all_meas]
        + [("hierarchy", h["name"], t["name"], h["desc"]) for t in T for h in t["hierarchies"]]
        + [("partition", p["name"], t["name"], "") for t in T for p in t["partitions"]]
        + [("calculationItem", ci["name"], t["name"], ci["desc"]) for t in T for ci in t["calcItems"]]
        + [("role", ro["name"], "", ro["desc"]) for ro in inv["roles"]]
        + [("perspective", pe["name"], "", "") for pe in inv["perspectives"]]
    )
    for kind, name, tname, desc in named:
        if ctrl(name):
            add("AVOID_INVALID_NAME_CHARACTERS", kind, name, tname)
        if ctrl(desc):
            add("AVOID_INVALID_DESCRIPTION_CHARACTERS", kind, name, tname)
        if kind in (
            "table",
            "measure",
            "hierarchy",
            "perspective",
            "partition",
            "column",
            "calculationItem",
        ) and any(ch in name for ch in "\t\n\r"):
            add("SPECIAL_CHARS_IN_OBJECT_NAMES", kind, name, tname)
        if name != name.strip():
            add("TRIM_OBJECT_NAMES", kind, name, tname)
            if kind in ("table", "measure", "hierarchy", "perspective", "partition", "column"):
                add("OBJECTS_SHOULD_NOT_START_OR_END_WITH_A_SPACE", kind, name, tname)

    # ---------------- Maintenance ----------------
    rls_text = "\n".join(e for es in rls.values() for e in es)
    for t, c in all_cols:
        key = (t["name"], c["name"])
        if (
            (c["hidden"] or t["hidden"])
            and key not in ref_cols
            and key not in rel_cols
            and key not in sort_targets
            and key not in hier_cols
            and ("[" + c["name"] + "]").lower() not in rls_text.lower()
        ):
            add("UNNECESSARY_COLUMNS", "column", c["name"], t["name"])
    for t, m in all_meas:
        if (m["hidden"] or t["hidden"]) and m["name"] not in ref_meas:
            add("UNNECESSARY_MEASURES", "measure", m["name"], t["name"])
    used_sources = " ".join(
        p["dataSource"] + " " + p["query"] for t in T for p in t["partitions"]
    ) + " ".join(e["expr"] for e in inv["expressions"])
    for d in inv["dataSources"]:
        if d["name"] not in used_sources:
            add("REMOVE_DATA_SOURCES_NOT_REFERENCED_BY_ANY_PARTITIONS", "dataSource", d["name"])
    for ro in inv["roles"]:
        if ro["members"] == 0:
            add("REMOVE_ROLES_WITH_NO_MEMBERS", "role", ro["name"])
    rel_tables = {r["fromTable"] for r in rels} | {r["toTable"] for r in rels}
    for t in T:
        auto = t["name"].startswith("LocalDateTable_") or t["name"].startswith("DateTableTemplate_")
        if t["name"] not in rel_tables and not auto:
            add("ENSURE_TABLES_HAVE_RELATIONSHIPS", "table", t["name"])
        if t["calcGroup"] and not t["calcItems"]:
            add("CALCULATION_GROUPS_WITH_NO_CALCULATION_ITEMS", "table", t["name"])
        if not t["hidden"] and not t["desc"].strip() and not auto:
            add("OBJECTS_WITH_NO_DESCRIPTION", "table", t["name"])
        if len(t["partitions"]) == 1 and t["partitions"][0]["name"] != t["name"]:
            add(
                "PARTITION_NAME_SHOULD_MATCH_TABLE_NAME_FOR_SINGLE_PARTITION_TABLES",
                "table",
                t["name"],
                note="partition " + t["partitions"][0]["name"],
            )
    for t, c in all_cols:
        if not c["hidden"] and not t["hidden"] and not c["desc"].strip():
            add("OBJECTS_WITH_NO_DESCRIPTION", "column", c["name"], t["name"])
    for t, m in all_meas:
        if not m["hidden"] and not m["desc"].strip():
            add("OBJECTS_WITH_NO_DESCRIPTION", "measure", m["name"], t["name"])
    for pe in inv["perspectives"]:
        if pe["tables"] == 0:
            add("PERSPECTIVES_WITH_NO_OBJECTS", "perspective", pe["name"])

    # ---------------- Formatting ----------------
    agg = re.compile(
        r"(?i)(COUNT|COUNTBLANK|SUM|AVERAGE|VALUES|DISTINCT|DISTINCTCOUNT|MIN|MAX|COUNTA|AVERAGEA|MAXA|MINA)"
        r"\s*\(\s*'*([^'\[]+?)'*\[([^\]]+)\]\s*\)"
    )
    aggregated = set()
    for _t, m in all_meas:
        for mm in agg.finditer(_dax_clean(m["expr"])):
            aggregated.add((mm.group(2).strip(), mm.group(3)))
    for t, c in all_cols:
        visible = not (c["hidden"] or t["hidden"])
        nm, dt, key = c["name"], c["dataType"], (t["name"], c["name"])
        if visible and ((nm.startswith("Is") and dt == "int64") or (nm.endswith(" Flag") and dt != "string")):
            add("FORMAT_FLAG_COLUMNS_AS_YES/NO_VALUE_STRINGS", "column", nm, t["name"])
        if "date" in nm.lower() and dt == "datetime" and c["formatString"] != "mm/dd/yyyy":
            add("DATECOLUMN_FORMATSTRING", "column", nm, t["name"], c["formatString"] or "no format string")
        if "month" in nm.lower() and dt == "datetime" and c["formatString"] != "MMMM yyyy":
            add("MONTHCOLUMN_FORMATSTRING", "column", nm, t["name"], c["formatString"] or "no format string")
        if dt in ("int64", "decimal", "double") and c["summarizeBy"] != "none" and visible:
            add(
                "NUMERIC_COLUMN_SUMMARIZE_BY",
                "column",
                nm,
                t["name"],
                "summarizes by " + (c["summarizeBy"] or "default"),
            )
        if key in rel_cols and dt and dt != "int64":
            add("RELATIONSHIP_COLUMNS_SHOULD_BE_OF_INTEGER_DATA_TYPE", "column", nm, t["name"], dt)
        low = nm.lower()
        if not c["dataCategory"] and (
            (any(w in low for w in ("country", "continent", "city")) and dt == "string")
            or (low in ("latitude", "longitude") and dt in ("decimal", "double"))
        ):
            add("ADD_DATA_CATEGORY_FOR_COLUMNS", "column", nm, t["name"])
        if not c["hidden"] and any(
            r["fromTable"] == t["name"] and r["fromColumn"] == nm and r["fromCard"] == "many" for r in rels
        ):
            add("HIDE_FOREIGN_KEYS", "column", nm, t["name"])
        if (
            not c["isKey"]
            and t["dataCategory"].lower() != "time"
            and any(r["toTable"] == t["name"] and r["toColumn"] == nm and r["toCard"] == "one" for r in rels)
        ):
            add("MARK_PRIMARY_KEYS", "column", nm, t["name"])
        if not c["hidden"] and dt in ("int64", "decimal", "double") and key in aggregated:
            add("HIDE_FACT_TABLE_COLUMNS", "column", nm, t["name"])
        if c["type"] != "data" and nm[:1] and nm[:1].upper() != nm[:1]:
            add("FIRST_LETTER_OF_OBJECTS_MUST_BE_CAPITALIZED", "column", nm, t["name"])
        if "MONTH" in nm.upper() and "MONTHS" not in nm.upper() and dt == "string" and not c["sortBy"]:
            add("MONTH_(AS_A_STRING)_MUST_BE_SORTED", "column", nm, t["name"])
    for t, m in all_meas:
        visible = not (m["hidden"] or t["hidden"])
        fs = m["formatString"]
        if visible and not fs.strip() and not m["fsExpr"].strip():
            add("PROVIDE_FORMAT_STRING_FOR_MEASURES", "measure", m["name"], t["name"])
        if "%" in fs and fs != "#,0.0%;-#,0.0%;#,0.0%":
            add("PERCENTAGE_FORMATTING", "measure", m["name"], t["name"], fs)
        if "$" not in fs and "%" not in fs and fs not in ("#,0", "#,0.0"):
            add("INTEGER_FORMATTING", "measure", m["name"], t["name"], fs or "no format string")
        if m["name"][:1] and m["name"][:1].upper() != m["name"][:1]:
            add("FIRST_LETTER_OF_OBJECTS_MUST_BE_CAPITALIZED", "measure", m["name"], t["name"])
    for t in T:
        if t["name"][:1] and t["name"][:1].upper() != t["name"][:1]:
            add("FIRST_LETTER_OF_OBJECTS_MUST_BE_CAPITALIZED", "table", t["name"])
        for h in t["hierarchies"]:
            if h["name"][:1] and h["name"][:1].upper() != h["name"][:1]:
                add("FIRST_LETTER_OF_OBJECTS_MUST_BE_CAPITALIZED", "hierarchy", h["name"], t["name"])
    return out, skipped
