## Context

C4 container **Telemetry & Episode Store**. Placement: **common core** (logging schema). Position: **owned** (outcome histories).

## Goals / Non-Goals

**Goals:** reconstruct any decision; link review outcomes back to cases; support KPI recomputation.

**Non-Goals:** application debug logging; real-time monitoring.

## Decisions

- **DuckDB** single file; append-only tables. Alternative: SQLite. DuckDB chosen for analytical queries from the KPI Calculator.
- **Tables:** `action_events(run_id, case_id?, stage, event, provider, model_id, tokens_in, tokens_out, latency_ms, cost_usd, cache_hit, ts)`, `decision_records(case_id, item_id?, hints, response_hash, parsed, evidence_ok, delta, confidence_components, thresholds, outcome, rule, ts)`, `outcome_records(case_id, reviewer_role, decision, corrected_items, reason_code, bucket, review_started, review_ended, workbook_hash, ts)`, `cases(case_id, status, reason_code, replay_pack_hash, outcome_link, version_tag, closed_at)`.
- **No PII in telemetry:** note text referenced by fingerprint; reviewer recorded by role and pseudonymous id.
- **Experience test** as a view: `adjudicated AND outcome_linked AND versioned`.

## Risks / Trade-offs

- [Concurrent writers] → single-process pipeline writes through one connection; review import runs separately.

## Open Questions

- Will PPG share later dispute resolution (paid/denied) for slow-clock outcome telemetry?
