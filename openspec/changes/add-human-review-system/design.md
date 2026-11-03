## Context

C4 container **Human Review System** (Queue Builder, Workbook Exporter (fallback), Review Decision Intake, Adjudication Recorder, Blind Labelling Protocol, Case Closer). Placement: workflow structure **common core**; capacity, audit rate, priority **configurable layer**; genuine exceptions **local exception**. Position: **owned**.

Authority: the accountant decides; the tool recommends. Payment remains **prohibited** for the tool.

## Goals / Non-Goals

**Goals:** fit PPG's time budget; unbiased estimate of Verified-row error; every override judged before it changes anything.

**Non-Goals:** UI pages (add-web-ui); payment recording.

## Decisions

- **Web UI is the primary review surface** (ADR 0007); this container is the service behind it. The Excel workbook remains an offline fallback with protected prediction columns. Both surfaces submit through one Review Decision Intake carrying the prediction hash the reviewer saw. Decision fields: decision columns: `decision` (approve/edit/reject), `corrected_items` (structured columns per item), `reason_code` (dropdown from error taxonomy: bad_classification, wrong_count_missing, wrong_count_extra, no_fitting_category, wrong_amount, evidence_wrong, other), `comment`, `minutes_spent` (optional).
- **Queue:** all Review and Discrepancy rows + `review.audit_sample_rate_verified` random sample of Verified rows (seeded, recorded); sorted by `review.priority`; truncated at `review.weekly_capacity_rows`; overflow logged as backlog.
- **Blind audit:** audit rows hide the tool's outcome and confidence band; items are still shown (cannot hide without making review impossible); disagreement reported separately as automation-bias guard.
- **Adjudication** by a labeller/adjudicator role, not the original reviewer: buckets AI wrong / human wrong / context changed / genuine exception. Only AI wrong and context changed may feed improvement (`adjudication.min_cases_for_change` before a change is proposed).
- **Labelling protocol (D2):** two labellers label 50 notes without tool output; Cohen's kappa on category, exact-match on amounts; the client reviewer (Jake or a PPG accountant) reviews all 50 and resolves every disagreement; remaining 150 single-labelled with spot checks; seal via ground truth store. The tooling comes from `add-ground-truth-bootstrap`.
- **Case closure:** reason code + replay pack (note fingerprint, manifest, prediction, decision) + outcome link + version tag.

## Risks / Trade-offs

- [Reviewer capacity too small] → backlog visible on dashboard; priority by $ ensures large disputes first.
- [Excel tampering with locked columns] → intake compares hashes of prediction columns and rejects changed rows.
- [Decision on a stale prediction in the UI] → intake rejects mismatched prediction hashes.

## Open Questions

- Actual weekly capacity and current minutes per dispute from PPG (scope asks for both).
