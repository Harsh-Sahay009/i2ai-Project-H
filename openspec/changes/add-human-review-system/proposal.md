## Why

Accountants keep the payment decision, and Review/Discrepancy rows need a person. Their decisions are the richest signal the system produces: approval rate (success e), audit disagreement on Verified rows, and the cases that drive improvement. The atlas warns that adjudication capacity is the binding constraint and that unadjudicated feedback is noise; it also warns of automation bias. D2 needs a blind double-labelling protocol.

## What Changes

- Review Queue Builder bounded by weekly capacity, prioritized by disputed dollars, with a blind audit sample of Verified rows.
- A single Review Decision Intake used by the Web UI (primary surface, see add-web-ui) and by an offline Excel review workbook (fallback) with locked prediction columns.
- Adjudication into four buckets with reason codes from the error taxonomy.
- Blind labelling protocol for TEST (two labellers on 50 notes, agreement, client review of all 50, sealing) and for TRAIN, VALIDATION and FRESH. D2 itself runs on workbooks from `add-ground-truth-bootstrap`; this change serves the UI and later labelling.
- Case Closer requiring reason code, replay pack, outcome link and version tag.

## Capabilities

### New Capabilities
- `review-workflow`: queue, review workbook, import, approval tracking, audit sampling, blind labelling.
- `adjudication`: four-bucket adjudication, reason codes, case closure.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.review`.
- Depends on core contracts, configuration registry (workflow family), version registry, ground truth, telemetry store.
