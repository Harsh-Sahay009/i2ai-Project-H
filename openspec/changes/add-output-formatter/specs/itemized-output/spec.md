## ADDED Requirements

### Requirement: Workbook structure
The formatter SHALL write an Excel workbook with sheets `Items`, `Row Summary`, `Run Info` and `Categories`, with one `Items` line per charge item and one `Row Summary` line per dispute row in the export.

#### Scenario: Row with no items
- **WHEN** a row has outcome `no_charge_stated`
- **THEN** it appears in `Row Summary` with zero items and does not appear in `Items`

### Requirement: Evidence shown for every item
Each `Items` line MUST show the exact evidence text from the raw note and the derivation type.

#### Scenario: Rate times quantity
- **WHEN** an item is derived from "2 hrs @ 75.00"
- **THEN** the line shows amount 150.00, derivation `rate_x_quantity` and evidence "2 hrs @ 75.00"

### Requirement: Discrepancies and reviews visible
Rows with outcome Discrepancy or Review SHALL be visually highlighted and SHALL show delta and outcome reason.

#### Scenario: Filter discrepancies
- **WHEN** an accountant filters `Row Summary` by outcome Discrepancy
- **THEN** each row shows disputed amount, items total and delta

### Requirement: Traceability to the run
The `Run Info` sheet SHALL carry the run id and manifest summary, and the output file hash SHALL be registered in the version registry.

#### Scenario: Find the run
- **WHEN** someone has only the workbook
- **THEN** the run id on `Run Info` locates the manifest with `itemizer lineage`

### Requirement: Deterministic bytes
Given identical predictions and manifest, the formatter SHALL produce byte-identical files.

#### Scenario: Rerun output
- **WHEN** a run is rerun with cache on
- **THEN** the output workbook hash is unchanged
