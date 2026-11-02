## ADDED Requirements

### Requirement: Three telemetry layers
The store SHALL keep action events, decision records and outcome records in separate append-only tables, each carrying run id and, where applicable, case id.

#### Scenario: Reconstruct a row
- **WHEN** an analyst queries a case id
- **THEN** the store returns the route and cost (action), the decision path (decision) and any review result (outcome)

### Requirement: Stable case linkage
Every decision and outcome record SHALL reference a case id equal to (run id, row id), and outcome records SHALL be rejected when their case id does not exist.

#### Scenario: Review for unknown run
- **WHEN** a review workbook references a run id not in the store
- **THEN** import fails for those rows and reports them

### Requirement: Append-only records
The store MUST NOT update or delete telemetry rows; corrections SHALL be new records referencing the corrected record.

#### Scenario: Reviewer changes mind
- **WHEN** a reviewer re-submits a different decision for the same case
- **THEN** both records are kept and the latest is marked current

### Requirement: Experience test
The store SHALL expose, per case, whether it is adjudicated, outcome-linked and versioned, and SHALL report only cases with all three as experience.

#### Scenario: Missing replay pack
- **WHEN** a case is adjudicated but has no replay pack
- **THEN** it is not counted as experience and stays open

### Requirement: No personal data
Telemetry MUST NOT store note text or person names; notes SHALL be referenced by fingerprint and reviewers by role and pseudonymous id.

#### Scenario: Schema check
- **WHEN** a write includes a free-text field longer than the configured limit outside the allowed fields
- **THEN** the write is rejected
