# 6. Product invariants live in the common core and are not configurable

Date: 2026-10-31

## Status

Accepted

## Context

Scope: every item shows its exact words; the tool never invents or edits an amount; non-reconciling rows are flagged.

## Decision

Evidence Verifier and Amount Reconciler are mandatory stages with no disabling parameter. Violations count as errors (g) and block a promotion.

## Consequences

Some correct-but-paraphrased model outputs are rejected to Review; this lowers coverage but keeps trust.
