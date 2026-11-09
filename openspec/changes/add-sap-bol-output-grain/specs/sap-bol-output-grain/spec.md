## ADDED Requirements

### Requirement: SAP BOL and bill ID are read
The loader SHALL read `SAP BOL` and `Invoice/Bill ID` when the export has them, and an export without them MUST still load.

#### Scenario: Both columns present
- **WHEN** an export holds `SAP BOL` and `Invoice/Bill ID`
- **THEN** every row result carries its SAP BOL and its bill ID as text, with leading zeros kept

#### Scenario: Column missing
- **WHEN** an export has no `SAP BOL` column
- **THEN** it loads, lines group by shipment ID, and `Run Info` says so

### Requirement: One line per charge per SAP BOL
The workbook SHALL show one line per SAP BOL and description, and MUST NOT allocate a charge across lines or shipments. A blank SAP BOL SHALL use the shipment ID. Rows with the same SAP BOL and description but a different disputed amount SHALL stay separate lines.

#### Scenario: A repeated join
- **WHEN** one SAP BOL has 24 rows: 8 bill IDs times 3 descriptions
- **THEN** `Charge Summary` has 3 lines for it, each listing 8 rows and its 8 bill IDs

#### Scenario: Spacing differs
- **WHEN** two rows on one SAP BOL have notes that differ only in spaces or case
- **THEN** they are one line

#### Scenario: Same words on two SAP BOLs
- **WHEN** two SAP BOLs have rows with the same note
- **THEN** each SAP BOL has its own line

#### Scenario: Same key, different amount
- **WHEN** two rows share a SAP BOL and a note but not a disputed amount
- **THEN** each amount is its own line

### Requirement: A line's outcome ignores the repeat flag
A line SHALL take the outcome its rows reach by reconciling its note against its disputed amount. `repeated_invoice` MUST NOT apply to a line.

#### Scenario: Every row flagged as a repeat
- **WHEN** a line's rows all carry `repeated_invoice` and its items add up
- **THEN** the line is `verified`

#### Scenario: Does not add up
- **WHEN** a line's items do not reach its disputed amount
- **THEN** the line is `discrepancy` with `does_not_add_up`, as its rows are

### Requirement: Items keyed by SAP BOL
Each `Items` line SHALL show its charge line, SAP BOL, shipment, category, amount and the exact words the amount came from, once per charge line and not once per export row.

#### Scenario: A note with two charges on four rows
- **WHEN** four rows on one SAP BOL share a note with two charges
- **THEN** `Items` has two lines for them, each with its exact words

### Requirement: Possible double counts flagged
A line SHALL list in `same_amount_as` the other lines on its SAP BOL with the same billed and disputed amounts.

#### Scenario: Two descriptions of one amount
- **WHEN** a SAP BOL has two lines with different notes, the same billed amount and the same disputed amount
- **THEN** each names the other in `same_amount_as`, and both stay in the workbook

### Requirement: Largest disputes by SAP BOL
`Largest` SHALL list SAP BOLs by their largest dispute, counted once, with the number of charge lines, the number of rows, and the total of their distinct charges.

#### Scenario: One dispute repeated
- **WHEN** a SAP BOL has six rows: three of 8,400.00 under one note and three of 8,000.00 under another
- **THEN** it appears once, with 2 charges, 6 rows, a largest dispute of 8,400.00 and a total of charges of 16,400.00

### Requirement: Measures stay on row results
Row results, KPIs, Level gates and the TEST budget SHALL be computed as before. A run written before this change SHALL get a plain message from `evaluate`, and MUST NOT be reported as tampered with.

#### Scenario: Old run
- **WHEN** `evaluate` is given a run whose stored rows lack the SAP BOL
- **THEN** it stops with a message to run again from the cache, and spends no TEST budget
