## ADDED Requirements

### Requirement: Every measure from a KPI snapshot
The report SHALL present every measure in scope section 3, including coverage in dollars and rows, accuracy and Level status, plus errors a–g and success a–e, each with its sample size and interval, and SHALL cite the KPI snapshot id of each.

#### Scenario: Missing measure
- **WHEN** a required measure has no KPI snapshot
- **THEN** generation fails and names the measure

### Requirement: Honest labels
The report SHALL state that results are in-sample when no FRESH data exists, SHALL label synthetic numbers as synthetic, SHALL give the number of TEST evaluations and VALIDATION comparisons, and SHALL list the known biases in `architecture/docs/04-kpi-calculator.md`.

#### Scenario: No FRESH data
- **WHEN** only the anonymized dataset was used
- **THEN** every accuracy table carries the label "in-sample"

### Requirement: Error examples
The report SHALL show error examples, drawn from TRAIN by default and from TEST only when `ui.test_error_examples_released` is true.

#### Scenario: Before the final freeze
- **WHEN** the report is generated before TEST examples are released
- **THEN** its examples come from TRAIN and say so

### Requirement: Rerun from the report alone
The report SHALL give the exact commands, code tag, lockfile hash, configuration, dataset source and hash, and model identity needed to rerun the tool, with a separate path on published synthetic data for a reader without the dataset.

#### Scenario: Reader with the dataset
- **WHEN** a reader outside the team follows the report with the dataset and response cache
- **THEN** the rerun reproduces the reported KPI values

#### Scenario: Reader without the dataset
- **WHEN** a reader outside the team follows the synthetic path
- **THEN** the rerun matches the published synthetic results, and the report states that this does not reproduce the accuracy numbers

### Requirement: Report length
The finished report SHALL be 8 to 12 pages, and the build SHALL warn when the rendered length is outside that range.

#### Scenario: Too long
- **WHEN** the rendered report is 15 pages
- **THEN** the build warns and reports the page count
