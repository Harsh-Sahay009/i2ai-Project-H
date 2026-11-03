## ADDED Requirements

### Requirement: Workbook sheets
The workbook SHALL hold `Items`, `Row Summary`, `Largest`, `Run Info` and `Categories` sheets, with one `Items` line per charge per row and one `Row Summary` line per row.

#### Scenario: Row with no charges
- **WHEN** a row's outcome is `no_charge_stated`
- **THEN** it appears in `Row Summary` and not in `Items`

### Requirement: Simple IDs
`row_id` SHALL identify a row, and `shipment`, `status` and `reason_code` SHALL drop the constant `PPGTM.` prefix.

#### Scenario: Several rows on one shipment
- **WHEN** a shipment has 24 rows
- **THEN** each has its own `row_id`, and all show the same `shipment`

### Requirement: Evidence on every item
Each `Items` line MUST show the exact words the amount came from.

#### Scenario: Stated amount
- **WHEN** an item comes from "LUMPER $85.00"
- **THEN** the line shows amount 85.00 and evidence "LUMPER $85.00"

### Requirement: Largest disputes by shipment
The `Largest` sheet SHALL list shipments by their largest dispute, counting each shipment once, with the rows, repeated rows, total on rows, share, cumulative share, worst outcome and main category.

#### Scenario: One dispute repeated
- **WHEN** a shipment has six rows of 8,400.00 and 8,000.00, five of them repeated
- **THEN** it appears once with a largest dispute of 8,400.00, and the total on rows is shown beside it

### Requirement: Discrepancy and Review visible
Rows with outcome `discrepancy` or `review` SHALL be highlighted and SHALL show their reason.

#### Scenario: Filter
- **WHEN** an accountant filters `Row Summary` by `discrepancy`
- **THEN** each row shows the disputed amount, items total, already paid and difference

### Requirement: Deterministic file
Identical inputs SHALL produce a byte-identical workbook.

#### Scenario: Same inputs twice
- **WHEN** the workbook is written twice from the same results
- **THEN** both files have the same hash
