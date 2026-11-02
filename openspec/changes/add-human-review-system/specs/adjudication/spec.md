## ADDED Requirements

### Requirement: Four-bucket adjudication
Every override (edit, reject or audit disagreement) SHALL be adjudicated into exactly one of AI wrong, human wrong, context changed or genuine exception, with a reason code, by an adjudicator role.

#### Scenario: Human wrong
- **WHEN** an adjudicator finds the tool's item was right and the reviewer's edit was wrong
- **THEN** the case is bucketed human wrong and is excluded from improvement inputs

### Requirement: Only eligible buckets change behaviour
Only cases adjudicated AI wrong or context changed SHALL be available to the Training & Calibration Pipeline, and only once at least `adjudication.min_cases_for_change` cases share a reason code.

#### Scenario: Single genuine exception
- **WHEN** one large dispute is adjudicated genuine exception
- **THEN** it stays visible in the exception list and no candidate change is generated

### Requirement: Case closure
A case SHALL be closed only when it has a reason code, a replay pack, an outcome link and a version tag; otherwise it SHALL remain open and listed.

#### Scenario: Missing version tag
- **WHEN** a case's run id cannot be resolved to a manifest
- **THEN** the case stays open with reason `unversioned`

### Requirement: Adjudication latency recorded
The system SHALL record the time from review export to adjudication for every case.

#### Scenario: Loop health
- **WHEN** the KPI Calculator computes triage latency
- **THEN** it uses these timestamps
