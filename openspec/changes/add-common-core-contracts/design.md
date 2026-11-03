## Context

The C4 container view has 19 containers. Common-core elements per atlas M5: logging/audit schema, routing contract, evaluation interface, version registry. This change provides the schema half; registries are separate changes.

Placement: **common core**. Position: **owned** (item schema, invariants) and **controlled** (manifest).

## Goals / Non-Goals

**Goals:** one importable definition of every cross-stage record; invariants as code; deterministic `run_id`.

**Non-Goals:** storage (version registry), configuration resolution (configuration registry).

## Decisions

- **pydantic v2 models as the source; JSON Schema generated from them.** Alternative: hand-written JSON Schema. Rejected: drifts from code.
- **Money as `Decimal` with 2 places, currency explicit.** Floats cause wrong-amount errors (g) at reconciliation.
- **`ChargeItem` fields:** `row_id`, `item_id`, `note_fingerprint`, `category`, `amount`, `currency`, `evidence_text`, `evidence_start`, `evidence_end`, `line_type` (`charge` | `tax` | `already_paid`), `derivation` (`stated` | `rate_x_quantity`), `derivation_spans`, `confidence`, `taxonomy_version`.
- **`RowResult` fields:** `row_id`, `disputed_amount`, `items`, `items_total`, `already_paid_total`, `delta`, `outcome` (`verified` | `discrepancy` | `review` | `no_charge_stated`), `outcome_reason`, `row_confidence`, `run_id`.
- **`CaseId = (run_id, row_id)`** used by all telemetry.
- **Manifest canonicalization:** sorted-key JSON, UTF-8, no whitespace; `run_id = "run_" + sha256(canonical)[:16]`, full hash stored.
- **Invariant validators** are pure functions returning violations; stages call them, KPI counts them. They take no parameters except `evidence.match_mode`, whose enum cannot express anything looser than whitespace normalization.

## Risks / Trade-offs

- [Schema churn during D3] → version the contract (`contract_version`) and keep migrations in one module.
- [Rate × quantity amounts are not literally in the text] → `derivation_spans` must point at both factors; the verifier recomputes the product.

## Open Questions

- Does PPG need CAD support, or only USD? `US/CAN` says US on every row, but 13 notes mention Canadian taxes and none state a currency. (Default USD; enum allows CAD; ask Jake.)
