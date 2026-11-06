# SPDX-License-Identifier: Apache-2.0
"""Short help for DAX functions: syntax and a one-line description.

Shown when you point at a function in the DAX of a measure, column, table or
calculation item. Each entry links to the function's page on Microsoft Learn,
which has the full reference.
"""

DAX_FUNCTIONS = {
    # Aggregation
    "APPROXIMATEDISTINCTCOUNT": (
        "APPROXIMATEDISTINCTCOUNT(<column>)",
        "An estimated count of the distinct values in a column, for DirectQuery sources.",
    ),
    "AVERAGE": ("AVERAGE(<column>)", "The average (arithmetic mean) of the numbers in a column."),
    "AVERAGEA": ("AVERAGEA(<column>)", "The average of a column, counting text as 0 and TRUE as 1."),
    "AVERAGEX": (
        "AVERAGEX(<table>, <expression>)",
        "The average of an expression evaluated for each row of a table.",
    ),
    "COUNT": ("COUNT(<column>)", "Counts the non-blank values in a column."),
    "COUNTA": ("COUNTA(<column>)", "Counts the non-blank values in a column of any type."),
    "COUNTAX": ("COUNTAX(<table>, <expression>)", "Counts the rows where an expression is not blank."),
    "COUNTBLANK": ("COUNTBLANK(<column>)", "Counts the blank cells in a column."),
    "COUNTROWS": ("COUNTROWS([<table>])", "Counts the rows of a table."),
    "COUNTX": (
        "COUNTX(<table>, <expression>)",
        "Counts the rows where an expression gives a number or non-blank value.",
    ),
    "DISTINCTCOUNT": ("DISTINCTCOUNT(<column>)", "Counts the distinct values in a column, blank included."),
    "DISTINCTCOUNTNOBLANK": (
        "DISTINCTCOUNTNOBLANK(<column>)",
        "Counts the distinct values in a column, leaving out blank.",
    ),
    "MAX": (
        "MAX(<column>) | MAX(<expression1>, <expression2>)",
        "The largest value in a column, or the larger of two values.",
    ),
    "MAXA": ("MAXA(<column>)", "The largest value in a column, counting TRUE as 1 and FALSE as 0."),
    "MAXX": (
        "MAXX(<table>, <expression>[, <variant>])",
        "The largest value of an expression evaluated for each row of a table.",
    ),
    "MIN": (
        "MIN(<column>) | MIN(<expression1>, <expression2>)",
        "The smallest value in a column, or the smaller of two values.",
    ),
    "MINA": ("MINA(<column>)", "The smallest value in a column, counting TRUE as 1 and FALSE as 0."),
    "MINX": (
        "MINX(<table>, <expression>[, <variant>])",
        "The smallest value of an expression evaluated for each row of a table.",
    ),
    "PRODUCT": ("PRODUCT(<column>)", "Multiplies the numbers in a column."),
    "PRODUCTX": (
        "PRODUCTX(<table>, <expression>)",
        "Multiplies an expression evaluated for each row of a table.",
    ),
    "SUM": ("SUM(<column>)", "Adds up the numbers in a column."),
    "SUMX": ("SUMX(<table>, <expression>)", "Adds up an expression evaluated for each row of a table."),
    # Date and time
    "CALENDAR": (
        "CALENDAR(<start_date>, <end_date>)",
        "A one-column table of every date from the start date to the end date.",
    ),
    "CALENDARAUTO": (
        "CALENDARAUTO([<fiscal_year_end_month>])",
        "A table of dates covering every date in the model, in whole years.",
    ),
    "DATE": ("DATE(<year>, <month>, <day>)", "A date from a year, month and day."),
    "DATEDIFF": (
        "DATEDIFF(<date1>, <date2>, <interval>)",
        "The number of interval boundaries (DAY, MONTH, YEAR and so on) between two dates.",
    ),
    "DATEVALUE": ("DATEVALUE(<date_text>)", "Converts a date in text form to a date."),
    "DAY": ("DAY(<datetime>)", "The day of the month, from 1 to 31."),
    "EDATE": ("EDATE(<start_date>, <months>)", "The date a number of months before or after a date."),
    "EOMONTH": (
        "EOMONTH(<start_date>, <months>)",
        "The last day of the month, a number of months before or after a date.",
    ),
    "HOUR": ("HOUR(<datetime>)", "The hour, from 0 to 23."),
    "MINUTE": ("MINUTE(<datetime>)", "The minute, from 0 to 59."),
    "MONTH": ("MONTH(<datetime>)", "The month, from 1 (January) to 12 (December)."),
    "NETWORKDAYS": (
        "NETWORKDAYS(<start_date>, <end_date>[, <weekend>, <holidays>])",
        "The number of whole working days between two dates.",
    ),
    "NOW": ("NOW()", "The current date and time."),
    "QUARTER": ("QUARTER(<date>)", "The quarter, from 1 to 4."),
    "SECOND": ("SECOND(<datetime>)", "The seconds, from 0 to 59."),
    "TIME": ("TIME(<hour>, <minute>, <second>)", "A time from hours, minutes and seconds."),
    "TIMEVALUE": ("TIMEVALUE(<time_text>)", "Converts a time in text form to a time."),
    "TODAY": ("TODAY()", "The current date."),
    "UTCNOW": ("UTCNOW()", "The current date and time in UTC."),
    "UTCTODAY": ("UTCTODAY()", "The current date in UTC."),
    "WEEKDAY": (
        "WEEKDAY(<date>[, <return_type>])",
        "The day of the week as a number, 1 to 7 by default starting on Sunday.",
    ),
    "WEEKNUM": ("WEEKNUM(<date>[, <return_type>])", "The week number of the year."),
    "YEAR": ("YEAR(<date>)", "The year of a date."),
    "YEARFRAC": (
        "YEARFRAC(<start_date>, <end_date>[, <basis>])",
        "The fraction of a year between two dates.",
    ),
    # Time intelligence
    "CLOSINGBALANCEMONTH": (
        "CLOSINGBALANCEMONTH(<expression>, <dates>[, <filter>])",
        "An expression evaluated at the last date of the month.",
    ),
    "CLOSINGBALANCEQUARTER": (
        "CLOSINGBALANCEQUARTER(<expression>, <dates>[, <filter>])",
        "An expression evaluated at the last date of the quarter.",
    ),
    "CLOSINGBALANCEYEAR": (
        "CLOSINGBALANCEYEAR(<expression>, <dates>[, <filter>][, <year_end_date>])",
        "An expression evaluated at the last date of the year.",
    ),
    "DATEADD": (
        "DATEADD(<dates>, <number_of_intervals>, <interval>)",
        "The dates shifted forward or back by a number of days, months, quarters or years.",
    ),
    "DATESBETWEEN": (
        "DATESBETWEEN(<dates>, <start_date>, <end_date>)",
        "The dates from a start date to an end date, both included.",
    ),
    "DATESINPERIOD": (
        "DATESINPERIOD(<dates>, <start_date>, <number_of_intervals>, <interval>)",
        "The dates in a period that starts at a date and runs for a number of intervals.",
    ),
    "DATESMTD": ("DATESMTD(<dates>)", "The dates from the start of the month to the current date."),
    "DATESQTD": ("DATESQTD(<dates>)", "The dates from the start of the quarter to the current date."),
    "DATESYTD": (
        "DATESYTD(<dates>[, <year_end_date>])",
        "The dates from the start of the year to the current date.",
    ),
    "ENDOFMONTH": ("ENDOFMONTH(<dates>)", "The last date of the month in the current context."),
    "ENDOFQUARTER": ("ENDOFQUARTER(<dates>)", "The last date of the quarter in the current context."),
    "ENDOFYEAR": (
        "ENDOFYEAR(<dates>[, <year_end_date>])",
        "The last date of the year in the current context.",
    ),
    "FIRSTDATE": ("FIRSTDATE(<dates>)", "The first date in the current context."),
    "FIRSTNONBLANK": (
        "FIRSTNONBLANK(<column>, <expression>)",
        "The first value of a column for which an expression is not blank.",
    ),
    "FIRSTNONBLANKVALUE": (
        "FIRSTNONBLANKVALUE(<column>, <expression>)",
        "The first non-blank value of an expression, in the order of a column.",
    ),
    "LASTDATE": ("LASTDATE(<dates>)", "The last date in the current context."),
    "LASTNONBLANK": (
        "LASTNONBLANK(<column>, <expression>)",
        "The last value of a column for which an expression is not blank.",
    ),
    "LASTNONBLANKVALUE": (
        "LASTNONBLANKVALUE(<column>, <expression>)",
        "The last non-blank value of an expression, in the order of a column.",
    ),
    "NEXTDAY": ("NEXTDAY(<dates>)", "The day after the first date in the current context."),
    "NEXTMONTH": ("NEXTMONTH(<dates>)", "All dates of the month after the current one."),
    "NEXTQUARTER": ("NEXTQUARTER(<dates>)", "All dates of the quarter after the current one."),
    "NEXTYEAR": ("NEXTYEAR(<dates>[, <year_end_date>])", "All dates of the year after the current one."),
    "OPENINGBALANCEMONTH": (
        "OPENINGBALANCEMONTH(<expression>, <dates>[, <filter>])",
        "An expression evaluated at the end of the previous month.",
    ),
    "OPENINGBALANCEQUARTER": (
        "OPENINGBALANCEQUARTER(<expression>, <dates>[, <filter>])",
        "An expression evaluated at the end of the previous quarter.",
    ),
    "OPENINGBALANCEYEAR": (
        "OPENINGBALANCEYEAR(<expression>, <dates>[, <filter>][, <year_end_date>])",
        "An expression evaluated at the end of the previous year.",
    ),
    "PARALLELPERIOD": (
        "PARALLELPERIOD(<dates>, <number_of_intervals>, <interval>)",
        "Whole months, quarters or years shifted from the current dates.",
    ),
    "PREVIOUSDAY": ("PREVIOUSDAY(<dates>)", "The day before the first date in the current context."),
    "PREVIOUSMONTH": ("PREVIOUSMONTH(<dates>)", "All dates of the month before the current one."),
    "PREVIOUSQUARTER": ("PREVIOUSQUARTER(<dates>)", "All dates of the quarter before the current one."),
    "PREVIOUSYEAR": (
        "PREVIOUSYEAR(<dates>[, <year_end_date>])",
        "All dates of the year before the current one.",
    ),
    "SAMEPERIODLASTYEAR": ("SAMEPERIODLASTYEAR(<dates>)", "The current dates shifted back one year."),
    "STARTOFMONTH": ("STARTOFMONTH(<dates>)", "The first date of the month in the current context."),
    "STARTOFQUARTER": ("STARTOFQUARTER(<dates>)", "The first date of the quarter in the current context."),
    "STARTOFYEAR": (
        "STARTOFYEAR(<dates>[, <year_end_date>])",
        "The first date of the year in the current context.",
    ),
    "TOTALMTD": (
        "TOTALMTD(<expression>, <dates>[, <filter>])",
        "An expression evaluated for the month to date.",
    ),
    "TOTALQTD": (
        "TOTALQTD(<expression>, <dates>[, <filter>])",
        "An expression evaluated for the quarter to date.",
    ),
    "TOTALYTD": (
        "TOTALYTD(<expression>, <dates>[, <filter>][, <year_end_date>])",
        "An expression evaluated for the year to date.",
    ),
    # Filter
    "ALL": (
        "ALL([<table> | <column>[, <column>, …]])",
        "A table or columns with every filter removed; inside CALCULATE, removes those filters.",
    ),
    "ALLCROSSFILTERED": (
        "ALLCROSSFILTERED(<table>)",
        "Removes every filter on a table, including filters from cross-filtering.",
    ),
    "ALLEXCEPT": (
        "ALLEXCEPT(<table>, <column>[, <column>, …])",
        "Removes every filter on a table except those on the given columns.",
    ),
    "ALLNOBLANKROW": (
        "ALLNOBLANKROW(<table> | <column>[, <column>, …])",
        "Like ALL, without the blank row a relationship can add.",
    ),
    "ALLSELECTED": (
        "ALLSELECTED([<table> | <column>[, <column>, …]])",
        "Removes filters from inside the visual but keeps those from outside it, such as slicers.",
    ),
    "CALCULATE": (
        "CALCULATE(<expression>[, <filter>, …])",
        "Evaluates an expression in a filter context changed by the given filters.",
    ),
    "CALCULATETABLE": (
        "CALCULATETABLE(<table>[, <filter>, …])",
        "Evaluates a table expression in a filter context changed by the given filters.",
    ),
    "EARLIER": (
        "EARLIER(<column>[, <number>])",
        "The value of a column in an outer row context. Variables are usually clearer.",
    ),
    "EARLIEST": ("EARLIEST(<column>)", "The value of a column in the outermost row context."),
    "FILTER": ("FILTER(<table>, <filter>)", "The rows of a table for which a condition is true."),
    "INDEX": (
        "INDEX(<position>[, <relation>][, <orderBy>][, <blanks>][, <partitionBy>][, <matchBy>])",
        "The row at a position in a sorted, optionally partitioned, table.",
    ),
    "KEEPFILTERS": (
        "KEEPFILTERS(<expression>)",
        "Adds a filter in CALCULATE on top of the existing ones instead of replacing them.",
    ),
    "LOOKUPVALUE": (
        "LOOKUPVALUE(<result_column>, <search_column>, <search_value>[, …][, <alternate_result>])",
        "The value of a column in the row that matches the search conditions.",
    ),
    "MATCHBY": (
        "MATCHBY([<column>[, <column>, …]])",
        "In window functions, the columns that identify the current row.",
    ),
    "OFFSET": (
        "OFFSET(<delta>[, <relation>][, <orderBy>][, <blanks>][, <partitionBy>][, <matchBy>])",
        "The row a number of rows before or after the current one in a sorted table.",
    ),
    "ORDERBY": ("ORDERBY(<expression>[, <order>[, …]])", "In window functions, the order of the rows."),
    "PARTITIONBY": (
        "PARTITIONBY(<column>[, <column>, …])",
        "In window functions, the columns that split the rows into groups.",
    ),
    "REMOVEFILTERS": (
        "REMOVEFILTERS([<table> | <column>[, <column>, …]])",
        "Removes filters from a table or columns inside CALCULATE.",
    ),
    "SELECTEDVALUE": (
        "SELECTEDVALUE(<column>[, <alternate_result>])",
        "The value of a column when only one is filtered, otherwise the alternate result.",
    ),
    "WINDOW": (
        "WINDOW(<from>[, <from_type>], <to>[, <to_type>][, <relation>][, <orderBy>][, <blanks>][, <partitionBy>][, <matchBy>])",
        "A range of rows around the current one in a sorted table.",
    ),
    # Information
    "COLUMNSTATISTICS": ("COLUMNSTATISTICS()", "A table of statistics about every column in the model."),
    "CONTAINS": (
        "CONTAINS(<table>, <column>, <value>[, …])",
        "TRUE when a table has a row with the given values.",
    ),
    "CONTAINSROW": (
        "CONTAINSROW(<table>, <value>[, …])",
        "TRUE when a table has a row equal to the given values (the IN operator).",
    ),
    "CONTAINSSTRING": (
        "CONTAINSSTRING(<within_text>, <find_text>)",
        "TRUE when text contains other text, ignoring case.",
    ),
    "CONTAINSSTRINGEXACT": (
        "CONTAINSSTRINGEXACT(<within_text>, <find_text>)",
        "TRUE when text contains other text, matching case.",
    ),
    "CUSTOMDATA": ("CUSTOMDATA()", "The CustomData property of the connection string."),
    "HASONEFILTER": (
        "HASONEFILTER(<column>)",
        "TRUE when a column is directly filtered to exactly one value.",
    ),
    "HASONEVALUE": (
        "HASONEVALUE(<column>)",
        "TRUE when a column has exactly one value in the current context.",
    ),
    "ISAFTER": (
        "ISAFTER(<value1>, <value2>[, <order>], …)",
        "TRUE when a row comes after another in a given order; used with START AT.",
    ),
    "ISBLANK": ("ISBLANK(<value>)", "TRUE when a value is blank."),
    "ISCROSSFILTERED": (
        "ISCROSSFILTERED(<table> | <column>)",
        "TRUE when a table or column is filtered, directly or through a relationship.",
    ),
    "ISEMPTY": ("ISEMPTY(<table>)", "TRUE when a table has no rows."),
    "ISERROR": ("ISERROR(<value>)", "TRUE when a value is an error."),
    "ISEVEN": ("ISEVEN(<number>)", "TRUE when a number is even."),
    "ISFILTERED": ("ISFILTERED(<table> | <column>)", "TRUE when a table or column is filtered directly."),
    "ISINSCOPE": (
        "ISINSCOPE(<column>)",
        "TRUE when a column is the current level of a hierarchy, as in a matrix row.",
    ),
    "ISLOGICAL": ("ISLOGICAL(<value>)", "TRUE when a value is TRUE or FALSE."),
    "ISNONTEXT": ("ISNONTEXT(<value>)", "TRUE when a value is not text."),
    "ISNUMBER": ("ISNUMBER(<value>)", "TRUE when a value is a number."),
    "ISODD": ("ISODD(<number>)", "TRUE when a number is odd."),
    "ISONORAFTER": (
        "ISONORAFTER(<value1>, <value2>[, <order>], …)",
        "TRUE when a row comes on or after another in a given order.",
    ),
    "ISSELECTEDMEASURE": (
        "ISSELECTEDMEASURE(<measure>[, <measure>, …])",
        "In a calculation item, TRUE when the measure it is applied to is one of those listed.",
    ),
    "ISSUBTOTAL": ("ISSUBTOTAL(<column>)", "In SUMMARIZE, TRUE on the subtotal rows of a column."),
    "ISTEXT": ("ISTEXT(<value>)", "TRUE when a value is text."),
    "NONVISUAL": (
        "NONVISUAL(<expression>)",
        "Marks a filter in SUMMARIZECOLUMNS as one that does not change the measure values.",
    ),
    "SELECTEDMEASURE": ("SELECTEDMEASURE()", "In a calculation item, the measure it is applied to."),
    "SELECTEDMEASUREFORMATSTRING": (
        "SELECTEDMEASUREFORMATSTRING()",
        "In a calculation item, the format string of the measure it is applied to.",
    ),
    "SELECTEDMEASURENAME": (
        "SELECTEDMEASURENAME()",
        "In a calculation item, the name of the measure it is applied to.",
    ),
    "USERCULTURE": ("USERCULTURE()", "The locale of the current user, such as en-US."),
    "USERNAME": ("USERNAME()", "The domain and user name of the current user."),
    "USEROBJECTID": ("USEROBJECTID()", "The object ID of the current user in Microsoft Entra ID."),
    "USERPRINCIPALNAME": (
        "USERPRINCIPALNAME()",
        "The user principal name (usually the email address) of the current user.",
    ),
    # Logical
    "AND": (
        "AND(<logical1>, <logical2>)",
        "TRUE when both values are TRUE. The && operator takes more than two.",
    ),
    "BITAND": ("BITAND(<number>, <number>)", "Bitwise AND of two numbers."),
    "BITLSHIFT": ("BITLSHIFT(<number>, <shift_amount>)", "A number with its bits shifted left."),
    "BITOR": ("BITOR(<number>, <number>)", "Bitwise OR of two numbers."),
    "BITRSHIFT": ("BITRSHIFT(<number>, <shift_amount>)", "A number with its bits shifted right."),
    "BITXOR": ("BITXOR(<number>, <number>)", "Bitwise exclusive OR of two numbers."),
    "COALESCE": ("COALESCE(<expression>, <expression>[, …])", "The first value that is not blank."),
    "FALSE": ("FALSE()", "The logical value FALSE."),
    "IF": (
        "IF(<logical_test>, <value_if_true>[, <value_if_false>])",
        "One value when a condition is TRUE, another when it is FALSE.",
    ),
    "IF.EAGER": (
        "IF.EAGER(<logical_test>, <value_if_true>[, <value_if_false>])",
        "Like IF, but evaluates both branches first; sometimes faster.",
    ),
    "IFERROR": ("IFERROR(<value>, <value_if_error>)", "A value, or an alternative when it is an error."),
    "NOT": ("NOT(<logical>)", "TRUE becomes FALSE and FALSE becomes TRUE."),
    "OR": (
        "OR(<logical1>, <logical2>)",
        "TRUE when either value is TRUE. The || operator takes more than two.",
    ),
    "SWITCH": (
        "SWITCH(<expression>, <value>, <result>[, <value>, <result>]…[, <else>])",
        "The result for the first value that matches the expression. SWITCH(TRUE(), …) tests conditions in turn.",
    ),
    "TRUE": ("TRUE()", "The logical value TRUE."),
    # Math and trig
    "ABS": ("ABS(<number>)", "The absolute value of a number."),
    "ACOS": ("ACOS(<number>)", "The arccosine of a number, in radians."),
    "ASIN": ("ASIN(<number>)", "The arcsine of a number, in radians."),
    "ATAN": ("ATAN(<number>)", "The arctangent of a number, in radians."),
    "CEILING": (
        "CEILING(<number>, <significance>)",
        "A number rounded up to the nearest multiple of significance.",
    ),
    "CONVERT": ("CONVERT(<expression>, <datatype>)", "Converts a value to another data type."),
    "COS": ("COS(<number>)", "The cosine of an angle in radians."),
    "CURRENCY": ("CURRENCY(<value>)", "Converts a value to the currency (fixed decimal) type."),
    "DEGREES": ("DEGREES(<angle>)", "Converts radians to degrees."),
    "DIVIDE": (
        "DIVIDE(<numerator>, <denominator>[, <alternate_result>])",
        "Divides, returning blank or the alternate result instead of an error when dividing by zero.",
    ),
    "EVEN": ("EVEN(<number>)", "A number rounded up to the nearest even integer."),
    "EXP": ("EXP(<number>)", "e raised to the power of a number."),
    "FACT": ("FACT(<number>)", "The factorial of a number."),
    "FLOOR": (
        "FLOOR(<number>, <significance>)",
        "A number rounded down to the nearest multiple of significance.",
    ),
    "GCD": ("GCD(<number1>[, <number2>, …])", "The greatest common divisor."),
    "INT": ("INT(<number>)", "A number rounded down to the nearest integer."),
    "ISO.CEILING": (
        "ISO.CEILING(<number>[, <significance>])",
        "A number rounded up to the nearest multiple of significance.",
    ),
    "LCM": ("LCM(<number1>[, <number2>, …])", "The least common multiple."),
    "LN": ("LN(<number>)", "The natural logarithm of a number."),
    "LOG": ("LOG(<number>[, <base>])", "The logarithm of a number to a base, 10 by default."),
    "LOG10": ("LOG10(<number>)", "The base-10 logarithm of a number."),
    "MOD": ("MOD(<number>, <divisor>)", "The remainder after division."),
    "MROUND": ("MROUND(<number>, <multiple>)", "A number rounded to the nearest multiple."),
    "ODD": ("ODD(<number>)", "A number rounded up to the nearest odd integer."),
    "PI": ("PI()", "The number pi, 3.14159265358979."),
    "POWER": ("POWER(<number>, <power>)", "A number raised to a power."),
    "QUOTIENT": ("QUOTIENT(<numerator>, <denominator>)", "The integer part of a division."),
    "RADIANS": ("RADIANS(<number>)", "Converts degrees to radians."),
    "RAND": ("RAND()", "A random number from 0 up to 1."),
    "RANDBETWEEN": ("RANDBETWEEN(<bottom>, <top>)", "A random whole number between two numbers."),
    "ROUND": ("ROUND(<number>, <num_digits>)", "A number rounded to a number of digits."),
    "ROUNDDOWN": ("ROUNDDOWN(<number>, <num_digits>)", "A number rounded down, toward zero."),
    "ROUNDUP": ("ROUNDUP(<number>, <num_digits>)", "A number rounded up, away from zero."),
    "SIGN": ("SIGN(<number>)", "1 for a positive number, 0 for zero and -1 for a negative number."),
    "SIN": ("SIN(<number>)", "The sine of an angle in radians."),
    "SQRT": ("SQRT(<number>)", "The square root of a number."),
    "SQRTPI": ("SQRTPI(<number>)", "The square root of a number times pi."),
    "TAN": ("TAN(<number>)", "The tangent of an angle in radians."),
    "TRUNC": ("TRUNC(<number>[, <num_digits>])", "A number with its fractional part cut off."),
    # Statistical
    "BETA.DIST": ("BETA.DIST(<x>, <alpha>, <beta>, <cumulative>[, <A>][, <B>])", "The beta distribution."),
    "CHISQ.DIST": ("CHISQ.DIST(<x>, <deg_freedom>, <cumulative>)", "The chi-squared distribution."),
    "CONFIDENCE.NORM": (
        "CONFIDENCE.NORM(<alpha>, <standard_dev>, <size>)",
        "The confidence interval for a population mean, using a normal distribution.",
    ),
    "CONFIDENCE.T": (
        "CONFIDENCE.T(<alpha>, <standard_dev>, <size>)",
        "The confidence interval for a population mean, using a Student's t distribution.",
    ),
    "EXPON.DIST": ("EXPON.DIST(<x>, <lambda>, <cumulative>)", "The exponential distribution."),
    "GEOMEAN": ("GEOMEAN(<column>)", "The geometric mean of the numbers in a column."),
    "GEOMEANX": (
        "GEOMEANX(<table>, <expression>)",
        "The geometric mean of an expression evaluated for each row of a table.",
    ),
    "LINEST": (
        "LINEST(<columnY>, <columnX>[, …][, <const>])",
        "A table describing the least-squares line through the data.",
    ),
    "LINESTX": (
        "LINESTX(<table>, <expressionY>, <expressionX>[, …][, <const>])",
        "Like LINEST, from expressions evaluated for each row of a table.",
    ),
    "MEDIAN": ("MEDIAN(<column>)", "The median of the numbers in a column."),
    "MEDIANX": (
        "MEDIANX(<table>, <expression>)",
        "The median of an expression evaluated for each row of a table.",
    ),
    "NORM.DIST": ("NORM.DIST(<x>, <mean>, <standard_dev>, <cumulative>)", "The normal distribution."),
    "NORM.INV": (
        "NORM.INV(<probability>, <mean>, <standard_dev>)",
        "The inverse of the normal cumulative distribution.",
    ),
    "NORM.S.DIST": ("NORM.S.DIST(<z>, <cumulative>)", "The standard normal distribution."),
    "PERCENTILE.EXC": (
        "PERCENTILE.EXC(<column>, <k>)",
        "The k-th percentile of a column, k between 0 and 1 exclusive.",
    ),
    "PERCENTILE.INC": (
        "PERCENTILE.INC(<column>, <k>)",
        "The k-th percentile of a column, k between 0 and 1 inclusive.",
    ),
    "PERCENTILEX.EXC": (
        "PERCENTILEX.EXC(<table>, <expression>, <k>)",
        "The k-th percentile of an expression over a table, exclusive.",
    ),
    "PERCENTILEX.INC": (
        "PERCENTILEX.INC(<table>, <expression>, <k>)",
        "The k-th percentile of an expression over a table, inclusive.",
    ),
    "POISSON.DIST": ("POISSON.DIST(<x>, <mean>, <cumulative>)", "The Poisson distribution."),
    "RANK": (
        "RANK([<ties>][, <relation>][, <orderBy>][, <blanks>][, <partitionBy>][, <matchBy>])",
        "The rank of the current row in a sorted, optionally partitioned, table.",
    ),
    "RANK.EQ": ("RANK.EQ(<value>, <column>[, <order>])", "The rank of a number in a column of numbers."),
    "RANKX": (
        "RANKX(<table>, <expression>[, <value>][, <order>][, <ties>])",
        "The rank of the current value of an expression among its values over a table.",
    ),
    "ROWNUMBER": (
        "ROWNUMBER([<relation>][, <orderBy>][, <blanks>][, <partitionBy>][, <matchBy>])",
        "The position of the current row in a sorted, optionally partitioned, table, with no ties.",
    ),
    "SAMPLE": ("SAMPLE(<n_value>, <table>, <orderBy>[, <order>[, …]])", "A sample of n rows from a table."),
    "STDEV.P": ("STDEV.P(<column>)", "The standard deviation of a whole population."),
    "STDEV.S": ("STDEV.S(<column>)", "The standard deviation of a sample."),
    "STDEVX.P": (
        "STDEVX.P(<table>, <expression>)",
        "The population standard deviation of an expression over a table.",
    ),
    "STDEVX.S": (
        "STDEVX.S(<table>, <expression>)",
        "The sample standard deviation of an expression over a table.",
    ),
    "T.DIST": ("T.DIST(<x>, <deg_freedom>, <cumulative>)", "The Student's left-tailed t distribution."),
    "T.INV": (
        "T.INV(<probability>, <deg_freedom>)",
        "The left-tailed inverse of the Student's t distribution.",
    ),
    "VAR.P": ("VAR.P(<column>)", "The variance of a whole population."),
    "VAR.S": ("VAR.S(<column>)", "The variance of a sample."),
    "VARX.P": ("VARX.P(<table>, <expression>)", "The population variance of an expression over a table."),
    "VARX.S": ("VARX.S(<table>, <expression>)", "The sample variance of an expression over a table."),
    # Table manipulation
    "ADDCOLUMNS": (
        "ADDCOLUMNS(<table>, <name>, <expression>[, <name>, <expression>]…)",
        "A table with calculated columns added.",
    ),
    "ADDMISSINGITEMS": (
        "ADDMISSINGITEMS([<showAll_column>, …], <table>[, <groupBy_column>, …][, <filterTable>]…)",
        "Adds rows with empty values that SUMMARIZECOLUMNS left out.",
    ),
    "CROSSJOIN": ("CROSSJOIN(<table>, <table>[, <table>]…)", "Every combination of the rows of the tables."),
    "CURRENTGROUP": ("CURRENTGROUP()", "In GROUPBY, the rows of the current group."),
    "DATATABLE": (
        "DATATABLE(<name>, <type>[, <name>, <type>]…, <data>)",
        "A table typed out in the expression.",
    ),
    "DETAILROWS": ("DETAILROWS(<measure>)", "The rows of the measure's detail rows expression."),
    "DISTINCT": (
        "DISTINCT(<column> | <table>)",
        "The distinct values of a column, or the distinct rows of a table.",
    ),
    "EXCEPT": ("EXCEPT(<table1>, <table2>)", "The rows of the first table that are not in the second."),
    "FILTERS": ("FILTERS(<column>)", "The values that directly filter a column."),
    "GENERATE": (
        "GENERATE(<table1>, <table2>)",
        "Each row of the first table joined to the rows the second table gives for it.",
    ),
    "GENERATEALL": (
        "GENERATEALL(<table1>, <table2>)",
        "Like GENERATE, keeping rows of the first table that give no rows.",
    ),
    "GENERATESERIES": (
        "GENERATESERIES(<start>, <end>[, <increment>])",
        "A one-column table of values from start to end.",
    ),
    "GROUPBY": (
        "GROUPBY(<table>[, <groupBy_column>, …][, <name>, <expression>]…)",
        "A table grouped by columns, with aggregations over CURRENTGROUP().",
    ),
    "IGNORE": (
        "IGNORE(<expression>)",
        "In SUMMARIZECOLUMNS, leaves an expression out of the check for blank rows.",
    ),
    "INTERSECT": ("INTERSECT(<table1>, <table2>)", "The rows that are in both tables."),
    "NATURALINNERJOIN": (
        "NATURALINNERJOIN(<left_table>, <right_table>)",
        "An inner join of two tables on their common columns.",
    ),
    "NATURALLEFTOUTERJOIN": (
        "NATURALLEFTOUTERJOIN(<left_table>, <right_table>)",
        "A left outer join of two tables on their common columns.",
    ),
    "ROLLUP": ("ROLLUP(<groupBy_column>[, <groupBy_column>, …])", "In SUMMARIZE, adds subtotal rows."),
    "ROLLUPADDISSUBTOTAL": (
        "ROLLUPADDISSUBTOTAL(<groupBy_column>, <name>[, …])",
        "In SUMMARIZECOLUMNS, adds subtotal rows and a column that marks them.",
    ),
    "ROLLUPGROUP": (
        "ROLLUPGROUP(<groupBy_column>[, <groupBy_column>, …])",
        "Groups columns so ROLLUP gives one subtotal for them together.",
    ),
    "ROLLUPISSUBTOTAL": (
        "ROLLUPISSUBTOTAL(<grandtotalFilter>, <groupBy_column>, <isSubtotal_column>[, …])",
        "Pairs ROLLUPADDISSUBTOTAL groups with their subtotal columns.",
    ),
    "ROW": ("ROW(<name>, <expression>[, <name>, <expression>]…)", "A table with one row."),
    "SELECTCOLUMNS": (
        "SELECTCOLUMNS(<table>[, <name>], <expression>[, …])",
        "A table with only the given columns or expressions.",
    ),
    "SUBSTITUTEWITHINDEX": (
        "SUBSTITUTEWITHINDEX(<table>, <name>, <semiJoinTable>, <expression>, <order>)",
        "A table with the columns it shares with another replaced by an index.",
    ),
    "SUMMARIZE": (
        "SUMMARIZE(<table>, <groupBy_column>[, <groupBy_column>]…[, <name>, <expression>]…)",
        "A table grouped by columns. Add calculated columns with ADDCOLUMNS rather than here.",
    ),
    "SUMMARIZECOLUMNS": (
        "SUMMARIZECOLUMNS(<groupBy_column>[, …][, <filterTable>]…[, <name>, <expression>]…)",
        "A table grouped by columns with measures added; what Power BI visuals ask for.",
    ),
    "TOPN": (
        "TOPN(<n_value>, <table>, <orderBy_expression>[, <order>[, …]])",
        "The top n rows of a table by an expression.",
    ),
    "TREATAS": (
        "TREATAS(<table_expression>, <column>[, <column>, …])",
        "Applies the values of a table as filters on unrelated columns.",
    ),
    "UNION": ("UNION(<table>, <table>[, <table>]…)", "The rows of the tables stacked."),
    "VALUES": (
        "VALUES(<table> | <column>)",
        "The distinct values of a column (with blank for missing related rows), or the rows of a table.",
    ),
    # Text
    "COMBINEVALUES": (
        "COMBINEVALUES(<delimiter>, <expression>, <expression>[, …])",
        "Joins text values with a delimiter; optimised for keys in DirectQuery.",
    ),
    "CONCATENATE": (
        "CONCATENATE(<text1>, <text2>)",
        "Joins two text values. The & operator joins any number.",
    ),
    "CONCATENATEX": (
        "CONCATENATEX(<table>, <expression>[, <delimiter>[, <orderBy_expression>[, <order>]]…])",
        "Joins an expression evaluated for each row of a table into one text.",
    ),
    "EXACT": ("EXACT(<text1>, <text2>)", "TRUE when two text values are the same, matching case."),
    "FIND": (
        "FIND(<find_text>, <within_text>[, <start_num>][, <NotFoundValue>])",
        "The position of text within other text, matching case.",
    ),
    "FIXED": ("FIXED(<number>[, <decimals>][, <no_commas>])", "A number rounded and written as text."),
    "FORMAT": (
        "FORMAT(<value>, <format_string>[, <locale_name>])",
        'A value written as text in a format such as "#,0.00" or "yyyy-mm".',
    ),
    "LEFT": ("LEFT(<text>[, <num_chars>])", "The first characters of text."),
    "LEN": ("LEN(<text>)", "The number of characters in text."),
    "LOWER": ("LOWER(<text>)", "Text in lower case."),
    "MID": ("MID(<text>, <start_num>, <num_chars>)", "Characters from the middle of text."),
    "REPLACE": (
        "REPLACE(<old_text>, <start_num>, <num_chars>, <new_text>)",
        "Replaces characters at a position in text.",
    ),
    "REPT": ("REPT(<text>, <num_times>)", "Text repeated a number of times."),
    "RIGHT": ("RIGHT(<text>[, <num_chars>])", "The last characters of text."),
    "SEARCH": (
        "SEARCH(<find_text>, <within_text>[, <start_num>][, <NotFoundValue>])",
        "The position of text within other text, ignoring case.",
    ),
    "SUBSTITUTE": (
        "SUBSTITUTE(<text>, <old_text>, <new_text>[, <instance_num>])",
        "Replaces existing text with new text.",
    ),
    "TRIM": ("TRIM(<text>)", "Text without leading, trailing and repeated spaces."),
    "UNICHAR": ("UNICHAR(<number>)", "The Unicode character for a number."),
    "UNICODE": ("UNICODE(<text>)", "The number of the first character of text."),
    "UPPER": ("UPPER(<text>)", "Text in upper case."),
    "VALUE": ("VALUE(<text>)", "Converts text that holds a number to a number."),
    # Parent and child
    "PATH": (
        "PATH(<id_column>, <parent_column>)",
        "The full chain of parent IDs for the current row, as delimited text.",
    ),
    "PATHCONTAINS": ("PATHCONTAINS(<path>, <item>)", "TRUE when a path contains an item."),
    "PATHITEM": ("PATHITEM(<path>, <position>[, <type>])", "The item at a position in a path."),
    "PATHITEMREVERSE": (
        "PATHITEMREVERSE(<path>, <position>[, <type>])",
        "The item at a position in a path, counting from the end.",
    ),
    "PATHLENGTH": ("PATHLENGTH(<path>)", "The number of items in a path."),
    # Relationship
    "CROSSFILTER": (
        "CROSSFILTER(<column1>, <column2>, <direction>)",
        "In CALCULATE, sets the filter direction of a relationship (or turns it off).",
    ),
    "RELATED": (
        "RELATED(<column>)",
        "The value of a column in the related row on the one side of a relationship.",
    ),
    "RELATEDTABLE": ("RELATEDTABLE(<table>)", "The related rows on the many side of a relationship."),
    "USERELATIONSHIP": (
        "USERELATIONSHIP(<column1>, <column2>)",
        "In CALCULATE, uses an inactive relationship instead of the active one.",
    ),
    # Other
    "BLANK": ("BLANK()", "A blank value."),
    "ERROR": ("ERROR(<text>)", "Raises an error with a message."),
    "EVALUATEANDLOG": (
        "EVALUATEANDLOG(<value>[, <label>][, <max_rows>])",
        "Returns a value and logs it for DAX debugging tools.",
    ),
    "NAMEOF": ("NAMEOF(<value>)", "The name of a column or measure as text; field parameters use it."),
    "TOCSV": (
        "TOCSV(<table>[, <max_rows>][, <delimiter>][, <include_headers>])",
        "A table written as CSV text.",
    ),
    "TOJSON": ("TOJSON(<table>[, <max_rows>])", "A table written as JSON text."),
    # Visual calculations
    "COLLAPSE": (
        "COLLAPSE([<expression>][, <axis>][, <n>])",
        "In a visual calculation, evaluates at a higher level of the axis.",
    ),
    "COLLAPSEALL": (
        "COLLAPSEALL(<expression>, <axis>)",
        "In a visual calculation, evaluates at the total level of the axis.",
    ),
    "EXPAND": (
        "EXPAND([<expression>][, <axis>][, <n>])",
        "In a visual calculation, evaluates at a lower level of the axis.",
    ),
    "EXPANDALL": (
        "EXPANDALL(<expression>, <axis>)",
        "In a visual calculation, evaluates at the lowest level of the axis.",
    ),
    "FIRST": (
        "FIRST(<column>[, <axis>][, <blanks>][, <reset>])",
        "In a visual calculation, the value in the first row of the axis.",
    ),
    "ISATLEVEL": (
        "ISATLEVEL(<column>)",
        "In a visual calculation, TRUE when a column is present at the current level.",
    ),
    "LAST": (
        "LAST(<column>[, <axis>][, <blanks>][, <reset>])",
        "In a visual calculation, the value in the last row of the axis.",
    ),
    "LOOKUP": (
        "LOOKUP(<expression>, <column>, <value>[, …])",
        "In a visual calculation, an expression evaluated at the row that matches the filters.",
    ),
    "LOOKUPWITHTOTALS": (
        "LOOKUPWITHTOTALS(<expression>, <column>, <value>[, …])",
        "Like LOOKUP, keeping totals for columns that are not filtered.",
    ),
    "MOVINGAVERAGE": (
        "MOVINGAVERAGE(<column>, <windowSize>[, <includeCurrent>][, <axis>][, <blanks>][, <reset>])",
        "In a visual calculation, the moving average over a window of rows.",
    ),
    "NEXT": (
        "NEXT(<column>[, <steps>][, <axis>][, <blanks>][, <reset>])",
        "In a visual calculation, the value in a later row of the axis.",
    ),
    "PREVIOUS": (
        "PREVIOUS(<column>[, <steps>][, <axis>][, <blanks>][, <reset>])",
        "In a visual calculation, the value in an earlier row of the axis.",
    ),
    "RANGE": (
        "RANGE(<step>[, <includeCurrent>][, <axis>][, <blanks>][, <reset>])",
        "In a visual calculation, an interval of rows around the current one.",
    ),
    "RUNNINGSUM": (
        "RUNNINGSUM(<column>[, <axis>][, <blanks>][, <reset>])",
        "In a visual calculation, the running total along the axis.",
    ),
}


def dax_learn_url(name: str) -> str:
    """The function's page on Microsoft Learn."""
    return "https://learn.microsoft.com/dax/" + name.lower().replace(".", "-") + "-function-dax"
