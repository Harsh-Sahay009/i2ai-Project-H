## ADDED Requirements

### Requirement: One-command run
The CLI SHALL execute ingest, itemization, output formatting and scoring for an export with `itemizer run <export.xlsx> [--env prod]` and write the itemized workbook path on success.

#### Scenario: Weekly run
- **WHEN** an operator runs `itemizer run exports/2026-11-02.xlsx --env prod`
- **THEN** the itemized workbook, the KPI snapshot and the dashboard are produced and the command exits 0

### Requirement: Manifest before work
The orchestrator MUST build and register the run manifest before any stage reads data, and every artifact the run writes SHALL reference its run id.

#### Scenario: Manifest failure
- **WHEN** the effective config fails validation
- **THEN** no stage runs and the command exits 2

### Requirement: Checkpoint and resume
The orchestrator SHALL checkpoint progress and SHALL resume a failed run from its last checkpoint with `--resume <run_id>` without re-processing completed notes.

#### Scenario: Interrupted run
- **WHEN** a run stops after 900 of 1,500 notes and is resumed
- **THEN** only the remaining notes are processed and the final output equals an uninterrupted run with cache on

### Requirement: Budgets never drop rows
When the time or cost budget is exhausted, the orchestrator SHALL stop calling models, mark every unprocessed row as Review with reason `budget_exhausted`, write the output and exit 4.

#### Scenario: Cost budget hit
- **WHEN** the run reaches `budget.max_usd_per_run`
- **THEN** remaining rows are Review, the workbook is complete, and the dashboard shows the budget stop

### Requirement: Performance target
A run of 1,500 rows on the prototype deployment SHALL complete in under 30 minutes on the default route.

#### Scenario: Timing check
- **WHEN** the D4 acceptance run processes a 1,500-row export
- **THEN** the manifest end time minus start time is under 30 minutes

### Requirement: Launch on a registered snapshot
The CLI SHALL accept `--snapshot <id>` to run on an export already registered by the Web UI, and SHALL write job status (stage, progress, exit reason) to action telemetry so the UI can monitor it.

#### Scenario: UI-launched job
- **WHEN** the Web UI launches `itemizer run --snapshot snap_ab12 --env prod`
- **THEN** the run's manifest references that snapshot and its progress events carry the run id

### Requirement: Rerun
`itemizer rerun <run_id>` SHALL restore the manifest's artifacts and re-execute the run, reporting whether outputs are byte-identical.

#### Scenario: Reproducible rerun
- **WHEN** a run is rerun with cache on
- **THEN** the command reports `identical: true`
