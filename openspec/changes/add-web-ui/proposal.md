## Why

The team has reversed the "no user interface" decision (ADR 0007 supersedes ADR 0002) and wants plain HTML rather than Streamlit (ADR 0011). Accountants and operators need to upload the export, start a run, explore results with each item's evidence highlighted in the note, review errors by type, and review, adjudicate and label rows without Excel round-trips, all from the browser. The approved scope excludes a UI, so this change needs the client owner's written agreement.

## What Changes

- Add a **Web UI** container (server-rendered HTML from a thin FastAPI server, username and password login) with role-based pages: Upload & Pre-check, Run Launcher & Monitor, Results Explorer, Agent Trace Viewer, Tool Reference, Error Review Workbench, Review Queue, Adjudication, Blind Labelling, KPI View.
- The UI holds **no business logic**: runs go through `itemizer run` as background jobs; decisions go through the Human Review System's single intake path; KPIs and error rows are read from snapshots.
- Server-side role enforcement, CSRF protection and a UI audit log.
- Protections from the architecture are kept: blind labelling (no predictions), blind audit rows, aggregate-only VALIDATION results, aggregate-only TEST results until the final freeze.
- Synthetic demo uploads are labelled and kept apart from runs on the real dataset.
- New configurable `ui` parameter family.

## Capabilities

### New Capabilities
- `ui-access-control`: login, role map, page and data permissions, sessions, CSRF protection, UI audit log.
- `export-upload`: upload, pre-check, registration, synthetic demo uploads, run launch and monitoring.
- `results-explorer`: browsing outcomes and items with evidence highlighted, explanations, workbook download.
- `error-review`: error-typed row inspection on TRAIN and PROD, VALIDATION and TEST aggregates, release of TEST examples after freeze.
- `review-workbench`: review queue, adjudication and blind labelling pages backed by the Human Review System.
- `agent-trace-viewer`: step-by-step agent trace for a row and the tool reference page.
- `kpi-view`: KPI snapshots rendered with the panels shared with the KPI Dashboard.

### Modified Capabilities
<!-- none: the related changes are not yet archived; their artifacts are edited in place -->

## Impact

- New package `itemizer.ui` (FastAPI, Jinja2) and command `itemizer ui`; deployment adds a reverse proxy (Caddy) for TLS on the team-controlled server.
- Depends on add-run-console, add-human-review-system, add-kpi-calculator, add-version-artifact-registry, add-telemetry-episode-store, add-configuration-registry, add-data-transformation-check.
- Changes in place: add-human-review-system (UI is the primary review surface; Excel becomes fallback), add-run-console (UI launches jobs), add-kpi-dashboard (shared panel templates), add-data-transformation-check (pre-check entry point).
- C4: container `webUi` and view `Components-WebUI` in `architecture/workspace.dsl`.
