## ADDED Requirements

### Requirement: D3 acceptance check
`itemizer acceptance d3 <export>` SHALL run the pipeline end to end on the sample export, report the Level 1 gate on TEST, and write an evidence summary with the run id.

#### Scenario: Stage fails
- **WHEN** a pipeline stage fails during the check
- **THEN** the summary names the failed stage and D3 stays `open`

### Requirement: Gate status reported as written
The acceptance summary SHALL show the status, point estimate, interval and n exactly as the KPI snapshot records them, and MUST NOT show a status without its interval.

#### Scenario: Interval contains the target
- **WHEN** accuracy is 0.96 with interval 0.93–0.98 and status `pass`
- **THEN** the summary shows the accuracy condition as met, with the interval beside it

### Requirement: Client review recorded
D3 SHALL stay `open` until a record exists showing the client owner has seen the prototype, with the date and the hash of the evidence.

#### Scenario: Not yet seen
- **WHEN** the check passes but no review record exists
- **THEN** the summary shows D3 as `open` with reason `client_review_missing`

### Requirement: D4 acceptance check
`itemizer acceptance d4 <export>` SHALL run with one command on an export not used to build the tool, SHALL check `budget.max_minutes_per_run` at 1,500 rows, the `Items` and `Row Summary` sheets, and the Level 2 gate on TEST.

#### Scenario: Over the time limit
- **WHEN** a 1,500-row run takes 34 minutes
- **THEN** the check reports the timing condition as failed, with the elapsed time

#### Scenario: Synthetic new export
- **WHEN** the new export is synthetic
- **THEN** its results are labelled synthetic and are not used for accuracy

### Requirement: Client requests tracked
The system SHALL track each request to PPG, including current minutes per dispute, monthly dispute volume and confirmation of the dataset, with owner, date asked and status.

#### Scenario: Open request at report time
- **WHEN** the D5 tables are generated and the minutes-per-dispute request is still open
- **THEN** the report shows the baseline as "not provided"
