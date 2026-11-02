# 6. Telemetry, the closed loop and adjudication capacity

## 6.1 Three telemetry layers (atlas M5)

All three are keyed by `case_id = (run_id, row_id)` and, for items, `item_id`.

| Layer | Records | Written by |
|---|---|---|
| **Action** — what happened | stage timings, route taken, provider, model id, tokens in/out, latency, cache hit, retries, fallbacks, data-quality findings | Data Prep, Router, Run Console |
| **Decision** — why | extractor hints, raw model output hash, parsed items, evidence check result, reconciliation delta, confidence components, thresholds in force, outcome and the rule that assigned it | Classifier |
| **Outcome** — what followed | reviewer decision (approve / edit / reject), corrected items, reason code, adjudication bucket, review open/submit timestamps, surface (UI or fallback workbook), later dispute resolution if PPG shares it | Human Review System (fed by the Web UI) |

The Web UI also writes **UI audit events** (upload, run launch, decision, label, download), keyed by role and pseudonymous id. They are action telemetry about people, used for accountability and review-time measurement, not for tuning.

## 6.2 The closed loop

```
Intervention (accountant edits/rejects, or audit disagreement)
  → Adjudication: AI wrong | human wrong | context changed | genuine exception (+ reason code)
  → Replay pack (note, manifest, prediction, decision)
  → Candidate change (lexicon, few-shot, prompt, threshold, taxonomy request)
  → Replay on DEV: current vs candidate
  → Promotion gate: one aggregate TEST evaluation, no regression on any error type
  → Published change under a version tag (owner, evidence, version, rollback, validity horizon)
```

What each bucket is allowed to change:

| Bucket | Action | May change behaviour? |
|---|---|---|
| AI wrong | Fix prompt / lexicon / threshold | Yes |
| Human wrong | Keep rule; coach reviewer; note in report | No |
| Context changed | Update for the new world (e.g., new carrier format) | Yes, with new validity horizon |
| Genuine exception | Keep visible as local exception | No |

A case **closes** only with reason code, replay pack, outcome link and version tag. Open cases are listed in the dashboard and never mined.

## 6.3 Adjudication capacity

The binding constraint is reviewer time (the scope budgets ~3 hours of PPG time). The queue is therefore sized, not unbounded:

* `review.weekly_capacity_rows` caps the queue; overflow is counted as **backlog** and surfaced, never silently dropped.
* Priority by disputed dollars puts consequential cases first.
* Audit sampling of Verified rows is the minimum viable loop; it is the only unbiased estimate of Verified-row error in PROD.

## 6.4 Validity horizons and recertification

Every published change carries a horizon (defaults in the parameter catalog). The Recertification Scheduler re-runs FRESH (or the latest labelled PROD sample) when a horizon passes, when the model digest changes, or when a canary set's response fingerprints drift (silent upstream change). Failure sends the change back for narrowing or rollback.
