## ADDED Requirements

### Requirement: Browse outcomes
The Results Explorer SHALL list a run's rows with outcome, carrier, disputed amount, items total and delta, filterable by outcome, carrier and amount range, paginated by `ui.page_size_rows`.

#### Scenario: Discrepancies above 1,000 dollars
- **WHEN** a user filters outcome Discrepancy and disputed amount ≥ 1,000
- **THEN** only matching rows are listed with their deltas

### Requirement: Evidence highlighted in the note
For a selected row, the UI SHALL show the raw note with each item's evidence span highlighted at its stored offsets, alongside category, amount, derivation and confidence shown as configured in `ui.show_confidence_as`.

#### Scenario: Rate times quantity
- **WHEN** a row has an item derived from "2 hrs @ 75.00"
- **THEN** both factor spans are highlighted and the derived amount 150.00 is shown

### Requirement: Outcome explanation
For Review and Discrepancy rows, the UI SHALL show the outcome rule applied and the values that triggered it, from decision telemetry.

#### Scenario: Low confidence Review
- **WHEN** a user opens a Review row
- **THEN** the UI shows "row confidence 0.62 below threshold 0.80" and the threshold version

### Requirement: Workbook download from the registry
The UI SHALL serve the itemized workbook from the version registry so that the downloaded bytes match the registered hash.

#### Scenario: Download
- **WHEN** an accountant downloads a run's workbook
- **THEN** the file hash equals the registered output hash and the download is logged
