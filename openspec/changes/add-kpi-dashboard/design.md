## Context

C4 container **KPI Dashboard** (slide "Daoardshb"). Placement: **common core** view over the evaluation interface. Position: **owned**.

## Goals / Non-Goals

**Goals:** read-only view; no computation; works offline; safe to keep on team storage.

**Non-Goals:** interactive editing; live hosting (the Web UI KPI View does that from the same panel definitions).

## Decisions

- **Static HTML** with inline Vega-Lite specs and embedded data; no external network requests (confidentiality). Alternative: Streamlit. Rejected: needs a server and invites ad-hoc computation.
- **Render only from snapshots;** each panel shows snapshot ids and versions in a footer.
- **No note text** except optional top error examples drawn from DEV, toggled by a flag and never from TEST.
- **Version banner** whenever compared snapshots differ in metric definitions, taxonomy, evaluation set or weights version.

## Risks / Trade-offs

- [Readers over-read point estimates] → intervals drawn on every rate; inconclusive gates in a distinct style.

## Open Questions

- Does the client want a PDF export for D5? (Print stylesheet included.)
