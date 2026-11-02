## ADDED Requirements

### Requirement: Shared charge item schema
The system SHALL represent every charge as a `ChargeItem` with row id, item id, note fingerprint, category, amount as a two-decimal Decimal, currency, evidence text, evidence start and end offsets into the raw note, derivation type, derivation spans, confidence in [0,1] and taxonomy version.

#### Scenario: Valid item round-trips
- **WHEN** a `ChargeItem` is serialized to JSON and parsed back
- **THEN** every field, including the Decimal amount, is identical

#### Scenario: Float amount rejected
- **WHEN** an item is built with amount `12.345`
- **THEN** validation fails with a precision error

### Requirement: Row outcome set
Every row result SHALL carry exactly one outcome from `verified`, `discrepancy`, `review`, `no_charge_stated`, plus an outcome reason, row confidence and the run id that produced it.

#### Scenario: Unknown outcome rejected
- **WHEN** a row result is built with outcome `approved`
- **THEN** validation fails

### Requirement: Evidence invariant
The system MUST provide a validator that reports a violation when an item's `evidence_text` is not equal to `raw_note[evidence_start:evidence_end]` under `evidence.match_mode`, or when a `stated` amount does not appear in the evidence text, or when a `rate_x_quantity` amount does not equal the product of the numbers in its derivation spans.

#### Scenario: Paraphrased evidence
- **WHEN** an item's evidence is "detention 2 hrs" but the note says "DET 2HRS"
- **THEN** the validator returns an `evidence_not_verbatim` violation

#### Scenario: Derived amount
- **WHEN** a note says "2 hrs @ 75.00" and the item amount is 150.00 with derivation `rate_x_quantity` and spans on "2" and "75.00"
- **THEN** no violation is returned

### Requirement: No-edit invariant
The system MUST provide a validator that reports a violation when any item amount differs from the amount stated or derived from the note, regardless of whether the change would make the row reconcile.

#### Scenario: Amount nudged to reconcile
- **WHEN** a note states 140.00 and the item carries 150.00 so that the row adds up
- **THEN** the validator returns an `amount_edited` violation

### Requirement: Contract tests for stage implementations
The core package SHALL ship contract tests that any stage implementation (rules-only, local model, external model) runs against fixture notes, asserting schema validity and zero invariant violations on accepted items.

#### Scenario: New implementation plugged in
- **WHEN** a developer adds a new itemizer implementation
- **THEN** `pytest -m contract` runs the shared fixtures against it without additional test code
