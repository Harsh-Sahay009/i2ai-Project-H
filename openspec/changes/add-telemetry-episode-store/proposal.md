## Why

The atlas says you cannot learn from a decision you cannot reconstruct. Cost of inference, approval rate, reproducibility, loop health and every closed-loop change need a record of what happened (action), why (decision) and what followed (outcome), linked by a stable case id and tagged with the version in force.

## What Changes

- Add the episode store with three telemetry tables and a closed-case table, keyed by case id and run id.
- Add a write API used by all containers and a read API used by KPI Calculator, Review System and Training pipeline.
- Add the experience test: a case is "experience" only when adjudicated, outcome-linked and versioned.

## Capabilities

### New Capabilities
- `telemetry`: action, decision and outcome telemetry, case linkage, closed cases, experience test.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.telemetry`; DuckDB file `${runtime.data_root}/episodes.duckdb`.
- Depends on core contracts (CaseId). Written by Data Prep, Router, Classifier, Run Console, Review System.
