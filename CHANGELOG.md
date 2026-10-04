# Changelog

All notable changes to Trails for Power BI.

## 1.0.0 - 2026-10-04

First public release.

- One offline HTML page per Power BI project (PBIP), with five views:
  - **Lineage**: column- and measure-level lineage from data sources through tables, columns and
    measures to visuals and pages. Upstream draws in navy, downstream in teal; compact and
    detailed cards; fit to screen
  - **Model**: every table, column, measure and relationship with DAX and Power Query, and a
    relationship diagram with automatic layout. Export as PNG or SVG, with names hidden if you like
  - **Reports**: each page drawn as a canvas preview, with filters at page, report and visual
    level, and the fields every visual uses by role. Show in lineage and Show in Model from any field
  - **Health**: Microsoft's Best Practice Analyzer rules evaluated from the model files, plus
    lineage checks such as unused columns and measures and report fields missing from the model
  - **AI Readiness**: how well Copilot and data agents will understand the model, as a score
    with the findings behind it
- Reads TMDL and model.bim models, PBIR and legacy report.json reports, and reports
  live-connected to a published semantic model
- `trailsbi` with no argument builds the project in the current folder; `-o` takes a file or a
  folder; `--open` opens the page when it is ready
- The page is saved as "TrailsBI Report - <project> - <date time>.html"
- The same project gives the same page on every run
- Python 3.9 or later, no dependencies. `pip install trailsbi`, or the single-file
  `trailsbi.pyz` from the release page
- Runs entirely on your machine: reads metadata files only, makes no network calls, sends no
  telemetry and never writes to your project
