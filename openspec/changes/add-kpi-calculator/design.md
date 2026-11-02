## Context

C4 container **KPI Calculator** (10 components). Full metric design: `architecture/docs/04-kpi-calculator.md`. Placement: **common core** (evaluation interface: the shared test every module must pass, per atlas design rules); targets, weights and price table are **configurable layer**. Position: **owned**.

## Goals / Non-Goals

**Goals:** correct, comparable, reproducible numbers with n and intervals; no TEST leakage.

**Non-Goals:** rendering (dashboard); choosing thresholds (training pipeline).

## Decisions

- **Pure function.** `snapshot = f(run_manifest, eval_set_version, metric_definitions_version, weights_version, price_table_version, code_sha)`. Inputs are fetched by hash only; "latest" lookups are forbidden in this package.
- **Populations** never mixed; each metric definition lists valid populations; computing a metric on an invalid population is an error.
- **TEST isolation.** Only this package holds the `kpi_calculator` role. For promotion requests it returns `{gate_status, point estimates, CI}` per metric, never per-row results; each TEST evaluation decrements `kpi.test_peek_budget_per_milestone` and is logged with candidate id.
- **Matching:** Hungarian assignment with costs 0/1/1/2 (doc §4.3), tolerance `kpi.amount_match_tolerance_usd`; matching rule version inside metric definitions.
- **Units:** item, note, row, dollar. TEST results are computed per note, fanned out to rows by row frequency, then weighted by stratum shares `π_s` from the reference production snapshot (`weights@<hash>`).
- **Intervals:** Wilson for unweighted proportions; stratified bootstrap (`kpi.bootstrap_resamples`, seeded) for weighted accuracy, AUC and ECE. Gate status: pass / fail / inconclusive.
- **Error metrics a–g** and **success metrics a–e** exactly as in doc §4.4–4.5. Error (d) duplicates (c) in the brief; it is implemented as the reviewer-side "no fitting category" rate and flagged as an open question.
- **AUC:** scikit-learn `roc_auc_score` on item confidence vs item-correct label; row-level likewise; returns `undefined` when a class is absent rather than a misleading number.
- **Cost:** recomputed from per-call telemetry and the price table version (not from a stored total), so a price correction can be applied retroactively under a new price table version.
- **Reproducibility (e):** compares predictions of runs sharing a manifest except `routing.cache_enabled`; reports row-level agreement and lists diffs.
- **Loop health:** triage latency, share adjudicated, time to update, backlog, expired changes (doc §4.7).
- **Snapshots** append-only rows `(kpi_snapshot_id, run_id, population, versions…, metric_key, stratum, value, ci_low, ci_high, n, gate_status)`, exported to CAS.

## Risks / Trade-offs

- [Few negatives at 95% accuracy → unstable AUC] → report interval and n of negatives; never gate on AUC alone.
- [PROD strata use predicted item counts] → weights flagged as approximate in D5; sensitivity shown with ±10% shares.
- [Approval rate inflated by automation bias] → audit disagreement reported alongside.
- [Definition change mid-project] → new definitions version; dashboard banner for cross-version comparisons.

## Open Questions

- Confirm with the client what error (d) should measure distinctly from (c).
- Baseline accountant minutes per dispute and monthly volume (requested in scope).
