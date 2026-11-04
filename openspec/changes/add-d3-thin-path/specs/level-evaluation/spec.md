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

### Requirement: A level needs its work
A level whose work in the scope's Table 1 is not built SHALL report `work_not_built`, whatever its numbers. The levels with their work built are fixed in the code, and MUST NOT depend on `gates` in `config/run.yaml`.

#### Scenario: Level 3
- **WHEN** a run's numbers reach Level 3's targets, and its code list and cost-driver summary do not exist
- **THEN** Level 3 reports `work_not_built`

### Requirement: Accepted without reading
The KPIs SHALL report rows and dollars an accountant can accept without reading the note, counting `verified` and `no_charge_stated`, beside coverage, which also counts rows flagged for an accountant to read.

#### Scenario: Flagged rows
- **WHEN** a row's outcome is `discrepancy`
- **THEN** it counts toward coverage, and not toward accepted without reading

### Requirement: Accuracy on labels a person has checked
The KPIs SHALL report accuracy on covered notes whose label is not a model draft, with its n and interval, unweighted because those notes are not a random sample, and SHALL report how many checked drafts people changed.

#### Scenario: Some labels checked
- **WHEN** people have checked 40 labels and changed 3
- **THEN** the figures show n of 40 or fewer, after notes in Review are left out, and 3 changed

### Requirement: Dollars with and without repeats
Coverage in dollars SHALL be reported with and without rows flagged `repeated_invoice`, and the gates SHALL use the scope's figure, which includes them.

#### Scenario: Repeated rows
- **WHEN** a covered shipment has five repeated rows
- **THEN** both figures appear in the report

### Requirement: TEST budget and aggregates only
A new run evaluated on TEST SHALL use the budget in `kpi.test_peek_budget_per_milestone` for a milestone listed in `kpi.milestones`. A charge follows what was scored: the answers, the prompt, the category list and the result-deciding settings. Scoring the same again SHALL be free, whatever the run id, because a change of code alone gives no new chance to pick a score. Different answers under one run id SHALL count as a new run. Spending past the budget SHALL need a stated reason, which is logged and flagged beside the result. Results MUST contain only aggregates.

#### Scenario: Second run on TEST
- **WHEN** a different run is evaluated at a milestone whose budget of 1 is spent
- **THEN** the request is refused and the refusal is logged

#### Scenario: Labels corrected by the client
- **WHEN** the client changes labels and the same run is evaluated again
- **THEN** the evaluation proceeds without using budget, and the status changes from provisional to sealed once TEST is sealed

#### Scenario: A change of code alone
- **WHEN** only code changed, so a new run has a new id, the same answers and the same inputs
- **THEN** scoring it is a free re-score, and the page warns of no second peek

#### Scenario: A new milestone name
- **WHEN** a second run is evaluated under a milestone not in `kpi.milestones`
- **THEN** the request is refused, so a new name cannot open a fresh budget

#### Scenario: New answers under one run id
- **WHEN** the cache is cleared, the model answers differently under the same run id, and the budget is spent
- **THEN** the request is refused as a new run

#### Scenario: An extra peek on purpose
- **WHEN** the client renames a category at approval, a new run uses the approved list, and the operator gives a reason
- **THEN** the run is scored, the reason is logged, and the status page says TEST was scored more than once

### Requirement: A score belongs to the run's own inputs
A run MUST NOT be scored when its category list, worked examples, prompt, grammar or result-deciding settings changed after it ran, when any of its notes got no answer, or when its rows do not follow from its note results and the dataset. These refusals MUST spend no TEST budget. Labels are not among these inputs, and a changed budget or concurrency does not change a run's identity.

#### Scenario: Moving a gate
- **WHEN** Level 1 failed and someone lowers its target, then evaluates the same run
- **THEN** the request is refused and nothing is charged

#### Scenario: Provider outage
- **WHEN** a run on all rows has notes in Review with `provider_unavailable`
- **THEN** the request is refused and nothing is charged, and a repeat run recovers the notes with the same run id

#### Scenario: Changed row file
- **WHEN** `row_results.json` has a changed outcome, a removed row or a changed amount
- **THEN** the request is refused and nothing is charged

#### Scenario: A commit that changes nothing
- **WHEN** only documents are committed between two runs with the same inputs
- **THEN** the run id and the workbook hash are unchanged, and the manifest records the new commit

### Requirement: Provisional freeze
Because D1, D2 and D3 are presented together, TEST SHALL be freezable on team-resolved labels before the client's review. Results on it MUST be labelled provisional, and final sealing SHALL still need the client's review and approved categories.

#### Scenario: Before the client's review
- **WHEN** a team member resolves disagreements and runs `gt seal --provisional`
- **THEN** a run on all rows is allowed, and every Level result is labelled provisional

#### Scenario: Final seal
- **WHEN** the client has reviewed all 50 notes and approved the categories
- **THEN** `gt seal` succeeds after the provisional freeze and the reserve is released
