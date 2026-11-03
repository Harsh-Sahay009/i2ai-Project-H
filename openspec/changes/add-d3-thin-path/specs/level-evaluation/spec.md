## ADDED Requirements

### Requirement: Where each number comes from
Coverage SHALL come from a run on all rows and accuracy from TEST, using covered notes only, weighted back to the real mix of rows.

#### Scenario: Oversampled large disputes
- **WHEN** TEST has 25% large notes and the dataset has 10% large rows
- **THEN** large notes contribute 10% of the weighted accuracy

### Requirement: Item matching
A note SHALL be correct only when every gold item matches a predicted item on category and amount and no predicted item is extra.

#### Scenario: Swapped categories
- **WHEN** gold has detention 150.00 and lumper 85.00, and the prediction has detention 85.00 and lumper 150.00
- **THEN** the note is not correct and two category errors are counted

### Requirement: Level met on the measured value
A level SHALL pass when every measured value reaches its target and invariant violations are zero, and the report MUST show each value's interval and n beside it.

#### Scenario: Interval contains the target
- **WHEN** dollar coverage is 0.83, row coverage 0.31 and accuracy 0.96 with interval 0.93–0.98
- **THEN** Level 1 passes, and the interval is shown

#### Scenario: Below the target
- **WHEN** accuracy is 0.94
- **THEN** Level 1 fails

#### Scenario: Invariant broken
- **WHEN** one accepted item's evidence is not verbatim
- **THEN** every level fails with reason `invariant_failed`

### Requirement: Dollars with and without repeats
Coverage in dollars SHALL be reported with and without rows flagged `repeated_invoice`, and the gates SHALL use the scope's figure, which includes them.

#### Scenario: Repeated rows
- **WHEN** a covered shipment has five repeated rows
- **THEN** both figures appear in the report

### Requirement: TEST budget and aggregates only
A new run evaluated on TEST SHALL use the budget in `kpi.test_peek_budget_per_milestone`, and re-scoring the same run SHALL be free. Results MUST contain only aggregates.

#### Scenario: Second run on TEST
- **WHEN** a different run is evaluated at a milestone whose budget of 1 is spent
- **THEN** the request is refused and the refusal is logged

#### Scenario: Labels corrected by the client
- **WHEN** the client changes labels and the same run is evaluated again
- **THEN** the evaluation proceeds without using budget, and the status changes from provisional to sealed once TEST is sealed

### Requirement: Provisional freeze
Because D1, D2 and D3 are presented together, TEST SHALL be freezable on team-resolved labels before the client's review. Results on it MUST be labelled provisional, and final sealing SHALL still need the client's review and approved categories.

#### Scenario: Before the client's review
- **WHEN** a team member resolves disagreements and runs `gt seal --provisional`
- **THEN** a run on all rows is allowed, and every Level result is labelled provisional

#### Scenario: Final seal
- **WHEN** the client has reviewed all 50 notes and approved the categories
- **THEN** `gt seal` succeeds after the provisional freeze and the reserve is released
