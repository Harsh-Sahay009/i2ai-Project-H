## ADDED Requirements

### Requirement: Workbook sheets
The workbook SHALL hold `Items`, `Charge Summary`, `Largest`, `Run Info` and `Categories` sheets, with one `Charge Summary` line per SAP BOL and description, and one `Items` line per charge item on it (ADR 0017, `add-sap-bol-output-grain`).

#### Scenario: Line with no charges
- **WHEN** a line's outcome is `no_charge_stated`
- **THEN** it appears in `Charge Summary` and not in `Items`

### Requirement: Simple IDs
`charge_id` SHALL identify a line, `row_ids` SHALL list the export rows it came from, and `shipment`, `status` and `reason_code` SHALL drop the constant `PPGTM.` prefix.

#### Scenario: Several rows on one line
- **WHEN** 8 rows share a SAP BOL and a description
- **THEN** they form one line whose `row_ids` lists all 8, and whose `shipment` is shown once

### Requirement: Evidence on every item
Each `Items` line MUST show the exact words the amount came from.

#### Scenario: Stated amount
- **WHEN** an item comes from "LUMPER $85.00"
- **THEN** the line shows amount 85.00 and evidence "LUMPER $85.00"

### Requirement: Largest disputes by SAP BOL
The `Largest` sheet SHALL list SAP BOLs by their largest dispute, counting each SAP BOL once, with its charge lines, rows, total of charges, share, cumulative share, worst outcome and main category.

#### Scenario: One dispute repeated
- **WHEN** a SAP BOL has six rows of 8,400.00 and 8,000.00 under two notes
- **THEN** it appears once with a largest dispute of 8,400.00, and the total of its two charges is shown beside it

### Requirement: Discrepancy and Review visible
Lines with outcome `discrepancy` or `review` SHALL be highlighted and SHALL show their reason.

#### Scenario: Filter
- **WHEN** an accountant filters `Charge Summary` by `discrepancy`
- **THEN** each line shows the disputed amount, items total, already paid and difference

### Requirement: Deterministic file
Identical inputs SHALL produce a byte-identical workbook.

#### Scenario: Same inputs twice
- **WHEN** the workbook is written twice from the same results
- **THEN** both files have the same hash
