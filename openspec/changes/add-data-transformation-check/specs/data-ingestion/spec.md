## ADDED Requirements

### Requirement: Input contract validation
The system SHALL validate each export against the input contract and SHALL stop with exit code 3 and a data-quality report when a required column is missing or an amount cannot be parsed.

#### Scenario: Missing note column
- **WHEN** the export has no note column under any configured alias
- **THEN** ingestion stops and the report names the missing column

#### Scenario: Duplicate invoice
- **WHEN** two rows share the same invoice key
- **THEN** both rows are kept, flagged `repeated_invoice`, and counted in the report

### Requirement: Row id from export position
The system SHALL give every row a `row_id` from its position in the export, because no combination of ID columns identifies a row, and SHALL keep the original ID columns alongside it.

#### Scenario: Same shipment on several rows
- **WHEN** one shipment appears on 24 rows
- **THEN** each row has its own `row_id` and all 24 keep the same shipment id

### Requirement: Rows with unusual amounts kept and flagged
The system SHALL keep rows whose disputed amount is zero or negative, SHALL flag them `non_positive_delta`, and SHALL count them in the data-quality report.

#### Scenario: Negative delta
- **WHEN** a row's billed charge is below its estimated charge
- **THEN** the row is kept, flagged and counted

### Requirement: Pre-check without side effects
The system SHALL offer a pre-check of an uploaded export against the input contract that returns the data-quality report without creating a snapshot or starting a run.

#### Scenario: Upload pre-check
- **WHEN** the Web UI pre-checks an upload with two duplicate invoices
- **THEN** the report lists both warnings and no snapshot is registered

### Requirement: Raw text preservation
The system MUST keep each raw note byte-for-byte in the snapshot alongside any normalized form.

#### Scenario: Odd encoding
- **WHEN** a note contains non-breaking spaces and smart quotes
- **THEN** the raw column keeps them and only the normalized column replaces them

### Requirement: Note deduplication with row frequency
The system SHALL compute a fingerprint per note, itemize each distinct fingerprint once, and record for every fingerprint the rows that share it.

#### Scenario: Repeated note
- **WHEN** 37 rows share the same note
- **THEN** one distinct note is passed to the classifier and its result is fanned out to all 37 rows

### Requirement: TEST and VALIDATION exclusion from tuning data
The system SHALL mark rows whose fingerprint belongs to TEST or VALIDATION so that they are never exported to TRAIN or to few-shot or lexicon candidates, and rows marked TEST SHALL also stay out of calibration data.

#### Scenario: Test note in weekly export
- **WHEN** a production row's note matches a TEST fingerprint
- **THEN** the row is itemized normally but flagged `test_fingerprint` and excluded from tuning exports

### Requirement: Dataset class recorded
The system SHALL record `data.dataset_class` on every snapshot, and SHALL pass note text unchanged to later stages.

#### Scenario: Anonymized dataset
- **WHEN** an export is ingested with `data.dataset_class` set to `open_anonymized`
- **THEN** the snapshot records that class and its evidence offsets refer to the note text as ingested

### Requirement: Snapshot registration
The system SHALL write raw and normalized tables as Parquet, register them in the version registry with the transform code SHA, and pass only the snapshot id downstream.

#### Scenario: Same export reprocessed
- **WHEN** the same export is ingested again with the same code
- **THEN** the snapshot hash is identical
