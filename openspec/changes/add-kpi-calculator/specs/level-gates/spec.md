## ADDED Requirements

### Requirement: Level gate evaluation
The gate evaluator SHALL compare dollar coverage and row coverage from a run on all rows, and weighted accuracy from TEST, with their intervals, against the configured `gates.level1`, `gates.level2` and `gates.level3` targets and SHALL report pass when the point estimate meets the target and fail otherwise, always showing the interval and n beside the status.

#### Scenario: Level 1 at prototype review
- **WHEN** dollar coverage is 0.83, row coverage 0.31 and accuracy 0.96 with interval 0.93–0.98
- **THEN** Level 1 is reported pass, and the accuracy interval 0.93–0.98 is shown beside it

#### Scenario: Below the target
- **WHEN** accuracy is 0.94 with interval 0.90–0.97
- **THEN** Level 1 is reported fail, even though the interval contains 0.95

### Requirement: Invariants gate every level
A level SHALL NOT pass when the run's invariant violation count is greater than zero or the evidence verifiability rate is below 100%.

#### Scenario: One edited amount
- **WHEN** one item violates the no-edit invariant
- **THEN** every level reports fail with reason `invariant_failed`

### Requirement: TEST peek budget
The gate evaluator SHALL allow at most `kpi.test_peek_budget_per_milestone` TEST evaluations per milestone, SHALL log each with build id and requester, and SHALL refuse further requests once the budget is spent.

#### Scenario: Budget exhausted
- **WHEN** a second TEST evaluation is requested with a budget of 1
- **THEN** the request is refused and the refusal is logged

### Requirement: TEST not used for promotion
The gate evaluator MUST refuse TEST evaluations requested by the Training & Calibration Pipeline, and results returned to that pipeline SHALL be VALIDATION point estimates and intervals per metric and stratum, with no per-note or per-item outcomes.

#### Scenario: Promotion request for TEST
- **WHEN** the promotion gate requests a TEST evaluation
- **THEN** the request is refused and the refusal is logged

#### Scenario: Promotion request for VALIDATION
- **WHEN** the promotion gate requests VALIDATION scores
- **THEN** the response contains no note fingerprints, items or row ids
