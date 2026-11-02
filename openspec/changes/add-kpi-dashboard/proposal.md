## Why

The client owner and the team need to see, per run and over time, whether the levels are met, which errors dominate, what the run cost and whether the review loop keeps up, without opening DuckDB. The Web UI KPI View (ADR 0007) covers live reading; a static file built only from KPI snapshots is still needed for D5, offline reading and archiving. Both must show the same panels.

## What Changes

- Generate a self-contained HTML report per run and a cumulative trend report.
- Panels: level gates with intervals, coverage, error breakdown a–g, success a–e, cost, calibration curve and AUC, approval and audit disagreement, loop health, run comparison, open cases.
- Shared panel definitions (`itemizer.kpi.panels`) used by both this report and the Web UI KPI View.
- Version banners when snapshots use different definitions, taxonomy or weights versions.

## Capabilities

### New Capabilities
- `kpi-dashboard`: static HTML rendering of KPI snapshots with version-aware comparisons.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.dashboard` (Jinja2, Vega-Lite inline). Output under `${runtime.data_root}/reports`.
- Depends on KPI Calculator snapshots only.
