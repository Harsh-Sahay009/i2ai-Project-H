## ADDED Requirements

### Requirement: Validated upload
The UI SHALL accept only file types in `ui.allowed_upload_types` up to `ui.max_upload_mb`, SHALL register the file in the content-addressed store before any processing, and SHALL show the input contract pre-check report.

#### Scenario: Missing column
- **WHEN** an accountant uploads an export without the note column
- **THEN** the pre-check report names the missing column and the launch button is disabled

#### Scenario: Same file uploaded twice
- **WHEN** a file with an existing hash is uploaded
- **THEN** the UI reports the earlier upload and its runs instead of storing a duplicate

### Requirement: Run launch through the pipeline
Launching from the UI SHALL start the same `itemizer run` pipeline the CLI uses, as a background job, and SHALL refuse a new launch when `ui.max_concurrent_runs` jobs are already running.

#### Scenario: Second launch
- **WHEN** a run is in progress and another user clicks launch
- **THEN** the UI refuses and shows the running job and who launched it

### Requirement: Run monitoring
The UI SHALL show each job's stage, processed note count, elapsed time, cost so far and any budget stop or failure, read from telemetry, and the job SHALL continue if the browser is closed.

#### Scenario: Budget stop
- **WHEN** a run stops on the cost budget
- **THEN** the monitor shows exit reason `budget_exhausted` and the number of rows set to Review
