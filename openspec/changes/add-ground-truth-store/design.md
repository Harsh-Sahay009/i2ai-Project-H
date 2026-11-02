## Context

C4 container **Ground Truth Store**. Placement: **common core** (taxonomy and evaluation interface are shared by every module). Position: **owned** — evaluation sets are the firm-specific asset the atlas says to own.

## Goals / Non-Goals

**Goals:** approved taxonomy versions; sealed TEST; disjoint DEV and FRESH; provenance good enough for D5.

**Non-Goals:** the labelling UI/workflow (Human Review System); metric computation (KPI Calculator).

## Decisions

- **Taxonomy as YAML in Git** (`taxonomy/categories.yaml`): `code`, `name`, `definition`, `includes`, `excludes`, `examples` (fingerprint + quote), `standard_codes` (Level 3, optional). Tag `taxonomy@D1-approved` requires an approval record (`approved_by_role`, date, evidence file hash).
- **Catch-all `other_unmapped`** exists in every version so error (c) is measurable.
- **TEST sampling (D2):** 200 distinct notes; 100 single-charge, 100 multi-charge-or-large; drawn by stratified random sampling with recorded seed; ~300 items expected.
- **Labelling provenance:** both labellers' raw labels, Cohen's kappa on category and exact-match on amount, resolution by client owner for the 50 double-labelled notes; final gold table.
- **Sealing:** TEST is registered sealed; its fingerprint list (not labels) is exported for exclusion.
- **DEV:** remaining sample notes labelled for tuning; FRESH: one recent month labelled after the tool is frozen.
- **Taxonomy change requests** carry evidence (share of $ in catch-all, reviewer reasons) and need client approval; a new taxonomy version invalidates comparisons with older KPI snapshots unless a mapping is published.

## Risks / Trade-offs

- [200 notes give ±3 pts at 95%] → reported with intervals; FRESH adds out-of-sample evidence.
- [Taxonomy change after D2 invalidates gold] → mapping table old→new codes required; relabel only affected items.

## Open Questions

- Will PPG provide the FRESH month? Without it, accuracy is reported as in-sample.
- ANSI X12 license availability for Level 3.
