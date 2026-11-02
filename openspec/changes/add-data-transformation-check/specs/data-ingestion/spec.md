## ADDED Requirements

### Requirement: Input contract validation
The system SHALL validate each export against the input contract and SHALL stop with exit code 3 and a data-quality report when a required column is missing or an amount cannot be parsed.

#### Scenario: Missing note column
- **WHEN** the export has no note column under any configured alias
- **THEN** ingestion stops and the report names the missing column

#### Scenario: Duplicate invoice
- **WHEN** two rows share the same invoice key
- **THEN** both rows are kept, flagged `repeated_invoice`, and counted in the report

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

### Requirement: Test-set exclusion for tuning data
The system SHALL mark rows whose fingerprint belongs to the sealed TEST set so that they are never exported to DEV, few-shot candidates or calibration data.

#### Scenario: Test note in weekly export
- **WHEN** a production row's note matches a TEST fingerprint
- **THEN** the row is itemized normally but flagged `test_fingerprint` and excluded from tuning exports

### Requirement: Confidentiality masking
The system SHALL produce masked note text with stable placeholders for person names, phone numbers and emails, SHALL store the reversal map only on team storage, and SHALL provide offsets mapping masked text back to the raw note.

#### Scenario: Driver name in note
- **WHEN** a note says "per driver John Smith 2hrs det"
- **THEN** masked text reads "per driver ⟨PERSON_1⟩ 2hrs det" and evidence offsets still resolve to the raw note

### Requirement: Snapshot registration
The system SHALL write raw and normalized tables as Parquet, register them in the version registry with the transform code SHA, and pass only the snapshot id downstream.

#### Scenario: Same export reprocessed
- **WHEN** the same export is ingested again with the same code
- **THEN** the snapshot hash is identical
