## Context

C4 container **KPI Dashboard** (slide "Daoardshb"). Placement: **common core** view over the evaluation interface. Position: **owned**.

## Goals / Non-Goals

**Goals:** read-only view; no computation; works offline; safe to keep on team storage.

**Non-Goals:** interactive editing; live hosting (the Web UI KPI View does that from the same panel definitions).

## Decisions

- **Static HTML** with inline Vega-Lite specs and embedded data; no external network requests. The templates are shared with the Web UI KPI View (ADR 0011). Alternative: serve reports only from the Web UI. Rejected: D5 and offline reading need a file.
- **Render only from snapshots;** each panel shows snapshot ids and versions in a footer.
- **No note text** except optional top error examples drawn from TRAIN, toggled by a flag and never from TEST.
- **Version banner** whenever compared snapshots differ in metric definitions, taxonomy, evaluation set or weights version.

## Risks / Trade-offs

- [Readers over-read point estimates] → intervals drawn on every rate, including beside each gate's pass or fail.

## Open Questions

- Does the client want a PDF export for D5? (Print stylesheet included.)
