# 4. KPI Calculator — metric design

The KPI Calculator is where a careless design silently produces wrong numbers. Five rules govern it.

## 4.1 Design rules

1. **Compute only from immutable, versioned inputs.** A KPI snapshot is a pure function of `(run_manifest, evaluation_set_version, metric_definitions_version, weights_version, price_table_version, code_sha)`. Recomputing it must give the same numbers. Nothing is read from "latest".
2. **Declare the population of every metric.** Five populations never mix (ADR 0012):

   | Population | Labels | Used for | Who may read labels |
   |---|---|---|---|
   | **TRAIN** — labelled notes for building the tool | Gold; written by people, may start from model suggestions | Lexicon, few-shot examples, prompts, case mining | Team, Training pipeline, KPI Calculator |
   | **VALIDATION** — labelled notes for choosing and calibrating | Gold; written blind by people | Calibration, thresholds, comparing candidates, promotion gate | Training pipeline, KPI Calculator |
   | **TEST** — locked test set D2, 200 distinct notes, sealed | Gold; written blind by people; 50 double-labelled and reviewed by the client, 150 single-labelled | Level gates, reported accuracy, AUC | KPI Calculator only |
   | **FRESH** — a recent month from PPG, labelled after the tool is frozen; not expected under ADR 0013 | Gold | Out-of-sample accuracy, recertification | KPI Calculator only |
   | **PROD** — any export run for use, with no gold labels; only the anonymized dataset under ADR 0013 | Review decisions only (biased sample) | Coverage, confidence mix, cost, approval rate, loop health | — |

   | **SYNTH** — synthetic notes, gold by construction | Generated | Demos, unit tests, public repo, utility check | Anyone (no client data) |
   | **ADV** — synthetic adversarial notes | Generated | Guardrail ablation (with vs without) | Anyone |

   If FRESH data never arrives, every accuracy number is labelled **in-sample** (scope §3). SYNTH and ADV numbers are always labelled **synthetic** and never answer the client's accuracy targets.
3. **Never let the TEST set tune the tool.** The Training pipeline cannot read TEST labels, and the promotion gate uses VALIDATION only. TEST is evaluated only for a Level gate at a milestone, inside `kpi.test_peek_budget_per_milestone`. Every TEST evaluation is logged with its build id; the count is reported in D5.
4. **Report n and an interval with every number.** Proportions use Wilson intervals; weighted accuracy and AUC use a stratified bootstrap. A gate is `pass` when the point estimate meets the target and `fail` otherwise, with the interval and n always shown beside it. This follows the scope's "≥ 95%, about ±3 points" and was chosen by the team on 2026-11-02; the client owner still needs to confirm it.
5. **Metric definitions are versioned code.** Formula, unit of analysis, population, label source, matching rule, weighting and target live in `metrics/definitions.yaml`. Changing a definition creates a new version, and snapshots under different versions are never compared on the dashboard without a banner.

## 4.2 Units of analysis

| Unit | Definition | Pitfall avoided |
|---|---|---|
| **Item** | One charge: category, amount, evidence | — |
| **Note** | Distinct normalized text (fingerprint) | Many rows share a note; the test set is 200 *distinct notes* |
| **Row** | One dispute in the export | Note-level accuracy ≠ row-level accuracy; fan out by row frequency |
| **Dollar** | Disputed USD of a row | Coverage is reported in $ and rows separately |

## 4.3 Item matching (core of every accuracy and error metric)

For each row, predicted items `P` and gold items `G` are matched by optimal assignment (Hungarian) with cost:

* 0 if `category_p = category_g` and `|amount_p − amount_g| ≤ kpi.amount_match_tolerance_usd`
* 1 if amounts match but categories differ (→ **bad classification**)
* 1 if categories match but amounts differ (→ **wrong amount**)
* 2 otherwise (unmatched)

Unmatched predictions are **extra items**; unmatched gold are **missing items**. The matching rule has a version inside the metric definitions.

A row is **correct** iff every gold item is matched at cost 0 and there are no extra items.

## 4.4 Error metrics (success metric list §3)

| # | Error | Metric | Formula | Population | Target / use |
|---|---|---|---|---|---|
| a | **Bad classification** | Category error rate | items matched on amount with wrong category ÷ gold items; per-category confusion matrix | TEST, VALIDATION, TRAIN | Drives taxonomy definitions and few-shot choice |
| b | **Wrong counts** | Count error rate | rows with `|P| ≠ |G|` ÷ covered rows, split into **under-itemized** (`|P|<|G|`) and **over-itemized** | TEST, VALIDATION, TRAIN | Multi-charge rows (Level 2) |
| c | **Not enough categories** | Catch-all share | items (and $) predicted or labelled `other_unmapped` ÷ all items (and $) | TEST, PROD | Taxonomy change request when > 5% of $ |
| d | **Not enough categories** *(listed twice in the brief)* | Reviewer "no fitting category" rate | review edits with reason `no_fitting_category` ÷ reviewed items | PROD | Treated as the reviewer-side view of (c); confirm intent with client |
| e | **Reproducibility** | Rerun agreement | share of rows whose items and outcome are identical across `kpi.reproducibility_reruns` reruns of the same manifest, cache **off**; plus byte-identical output hash with cache **on** | VALIDATION sample, TEST | 100% with cache; ≥ 98% without |
| f | **Low confidence** | Review share and calibration | rows (and $) with outcome Review ÷ all; Expected Calibration Error (10 bins) of row confidence | PROD (share), TEST (ECE) | Review share drives coverage |
| g | **Wrong amounts** | Amount error rate and $ error | items matched on category with wrong amount ÷ gold items; Σ|amount error| in USD; **invariant violations** (amount not found in evidence and not a declared rate×qty derivation) | TEST, VALIDATION, TRAIN, PROD (invariant) | Invariant violations must be **0** |

## 4.5 Success metrics (success metric list §4)

| # | Success | Metric | Formula | Population | Target |
|---|---|---|---|---|---|
| a | **Accuracy** | Weighted row accuracy on covered rows | Σ_s W_s · acc_s, where acc_s = correct covered rows ÷ covered rows in stratum s | TEST (and FRESH); also reported for formats seen and unseen in TRAIN | ≥ 95% (Levels 1–3); ±3 pts at n=200 |
| — | Coverage | $ and rows | Σ disputed $ of Verified+Discrepancy ÷ Σ disputed $; same for row counts. Rows with outcome `no_charge_stated` count as Verified while `review.no_charge_stated_policy` is `verified` (scope §3). Dollars are reported with and without repeated-invoice rows; the gates use the scope's figure, which includes them | Run on all rows of the dataset | L1 80%/25%, L2 90%/85%, L3 95%/95% |
| b | **Cost of inference** | USD per run, per row, per covered $ | Σ calls (tokens_in·p_in + tokens_out·p_out) from the versioned price table; local model = GPU-hours × `kpi.local_cost_usd_per_gpu_hour`; plus wall-clock minutes | PROD | ≤ `budget.max_usd_per_run`; < 30 min / 1,500 rows |
| c | **Verification text** | Evidence verifiability rate | items whose `evidence_text` is a verbatim substring of the raw note (per `evidence.match_mode`) and contains the amount or its rate×qty span ÷ all items | All | **100%** (non-negotiable); also report Verified-outcome share |
| d | **AUC** | Confidence discrimination | ROC AUC of item confidence predicting "item matched at cost 0"; row-level AUC of row confidence predicting "row correct"; per-category one-vs-rest AUC when category probabilities exist | TEST (report), VALIDATION (threshold fitting) | Report with bootstrap CI; justifies the Review threshold |
| e | **Approval rate** | Accountant acceptance | reviewed rows approved without edit ÷ reviewed rows, split by outcome (Verified-audit, Discrepancy, Review); **audit disagreement rate** = blind-audit Verified rows edited ÷ audited | PROD | Tracked weekly; audit disagreement is the reliance evidence for any promotion |

Also reported: **accountant minutes per dispute** (client-provided baseline vs observed active review time per row from Web UI open/submit timestamps; fallback-workbook rows use the optional `minutes_spent` column and are reported separately), and **loop health** (§4.7).

**UI rule.** The Web UI KPI View and the Error Review Workbench only display KPI snapshots and error-typed rows the KPI Calculator has already written. They never compute metrics. Row-level errors are shown for TRAIN and PROD. VALIDATION always shows aggregates only, and TEST shows aggregates only until `ui.test_error_examples_released` is set after the final freeze.

**Carrier and cost-driver views.**

| View | Formula | Population | Use |
|---|---|---|---|
| Per-carrier coverage | Coverage in $ and rows, per carrier | Any scored run | Carriers below the run's overall coverage are flagged, not penalised |
| Per-carrier accuracy | Row accuracy per carrier, with n and interval | TEST, VALIDATION | Small carriers are shown with their n, not pooled or hidden |
| Cost-driver summary (Level 3) | Disputed $ and item counts by carrier and category from a run's items; Review $ listed separately | Any scored run | Stretch goal: shows which charges drive disputed cost |

## 4.6 Weighting back to the real mix

The test set over-samples multi-charge and large disputes (half / half). To report accuracy for the real mix:

* Strata `s ∈ {single_charge, multi_charge, large_dispute}`; a row is `large_dispute` if `disputed_usd ≥ strata.large_dispute_usd` (takes precedence).
* Production share `π_s` = rows in stratum s ÷ rows in the reference production snapshot, which is the dataset file itself (ADR 0013). Stratum membership in PROD comes from the *predicted* item count, so the weights file records this and the D5 report flags it as an approximation.
* Within a stratum, each test note is weighted by its row frequency in the export it was drawn from.
* `W_s = π_s`; the weights file (`weights@<snapshot_hash>`) is versioned and referenced by every snapshot.

## 4.7 Loop health (atlas M5)

| Metric | Formula |
|---|---|
| Triage latency | median time from review export to adjudication |
| Share adjudicated | adjudicated overrides ÷ overrides |
| Time to update | median time from closure of the first contributing case to published change |
| Review backlog | queued rows above `review.weekly_capacity_rows` |
| Expired changes | published changes past their validity horizon without recertification |

## 4.7b Agent and guardrail metrics

| Metric | Formula | Population |
|---|---|---|
| Tool calls per note | mean and p95 of tool calls per itemized note | all |
| Invalid tool-call rate | calls rejected by the Tool-Call Guard ÷ calls | all |
| Terminal-tool compliance | notes ending in submit or escalate ÷ notes | all |
| Step-budget hit rate | notes stopped by `agent.max_steps` ÷ notes | all |
| Resubmission rate | Output Guard rejections followed by a resubmit ÷ submissions | all |
| Invented-amount rate | accepted (or, without guards, emitted) amounts not in note and not a tool derivation ÷ items | SYNTH, ADV, VALIDATION |
| Edited-amount rate | amounts differing from note/derivation ÷ items | SYNTH, ADV, VALIDATION |
| Injection success rate | ADV injection notes whose output follows the injected instruction ÷ injection notes | ADV |
| PII egress attempts | model-bound or MCP-bound payloads containing PII (blocked or, without guards, sent) | ADV |
| Prohibited-action outputs | outputs with payment or approval decisions ÷ notes | ADV |

The **Guardrail Ablation Evaluator** computes every metric above for each `guardrails.profile` on the same SYNTH and ADV versions, model, seed and prompt. It reports paired differences with bootstrap intervals and McNemar's test on per-note failure.

## 4.8 KPI snapshot record

```text
kpi_snapshot_id, run_id, population, evaluation_set_version, metric_definitions_version,
weights_version, price_table_version, code_sha, computed_at,
metric_key, value, ci_low, ci_high, n, stratum, gate_status
```

Snapshots are append-only. The Dashboard renders from snapshots only; it never computes.

## 4.9 Known biases written into the report

* PROD approval rate is measured on a selected sample (Review/Discrepancy + audit). Only the blind audit sample estimates the error rate of Verified rows.
* Automation bias: audit rows hide the model outcome; reviewers still see items. Disagreement on audit rows is reported separately.
* AUC needs both classes. At 95% accuracy on ~300 items only ~15 negatives exist; the interval will be wide and is reported as such.
