## ADDED Requirements

### Requirement: Capacity-bounded queue
The queue builder SHALL include all Review and Discrepancy rows plus a seeded random sample of Verified rows at `review.audit_sample_rate_verified`, order them by `review.priority`, cap the queue at `review.weekly_capacity_rows`, and record the overflow as backlog.

#### Scenario: More rows than capacity
- **WHEN** 140 rows qualify and capacity is 60
- **THEN** the 60 highest-priority rows are exported and a backlog of 80 is recorded

### Requirement: Single decision intake for UI and workbook
The Review Decision Intake SHALL accept decisions from the Web UI and from the fallback workbook through the same validation, and SHALL reject a decision whose prediction hash differs from the current prediction.

#### Scenario: Same decision, two surfaces
- **WHEN** identical decisions arrive from the UI and from a returned workbook
- **THEN** both produce outcome records with the same fields, differing only in the `surface` value

### Requirement: Fallback review workbook with locked predictions
When `ui.allow_workbook_fallback` is true, the exporter SHALL write a review workbook whose prediction columns are protected and whose decision columns accept approve, edit or reject, corrected items and a reason code from the error taxonomy.

#### Scenario: Edit requires reason
- **WHEN** `review.require_reason_code_on_edit` is true and a row is marked edit without a reason code
- **THEN** the importer rejects that row with a message

### Requirement: Tamper-checked import
The importer MUST reject rows whose prediction columns differ from the exported values.

#### Scenario: Amount overwritten in prediction column
- **WHEN** a reviewer types a new amount into the locked prediction column
- **THEN** the row is rejected and listed in the import report

### Requirement: Blind audit of Verified rows
Audit-sample rows SHALL hide the tool's outcome and confidence, and their decisions SHALL be reported separately as audit disagreement.

#### Scenario: Audit row edited
- **WHEN** a reviewer edits an audit-sample row
- **THEN** it counts toward audit disagreement and toward approval-rate denominators by outcome

### Requirement: Approval tracking
The system SHALL record for each reviewed row whether it was approved without edit, edited or rejected, with timestamps, so approval rate and review minutes can be computed.

#### Scenario: Weekly approval rate
- **WHEN** a review workbook is imported
- **THEN** outcome records exist for every decided row with decision and timestamps

### Requirement: Blind double labelling for TEST
The labelling protocol SHALL give two labellers the same 50 notes without tool output, compute agreement, send disagreements to the client owner, and allow sealing only when every disagreement is resolved.

#### Scenario: Labeller sees predictions
- **WHEN** a labelling workbook or labelling page session for TEST is created
- **THEN** it contains no prediction data
