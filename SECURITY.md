# Security

Trails for Power BI is built so that it can be approved without a security review of a
vendor: it is a small, readable Python package with no dependencies beyond the standard
library. It runs locally and touches nothing it does not need.

## What it reads

- Semantic model metadata: TMDL folders, `model.bim`, `definition.pbism`,
  `modelReference.json`
- Report metadata: PBIR folders, legacy `report.json`, `definition.pbir`
- Power Query (M) expressions and DAX formulas, as text

## What it never touches

- `cache.abf` or any other file holding imported data — row-level data is never read
- The Power BI Service, XMLA endpoints or any tenant API
- Credentials, gateways or connection secrets

## What it does not do

- No network calls of any kind, and no telemetry
- No installation, registry changes or admin rights
- No writes to your project folders — the only file it creates is the HTML page,
  at the path you choose

## The output

One self-contained HTML file. It loads no external scripts, fonts or images, and its
Content-Security-Policy blocks network access from the page itself.

## Verifying a download

Each release lists SHA-256 checksums for `trailsbi.pyz` and the wheel. On Windows:

```
certutil -hashfile trailsbi.pyz SHA256
```

On macOS or Linux:

```
shasum -a 256 trailsbi.pyz
```

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting on this repository (Security tab →
Report a vulnerability) rather than a public issue.
