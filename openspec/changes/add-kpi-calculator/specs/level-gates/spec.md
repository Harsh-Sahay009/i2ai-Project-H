## ADDED Requirements

### Requirement: Level gate evaluation
The gate evaluator SHALL compare dollar coverage, row coverage and weighted accuracy with their intervals against the configured `gates.level1`, `gates.level2` and `gates.level3` targets and SHALL report pass when the point estimate meets the target, inconclusive when the interval contains the target, and fail otherwise.

#### Scenario: Level 1 at prototype review
- **WHEN** dollar coverage is 0.83, row coverage 0.31 and accuracy 0.96 with interval 0.93–0.98
- **THEN** Level 1 is reported pass for coverage and inconclusive for accuracy

### Requirement: Invariants gate every level
A level SHALL NOT pass when the run's invariant violation count is greater than zero or the evidence verifiability rate is below 100%.

#### Scenario: One edited amount
- **WHEN** one item violates the no-edit invariant
- **THEN** every level reports fail with reason `invariant_failed`

### Requirement: TEST peek budget
The gate evaluator SHALL allow at most `kpi.test_peek_budget_per_milestone` TEST evaluations per milestone, SHALL log each with candidate id and requester, and SHALL refuse further requests once the budget is spent.

#### Scenario: Budget exhausted
- **WHEN** a sixth TEST evaluation is requested with a budget of 5
- **THEN** the request is refused and the refusal is logged

### Requirement: Aggregate-only results for promotion
Results returned to the Training & Calibration Pipeline SHALL contain only gate status, point estimates and intervals per metric and stratum, and MUST NOT contain per-note or per-item outcomes.

#### Scenario: Promotion request
- **WHEN** the promotion gate requests a TEST evaluation
- **THEN** the response contains no note fingerprints, items or row ids
