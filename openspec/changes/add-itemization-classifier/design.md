## Context

C4 container **Itemization Classifier** (8 components). Placement: item schema, verifier and reconciler are **common core**; prompt, few-shot, lexicon, thresholds and calibration are **configurable layer**; unsettled carrier conventions are **local exception** (routed to Review). Position: **owned** business logic; Prompt Builder is **controlled**.

Authority rung: **recommend**. The classifier proposes items and an outcome; it never decides payment.

## Goals / Non-Goals

**Goals:** high precision on Verified rows; every item verifiable; honest confidence; deterministic given the manifest.

**Non-Goals:** paying decisions; correcting carrier arithmetic; training model weights.

## Decisions

- **Bounded agent (ADR 0008).** The LLM decides which tools to call and how to group spans into items. Tools do all arithmetic, lookup, verification and reconciliation. Budgets: `agent.max_steps`, `agent.max_calls_per_tool`, `agent.max_resubmits`. Temperature 0, pinned model, cache keyed by the full transcript. Every turn and tool call is recorded as decision telemetry and shown in the UI's Agent Trace Viewer.
- **Hybrid extraction.** Rules first to find every money token and pattern (also exposed as `extract_money_spans`); the agent assigns categories and groups tokens into items. Rules-only is also a full route (fallback and baseline). Alternative: model-only. Rejected: amounts are the costliest errors (g); rules give recall checks and an agreement signal for confidence.
- **Structured output** through the terminal tool `submit_itemization` (ChargeItem schema); a final message without a terminal call → Review (`no_terminal_call`); parse failure → provider failure path, not repair.
- **Evidence verification** maps model-quoted evidence to offsets in the raw note; non-verbatim → item rejected; if any item is rejected the row goes to Review (`evidence_failed`).
- **Reconciliation** uses Decimal: `delta = disputed − (Σ items − Σ already_paid)`; `|delta| ≤ max(abs_tol, rel_tol·disputed)` → candidate Verified; else Discrepancy. Amounts are never changed.
- **Confidence** features: model log-prob or self-reported score (if available), extractor agreement (every money token explained?), evidence pass, reconciliation pass, category definition match, note length. Combined via a published isotonic calibration map fitted on VALIDATION. Row confidence = min over items × reconciliation factor (documented in metric definitions).
- **Outcome rules** (ordered): no money tokens and model says none → `no_charge_stated` (policy per `review.no_charge_stated_policy`); any evidence failure or provider unavailable → Review; row confidence < `confidence.review_threshold_row` → Review; reconciles → Verified; else Discrepancy.
- **Fan-out** from fingerprint to rows; row-specific fields (disputed amount) applied per row, so reconciliation is per row even when the note is shared.
- **Decision telemetry:** hints, raw output hash, parsed items, verifier result, delta, confidence components, thresholds in force, outcome rule fired.

## Risks / Trade-offs

- [Model paraphrases evidence → many Review rows] → prompt instructs verbatim quoting; measured as verification-text rate; few-shot examples show exact quotes.
- [Shared note with different disputed amounts] → per-row reconciliation handles it; flagged in telemetry.
- [Confidence poorly calibrated on small VALIDATION] → ECE and AUC reported; conservative thresholds.

## Open Questions

- How should "amounts already paid" be shown in the output — negative item or separate column? (Proposed: separate derivation `already_paid`, shown as negative line.)
