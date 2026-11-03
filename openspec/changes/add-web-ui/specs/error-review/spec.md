## ADDED Requirements

### Requirement: Error-typed rows for TRAIN and PROD
The Error Review Workbench SHALL show rows grouped by error type (bad classification, wrong count under/over, not enough categories, irreproducible, low confidence, wrong amount, invariant violation) for TRAIN runs and for reviewed PROD rows, using only the error-typed records written by the KPI Calculator.

#### Scenario: Wrong amounts on TRAIN
- **WHEN** an operator selects error type wrong amount for a TRAIN run
- **THEN** each row shows predicted and gold items side by side with evidence highlighted

### Requirement: VALIDATION stays aggregate
For VALIDATION, the workbench SHALL show only aggregate metrics with intervals and MUST NOT show note text, items or row identifiers.

#### Scenario: Errors on VALIDATION
- **WHEN** an operator opens VALIDATION errors
- **THEN** only counts, rates and intervals per error type are shown

### Requirement: TEST stays aggregate
For TEST, the workbench SHALL show only aggregate metrics with intervals and MUST NOT show note text, items or row identifiers unless `ui.test_error_examples_released` is true.

#### Scenario: Before final freeze
- **WHEN** an operator opens TEST errors before release
- **THEN** only counts, rates and intervals per error type are shown

#### Scenario: After release for D5
- **WHEN** release is approved after the final freeze
- **THEN** TEST error examples are visible and each view is recorded in the audit log

### Requirement: Run comparison
The workbench SHALL compare two runs on the same evaluation set, row by row on TRAIN and PROD and by error type on VALIDATION, and SHALL show a version banner when their metric definitions, taxonomy or weights versions differ.

#### Scenario: Candidate vs current on TRAIN
- **WHEN** an operator compares a candidate replay with the current build on TRAIN
- **THEN** rows that changed outcome or error type are listed first

#### Scenario: Candidate vs current on VALIDATION
- **WHEN** an operator compares a candidate replay with the current build on VALIDATION
- **THEN** only changes in counts and rates per error type are shown
