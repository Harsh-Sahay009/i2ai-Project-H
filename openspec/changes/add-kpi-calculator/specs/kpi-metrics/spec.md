## ADDED Requirements

### Requirement: Versioned metric definitions
Every metric SHALL be computed from a definition in the metric definitions version recorded in the snapshot, specifying formula, unit of analysis, valid populations, label source, matching rule, weighting, interval method and target.

#### Scenario: Definition changed
- **WHEN** the amount match tolerance in a definition changes
- **THEN** a new definitions version is required and new snapshots reference it

### Requirement: Inputs by version only
The KPI Calculator MUST read every input by hash or version tag from the version registry and MUST NOT resolve "latest" artifacts.

#### Scenario: Recompute a snapshot
- **WHEN** a KPI snapshot is recomputed six weeks later with the same versions
- **THEN** every value, interval and n is identical

### Requirement: Population separation
Each metric SHALL be computed only on populations its definition allows, and every snapshot row SHALL record its population (TRAIN, VALIDATION, TEST, FRESH or PROD).

#### Scenario: Accuracy on PROD
- **WHEN** accuracy is requested on a PROD run without gold labels
- **THEN** the calculator returns an `invalid_population` error

### Requirement: Item matching
The calculator SHALL match predicted to gold items within each row by optimal assignment, where a pair costs 0 when category matches and amounts are within tolerance, 1 when only one of category or amount matches, and 2 otherwise, and a row SHALL be correct only when all gold items match at cost 0 and no predicted item is extra.

#### Scenario: Swapped categories
- **WHEN** gold has detention 150 and lumper 85 and prediction has detention 85 and lumper 150
- **THEN** the matcher pairs by amount, records two bad classifications and the row is not correct

### Requirement: Error metrics
The calculator SHALL compute (a) category error rate with confusion matrix, (b) count error rate split into under- and over-itemized rows, (c) catch-all share of items and dollars, (d) reviewer "no fitting category" rate, (e) rerun agreement with and without cache, (f) Review share of rows and dollars plus expected calibration error, and (g) amount error rate, total absolute dollar error and invariant violation count.

#### Scenario: Invariant violation present
- **WHEN** any accepted item has an amount not found in its evidence and not a declared derivation
- **THEN** the violation count is greater than zero and the snapshot marks the run `invariant_failed`

### Requirement: Success metrics
The calculator SHALL compute (a) weighted row accuracy on covered rows, (b) cost of inference per run, per row and per covered dollar plus wall-clock minutes, (c) evidence verifiability rate and Verified share, (d) item-level and row-level ROC AUC of confidence against correctness, and (e) approval rate by outcome with audit disagreement rate; it SHALL also compute coverage in dollars and rows.

#### Scenario: AUC with one class
- **WHEN** every TEST item is correct
- **THEN** AUC is reported as undefined with n of each class rather than a number

#### Scenario: Cost recomputed under new prices
- **WHEN** a corrected price table version is published
- **THEN** recomputing cost for an old run with the new version gives a new snapshot and leaves the old one unchanged

### Requirement: Coverage definition
The calculator SHALL count a row as covered when its outcome is `verified` or `discrepancy`, or `no_charge_stated` while `review.no_charge_stated_policy` is `verified`, SHALL compute coverage from a run on all rows, and SHALL report coverage in dollars and in rows separately, with dollars shown both with and without rows flagged `repeated_invoice`.

#### Scenario: No charge stated
- **WHEN** a row has outcome `no_charge_stated` and the policy is `verified`
- **THEN** the row counts toward coverage in dollars and rows and toward the Verified share

#### Scenario: Repeated invoice
- **WHEN** a shipment's dispute appears on six rows, five of them flagged `repeated_invoice`
- **THEN** the report shows dollars with all six rows and with the flagged rows left out

### Requirement: Per-carrier views
The calculator SHALL report coverage in dollars and rows per carrier on every scored run and accuracy per carrier on TEST and VALIDATION, each with n and an interval, and SHALL flag carriers below the run's overall coverage without penalising them.

#### Scenario: Carrier with few notes
- **WHEN** a carrier has 4 TEST notes
- **THEN** its accuracy is reported with n = 4 and its interval, and is not pooled or hidden

### Requirement: Cost-driver summary
For Level 3, the calculator SHALL report disputed dollars and item counts by carrier and category from a run's items, and SHALL list the dollars of Review rows separately.

#### Scenario: Review rows in a run
- **WHEN** a run has 40 Review rows
- **THEN** their dollars appear as a separate line and are not assigned to any category

### Requirement: Weighting to the real mix
TEST accuracy SHALL be weighted by stratum shares from a versioned reference production snapshot and by each note's row frequency, and the weights version SHALL be recorded.

#### Scenario: Oversampled multi-charge notes
- **WHEN** TEST has 50% multi-charge notes but production has 20% multi-charge rows
- **THEN** multi-charge accuracy contributes 20% of the weighted accuracy

### Requirement: Accuracy by format coverage
The calculator SHALL report TEST accuracy overall and separately for notes whose format appears in TRAIN and notes whose format does not.

#### Scenario: Unseen formats
- **WHEN** 52 TEST notes have a format that does not appear in TRAIN
- **THEN** their accuracy is reported separately with n = 52

### Requirement: Sample size and intervals
Every reported value SHALL include n and a confidence interval, using Wilson intervals for unweighted proportions and a seeded stratified bootstrap for weighted accuracy, AUC and calibration error.

#### Scenario: Report row
- **WHEN** accuracy is reported
- **THEN** the snapshot row has value, ci_low, ci_high and n

### Requirement: In-sample labelling
Snapshots computed on evaluation sets drawn from data used to build the tool SHALL be marked in-sample.

#### Scenario: TEST from the 2021–2022 sample
- **WHEN** accuracy is computed on TEST drawn from the build sample
- **THEN** the snapshot is marked in-sample

### Requirement: Loop health metrics
The calculator SHALL compute triage latency, share adjudicated, time to update, review backlog and count of expired published changes from telemetry.

#### Scenario: Backlog grows
- **WHEN** queued rows exceed capacity for two consecutive weeks
- **THEN** the backlog metric shows both weeks and the trend

### Requirement: Immutable snapshots
KPI snapshots SHALL be append-only and keyed by run id, population, evaluation set version, metric definitions version, weights version, price table version and code SHA.

#### Scenario: Duplicate computation
- **WHEN** the same snapshot key is computed twice
- **THEN** the second computation verifies equality instead of writing a new row
