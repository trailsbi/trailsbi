# Contributing

Thanks for helping. Bug reports with a small PBIP project that shows the problem are the
most useful thing you can send: please remove anything confidential first (table names
can be renamed, and the `.pbi/` folders and `cache.abf` should never be shared).

## How the code is laid out

TrailsBI uses the Python standard library only, so it can run on locked-down machines.

```
src/trailsbi/
  cli.py            command line: parses arguments and runs the steps below
  project.py        finds the report and semantic model that make up the project
  tmdl.py           TMDL parser
  model.py          loads a semantic model (TMDL or model.bim); outline and diagram data
  powerquery.py     Power Query (M): steps, data sources, query references
  dax.py            DAX: which tables, columns and measures an expression uses
  report.py         loads a report (PBIR or legacy report.json): pages, visuals, fields
  graph.py          builds the lineage graph from source to page
  bpa.py            Best Practice Analyzer rules
  ai_readiness.py   AI readiness rules
  health.py         the Health view: rule results plus lineage checks
  render.py         assembles the HTML page
  brand.py          product name, version and logo
  icons.py          inline SVG icons
  utils.py          warnings, file reading and small value helpers
  web/
    page.html       page skeleton
    styles.css      page styles
    js/*.js         page script, concatenated in name order into one <script>
```

The page must stay self-contained: no network requests, no external scripts, fonts or
images. Its Content-Security-Policy enforces this.

Some functions are long because they follow the file formats closely: `graph.build_graph`
and `_build_model_part`, `bpa.bpa_evaluate` and the diagram layout in `web/js/10-diagram.js`.
Splitting them is welcome when it makes them easier to follow, with the tests passing before
and after.

## Checks

```
python -m pytest
ruff check .
ruff format --check .
```

To check the page in a browser, build a fixture and run the smoke test (needs Node.js and
Playwright):

```
trailsbi tests/fixtures/Shop -o shop.html
npm install --no-save playwright && npx playwright install chromium
node tools/smoke_page.js shop.html
```

Tests build the synthetic projects in `tests/fixtures/`. Add a fixture when you fix a
parsing problem, so it stays fixed. Never add a real customer project.

## Building the single-file download

```
python tools/build_pyz.py
```

writes `dist/trailsbi.pyz`, which runs with `python trailsbi.pyz PROJECT`.
