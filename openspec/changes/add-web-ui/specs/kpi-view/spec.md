## ADDED Requirements

### Requirement: Render KPI snapshots only
The KPI View SHALL render KPI snapshots using the panels shared with the KPI Dashboard and MUST NOT compute any metric.

#### Scenario: Run not scored
- **WHEN** a user opens a run with no KPI snapshot
- **THEN** the page says the run has not been scored and shows no values

### Requirement: Level gates with intervals
The KPI View SHALL show each Level gate's status together with its point estimate, interval and n, exactly as the KPI Calculator wrote them.

#### Scenario: Interval contains the target
- **WHEN** a snapshot reports accuracy 0.96 with interval 0.93–0.98 and status `pass`
- **THEN** the page shows the status, the value, the interval and n together

### Requirement: Guardrail comparison panel
When a guardrail ablation snapshot exists, the KPI View SHALL show the with-and-without comparison and SHALL label it synthetic.

#### Scenario: Ablation results available
- **WHEN** a user opens the guardrail panel
- **THEN** the results for each profile appear with a "synthetic" label

### Requirement: HTML report download
The KPI View SHALL offer the static HTML report for the run, served from the version registry.

#### Scenario: Offline reading
- **WHEN** a client owner downloads the report
- **THEN** the file opens with no network connection and shows the same panels
