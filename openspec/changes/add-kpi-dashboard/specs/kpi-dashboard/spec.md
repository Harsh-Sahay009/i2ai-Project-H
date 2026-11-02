## ADDED Requirements

### Requirement: Render from snapshots only
The dashboard SHALL be generated only from KPI snapshots and MUST NOT compute metrics itself.

#### Scenario: Missing snapshot
- **WHEN** a run has no KPI snapshot
- **THEN** the dashboard reports that the run has not been scored instead of computing values

### Requirement: Required panels
The run report SHALL show level gates with intervals, coverage in dollars and rows, errors a–g, success metrics a–e, cost per run and per row, calibration curve with AUC, approval rate with audit disagreement, loop health and open cases.

#### Scenario: Prototype review
- **WHEN** the client owner opens the D3 report
- **THEN** the Level 1 gate status and its evidence are visible on the first screen

### Requirement: Version-aware comparison
When compared snapshots differ in metric definitions, taxonomy, evaluation set or weights version, the dashboard SHALL display a banner naming the differing versions.

#### Scenario: Taxonomy v2 run
- **WHEN** a trend chart spans taxonomy v1 and v2 runs
- **THEN** a banner names both versions and the mapping used

### Requirement: Offline and confidential
The generated HTML SHALL be self-contained with no external network requests and SHALL NOT include TEST notes.

#### Scenario: Open without network
- **WHEN** the report is opened on a machine without internet
- **THEN** all charts render
