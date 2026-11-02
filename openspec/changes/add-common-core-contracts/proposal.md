## Why

Every container exchanges dispute rows, notes, items and outcomes. Without one fixed contract each stage invents its own shapes, the KPI Calculator cannot compare runs, and the scope invariants (exact evidence, no edited amounts, flagged non-reconciling rows) are enforced nowhere in particular. The atlas design rules say: standardize the contract, not the implementation.

## What Changes

- Define the shared data contracts as pydantic models and JSON Schemas: `DisputeRow`, `Note`, `ChargeItem`, `RowResult`, `RowOutcome`, `CaseId`.
- Define the invariant checks as reusable, non-configurable validators.
- Define the run manifest and `run_id` derivation that every stage, store and KPI references.
- Publish contract tests that any implementation of a stage must pass.

## Capabilities

### New Capabilities
- `item-schema-contract`: shared schemas for rows, notes, items, row outcomes and the product invariants.
- `run-manifest`: the frozen, hashed description of every input to a run (the atlas version tag).

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.core` (contracts, invariants, manifest). No runtime dependencies beyond pydantic.
- Consumed by every other change; must land first.
- C4: common core across all containers; Run Manifest Builder component (Run Console).
