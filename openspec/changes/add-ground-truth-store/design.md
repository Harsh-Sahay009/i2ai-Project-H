## Context

C4 container **Ground Truth Store**. Placement: **common core** (taxonomy and evaluation interface are shared by every module). Position: **owned** — evaluation sets are the firm-specific asset the atlas says to own.

## Goals / Non-Goals

**Goals:** approved taxonomy versions; sealed TEST; disjoint TRAIN, VALIDATION and FRESH; provenance good enough for D5.

**Non-Goals:** the labelling UI/workflow (Human Review System); metric computation (KPI Calculator).

## Decisions

- **Taxonomy as YAML in Git** (`taxonomy/categories.yaml`): `code`, `name`, `definition`, `includes`, `excludes`, `examples` (fingerprint + offsets; quotes are resolved from the dataset when rendered, so Git holds no note text), `standard_codes` (Level 3, optional). Tag `taxonomy@D1-approved` requires an approval record (`approved_by_role`, date, evidence file hash).
- **Catch-all `other_unmapped`** exists in every version so error (c) is measurable.
- **TEST sampling (D2):** 200 distinct notes; 100 single-charge, 100 multi-charge-or-large; drawn by stratified random sampling with recorded seed; ~300 items expected. Sampling runs in `add-ground-truth-bootstrap`; this store registers the result.
- **Labelling provenance:** both labellers' raw labels, Cohen's kappa on category and exact-match on amount, review of all 50 double-labelled notes by Jake or a PPG accountant, including resolution of every disagreement; final gold table.
- **Sealing:** TEST is registered sealed; its fingerprint list (not labels) is exported for exclusion.
- **TRAIN and VALIDATION (ADR 0012):** the remaining notes, split by distinct note. TRAIN builds the tool; VALIDATION calibrates and chooses between candidates. FRESH: a recent month labelled after the tool is frozen, not expected under ADR 0013.
- **Taxonomy change requests** carry evidence (share of $ in catch-all, reviewer reasons) and need client approval; a new taxonomy version invalidates comparisons with older KPI snapshots unless a mapping is published.

## Risks / Trade-offs

- [200 notes give ±3 pts at 95%] → reported with intervals; no FRESH month is expected, so results are labelled in-sample.
- [Taxonomy change after D2 invalidates gold] → mapping table old→new codes required; relabel only affected items.

## Open Questions

- None for the split: the file has 729 distinct notes (ADR 0012).
- ANSI X12 license availability for Level 3.
