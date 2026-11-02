## Why

D4 requires the tool to run on a new export with one command. The Web UI (ADR 0007) and operators both need one pipeline owner that freezes every input before work starts, so each run is reproducible and comparable whichever surface launched it.

## What Changes

- Add the `itemizer` CLI: `run`, `rerun`, `evaluate`, `review export|import`, `calibrate`, `replay`, `promote`, `recertify`, `report`, `config …`, `lineage`.
- Add the Pipeline Orchestrator: ingest → route/itemize → format → score, with checkpoints and resume by run id.
- Add the Run Manifest Builder invocation before stage 1.
- Accept `--snapshot <id>` so the Web UI can launch runs on an already-registered upload as a background job, and report job status via telemetry.
- Enforce the runtime budget (<30 min for 1,500 rows) and cost budget.

## Capabilities

### New Capabilities
- `run-console`: command surface, orchestration, checkpoints, budgets, exit codes.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.cli` (Typer) and `itemizer.pipeline`.
- Depends on core contracts, configuration registry, version registry; invokes all stage containers.
