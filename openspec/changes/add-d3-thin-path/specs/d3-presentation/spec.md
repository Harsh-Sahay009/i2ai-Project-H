## ADDED Requirements

### Requirement: One page for D1, D2 and D3
`itemizer acceptance d3` SHALL write one summary showing D1 status and category count, D2 status with labelled notes and agreement, and D3 status with each Level 1 condition, its interval and n, and whether labels are provisional.

#### Scenario: Labels still provisional
- **WHEN** the summary is written before the client's review
- **THEN** every Level result is marked provisional

#### Scenario: Nothing labelled yet
- **WHEN** TEST is not frozen
- **THEN** the summary says so and shows no accuracy, instead of a guess

### Requirement: Largest disputes shown
The summary SHALL show the ten largest shipments, each counted once, with no note text.

#### Scenario: Top shipment
- **WHEN** one shipment holds a quarter of the dollars on its rows
- **THEN** the summary shows its largest dispute and the total on its rows side by side

### Requirement: Client review recorded
D3 SHALL stay `open` until `itemizer acceptance record-review` records the date and the hash of the evidence.

#### Scenario: Not yet reviewed
- **WHEN** the Level 1 conditions are met and no review is recorded
- **THEN** D3 shows `open`, with reason `client_review_missing`

#### Scenario: Reviewed on provisional labels
- **WHEN** a review is recorded and the labels are still provisional
- **THEN** D3 shows `open`, with reason `labels_provisional`, until TEST is sealed and the run is scored again

### Requirement: Only a score that belongs to the run
The summary MUST NOT show a score when the run's inputs or answers changed after it was scored, and SHALL flag an extra peek, a run from uncommitted code and negative rows left uncovered.

#### Scenario: Category definition changed at approval
- **WHEN** the client rewrites a definition after the run
- **THEN** D3 shows `open`, with reason `run_out_of_date` and what changed, and no result, while D1 can show `approved`

#### Scenario: Answers changed after scoring
- **WHEN** the run's answers differ from those it was scored on
- **THEN** D3 shows `open`, with reason `results_changed_since_scored`, and no result
