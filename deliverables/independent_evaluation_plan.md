# Independent reproduction and evaluation

We can run a new, fully recorded experiment without Alejandro's original run files. Those files are needed only to reproduce the exact historical run. The supplied `test_provisional.json` provides an existing benchmark of 200 notes, with model-drafted reference answers; it is not independently verified ground truth.

## Fixed inputs

- Dataset SHA-256: `e08da6c7fd6e03036d537a13ed0a52748ef81fc5cedea0df7f3ec037bc43c0e5`.
- Benchmark SHA-256: `f1c566fe2bf036088765db61ecd0cd8e6f84ea8822416ada6bc21d067ab33697`.
- Benchmark: 200 notes, 279 items, 307 associated dispute rows. Original reference strata: 103 single, 47 multi, 50 large.
- Zero benchmark notes occur in either the current prompt examples or taxonomy examples. All references pass identity, category, evidence-span and amount checks.
- All 200 reference labels remain `model_draft`. The dataset and prior benchmark results have already been seen by the team; this is a reproduction on an existing benchmark, not a new unseen test.

## Procedure

1. Keep the received benchmark immutable. Store new experiment records under ignored `data/evaluation/independent-v1/`; do not create historical freeze/approval/agreement records.
2. Record dataset, benchmark, source code, taxonomy, worked examples, rendered prompt, model registry entry and inference settings by hash before predictions. Benchmark answers must never enter the extraction prompt. Keep the other 529 distinct notes outside the benchmark for development; do not claim to have recreated the historical TRAIN/VALIDATION split.
3. Confirm the inference route. No API credential or running Ollama model was available during the readiness check. External sends require the actual data-use authorization and a recorded scan decision; local inference does not send notes externally.
4. Use a small development-only smoke run to verify model access and schema handling. Freeze the candidate configuration before benchmark scoring. Do not choose models or prompts from repeated scores on these 200 notes.
5. Run fresh extraction on all 729 distinct nonempty notes, preserving per-note outputs, telemetry, cache identity and an itemized workbook for all 1,347 dispute rows.
6. Score predictions on the fixed 200 references with the existing matching and weighting functions. Report covered and total benchmark notes, exact all-item agreement, category/amount/missing/extra errors, large/multi/single strata, confidence intervals, full-data row/dollar coverage, accepted-without-reading shares, invariant violations, runtime and cost. Incomplete provider runs are not accepted as completed evaluations.
7. Label the reference-based score **agreement with model drafts**. If the extraction model is also Opus, explicitly state the shared-model dependence. No human-verified accuracy or completed client acceptance is claimed.
8. Independently check the reference answers with real reviewers, including the required two-reader subset and client review. Preserve reviewer identities and corrections. Re-score the same saved predictions against reviewed references without new model calls. Keep the original and corrected-reference scores side by side.

## Immediate reference audit

`data/evaluation/independent-v1/reference_audit.json` is a reference-quality audit, not a prediction evaluation. It records zero contract errors or prompt/taxonomy leakage, 12 notes where the original model expressed doubt, and 31 of the 307 associated rows whose disputed amounts do not reconcile with their reference items. Reconciliation mismatches are not automatically labeling mistakes: repeated invoices and genuine discrepancies can be legitimate. Review doubtful and large-dispute references first, without adjusting amounts to make them add up.

## Pending inputs

Select/configure model access and decide the data-use route before inference. No new model calls or scoring have been performed by this audit. The portable workbook at `data/incoming/alejandro/test_label_review_portable.xlsx` is available for human review while inference access is arranged.

## Gemini execution update — 5 November 2026

The user confirmed external use is approved in writing and supplied a Gemini API credential in a local Desktop file. The credential is stored only in ignored `.env` with mode 0600; no key or curl command is executed or included in project source. No local model was downloaded and no billing settings were changed.

Model discovery and a harmless request succeeded. `gemini-3.8-flash` had service-availability problems during development-only checks. `gemini-3-flash-preview` returned a valid structured answer to the full extraction prompt on a development note in 2.49 seconds. Model choice was based on availability and schema compatibility before benchmark scoring, not TEST scores. This does not establish accuracy.

`python -m itemizer.independent --experiment gemini-free-v2 --run` runs the fixed 200-note benchmark first. The preflight-only `independent-v1` and `gemini-free-v1` protocols are retained; v2 records the final privacy and scoring corrections. Outputs are under ignored `data/evaluation/gemini-free-v2/benchmark/`; request/answer cache is under the experiment's `cache/`. Input hashes are frozen, and changes require a new experiment version. A circuit breaker stops new requests after provider failure; incomplete runs produce no accuracy. Retrying the same protocol reuses cached answers.

Benchmark weights use the supplied reference strata and their actual row counts, independently of predictions. This phase covers the 307 rows associated with the 200 benchmark notes; it does **not** measure full-export coverage. A later `--scope all` run can reuse the cache to cover all 729 notes and 1,347 rows. Its predicted full-population weighting remains explicitly approximate, matching the existing KPI method. Neither phase creates official D3 acceptance or a human-reviewed reference set.

The selected Gemini entry uses free-tier zero rates from Google's documented free quota; these are not paid-tier prices or a billing audit. Free-tier availability/limits are controlled by the account. No upgrade to paid billing is authorized by this plan.

Implementation checks: 125 new/affected tests pass (six independent-evaluation checks and 119 provider tests). Independent code review found no remaining blockers. Live inference results are recorded separately after completion; no provisional score is inferred from a progress counter.
