# Changelog

All notable changes to Trails for Power BI.
## 1.5.2 - 2026-11-12

- updated detail panel for workspace view

## 1.5.1 - 2026-11-12

- **Multiple workspaces** Give TrailsBI more than one workspaces folders, and it builds one report covering everything from all workspaces.
- Cards, the details pane and `--list` show each item's workspace. 
- **Scope** groups models and reports by workspace, with an option to pick a whole workspace.
- `-w/--workspace NAME` builds the reports and models of one workspace.

## 1.5.0 - 2026-11-12

- **Workspace lineage.** Point TrailsBI at a folder with several reports and semantic models, such as the Git folder a Power BI or Fabric workspace syncs to, and it builds one report for all of them.
- **Scope** in the toolbar picks the semantic models and reports that the lineage, the model, the report pages and the findings show.
- Build part of a folder with `--model`, `--report`, `--with-reports` or `--include`; names may be display names or paths and may use wildcards. `--list` shows what the folder holds.

## 1.4.0 - 2026-11-09

- **Graph view.** Lineage has a new **Map | Graph** switch. Graph shows the same items and links as a circular graph.
  - Uses the map's type filters, view options, search and selection, and the details pane; an item selected in one view stays selected in the other.
- **Report measures.** A report connected live to a semantic model can add measures of its own. TrailsBI now shows them in the lineage as **report measures**, apart from the model's measures.


## 1.3.0 - 2026-11-07

- **Function help in code.** Point at a DAX or Power Query function in any code block to see its syntax and what it does, with a link to its page on Microsoft Learn. 
- **Dark theme.** The page follows the system's light or dark setting. The new button in the header switches between them, and the page remembers your choice.


## 1.2.2 - 2026-11-04

- `--embed` writes the TrailsBI table with just one column, **Chunk**. A TrailsBI table or page from an earlier `--embed` is switched over when you run it again.
- `--embed` adds the TrailsBI visual 1.0.1: one field, Power BI's right-click menu, and a copy button on code.
- The HTML report: every DAX and M code block has a copy button at its top right when the pointer is over it.

## 1.2.1 - 2026-10-25

- `--embed` adds the TrailsBI visual 1.0.0

## 1.2.0 - 2026-10-24

- `--embed` now also adds a **TrailsBI** page to the report, hidden in view mode, with the
  TrailsBI visual on it and its fields already set. The visual (0.9.2) ships with trailsbi and is
  saved inside the report the way Power BI Desktop saves a visual imported from a file, so there
  is nothing to import or drag. Running it again keeps the page as you left it and updates the
  visual. PBIR reports only: for an older report, `--embed` writes the table and says why it
  left the page out.

## 1.1.2 - 2026-10-23

- Recognises the TrailsBI visual's new, shorter ID (from visual 0.9.1) as well as the old one, and leaves both out of the analysis. Without it, the visual's Part and Chunk fields show in Health as fields missing from the model.

## 1.1.1 - 2026-10-23

- `--embed`: the TrailsBI visual could fail with "Cannot read properties of undefined (reading
  'push')" on larger models. Power BI trims trailing spaces when it loads text, and a part that
  ended with a space inside a name lost it. Parts now never start or end with whitespace. Run
  `--embed` again and refresh.

## 1.1.0 - 2026-10-22

- `--embed` writes the page data into the project's semantic model as a hidden `TrailsBI` table
  (TMDL or model.bim), for the [TrailsBI visual](https://github.com/trailsbi/trailsbi-visual)
  to show the report inside Power BI. Running it again replaces the table. Without `-o` or
  `--open`, no HTML page is written.
- The `TrailsBI` table and the TrailsBI visual are left out of the analysis.

## 1.0.1 - 2026-10-06

- Install with uv as well as pip: `uv tool install trailsbi`
- Help for Windows when pip installs the `trailsbi` command outside PATH (Microsoft Store or install
  manager Python): add the Scripts folder to your user PATH once.
  Guide at https://trailsbi.com/setup/

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
