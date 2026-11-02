## Context

C4 container **Training & Calibration Pipeline** (7 components). ADR 0004: tuning, not training. Placement: produces **configurable layer** changes; the gate itself is **common core**. Position: **owned**.

Authority: publishing a change is **supervised**: the pipeline proposes, the operator approves at the gate.

## Goals / Non-Goals

**Goals:** every behaviour change traceable to cases and evidence; no TEST leakage; safe rollback; scheduled re-validation.

**Non-Goals:** fine-tuning model weights; automatic publication without a person.

## Decisions

- **Eligible inputs only:** cases closed with buckets AI wrong or context changed, at least `adjudication.min_cases_for_change` per reason code, excluding any `test_fingerprint` rows.
- **Candidate types:** `lexicon_add`, `fewshot_swap`, `prompt_edit`, `threshold_update`, `calibration_refit`, `taxonomy_change_request` (needs client approval, routed to ground truth).
- **Calibration:** isotonic regression of correctness on raw confidence over DEV; row threshold chosen as the lowest value giving Verified-row precision ≥ target (default 0.97) on DEV; per-category overrides only with ≥ 30 DEV items in the category.
- **Replay:** candidate vs current on (1) the replay packs of the contributing cases, (2) full DEV; row-level diff with error-type deltas. Cache keyed by the candidate manifest, so replays are reproducible.
- **Promotion evidence** (atlas M6 four channels, adapted):
  - Operating: DEV improvement and one aggregate TEST evaluation with no regression on any error type beyond its interval and no invariant violations.
  - Reliance: PROD audit disagreement not worse than current (when available).
  - Control: confidentiality gate and contract tests pass for the candidate.
  - Recovery: rollback pointer exists and a rollback dry run succeeds.
- **Publication record:** owner role, evidence (snapshot ids, case ids), version, rollback pointer, validity horizon (from the parameter catalog), change log entry.
- **Recertification:** on horizon expiry, on model digest change, or on `silent_change` canary events; re-run FRESH (or newest labelled PROD sample); failure → narrow or roll back with operator approval.

## Risks / Trade-offs

- [Overfitting DEV] → TEST evaluated once per candidate, peek budget reported in D5.
- [Too few cases to justify a change] → minimum case count; otherwise keep as local exception.
- [Validity horizons ignored] → expired changes shown on dashboard and printed at every run.

## Open Questions

- Target Verified-row precision (default 0.97) to be confirmed with the client owner.
