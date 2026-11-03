## ADDED Requirements

### Requirement: Four evidence channels
A candidate SHALL be promoted only when operating evidence (VALIDATION improvement with no error-type regression beyond its interval and zero invariant violations, without using TEST), reliance evidence (audit disagreement not worse, when PROD data exist), control evidence (contract and confidentiality tests pass) and recovery evidence (rollback dry run succeeds) all hold.

#### Scenario: Rollback dry run fails
- **WHEN** the rollback pointer cannot restore the previous config
- **THEN** the candidate is held and the gate reports `recovery_evidence_failed`

### Requirement: Operator approval
Publication SHALL require explicit operator approval at the gate after the evidence summary is shown.

#### Scenario: Approval declined
- **WHEN** the operator declines
- **THEN** nothing is published and the decision is logged with its reason

### Requirement: Published change record
Each published change SHALL carry owner role, evidence links (KPI snapshot ids and case ids), version, rollback pointer and validity horizon, and SHALL be written to the configuration change log and version registry.

#### Scenario: Audit months later
- **WHEN** someone asks why `confidence.review_threshold_row` is 0.83
- **THEN** the change record names the owner, the evidence snapshots, the previous value and the expiry date

### Requirement: Rollback
The operator SHALL be able to roll back any published change to its rollback pointer with one command, creating a new published change record.

#### Scenario: Regression in PROD
- **WHEN** audit disagreement rises after a change
- **THEN** `itemizer promote --rollback <change_id>` restores the previous values and logs the rollback

### Requirement: Recertification
The scheduler SHALL flag a published change for recertification when its validity horizon passes, when the model digest it was validated with changes, or when a silent-change event occurs, and SHALL re-evaluate it on VALIDATION, or on FRESH if it exists.

#### Scenario: Horizon passes
- **WHEN** a threshold's 30-day horizon passes
- **THEN** the run prints a warning, the dashboard lists it as expired and `itemizer recertify` re-evaluates it
