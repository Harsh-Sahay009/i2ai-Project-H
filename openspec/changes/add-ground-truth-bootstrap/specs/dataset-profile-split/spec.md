## ADDED Requirements

### Requirement: Dataset profile
The system SHALL report the rows, distinct notes, note formats, carriers, date range, disputed dollars, repeated-invoice rows and catch-all reason code share of the dataset, next to the figures in the scope statement.

#### Scenario: Dataset differs from the scope
- **WHEN** the dataset has a different row count from the scope's 1,347 rows
- **THEN** the report shows both values and flags the difference

### Requirement: Anonymization scan
The system SHALL scan note text for phone numbers, emails and person names, SHALL report the counts and note fingerprints, and MUST block external sends until the operator records a decision on any findings.

#### Scenario: Email found
- **WHEN** the scan finds an email address in a note
- **THEN** `gt draft-taxonomy` refuses to send text until the operator's decision is recorded

### Requirement: Split by distinct note
The system SHALL assign every distinct normalized note to exactly one of TEST, TRAIN and VALIDATION using `split.seed` and `split.validation_share`, stratified by provisional stratum and by how often the note repeats.

#### Scenario: Repeated note
- **WHEN** 37 rows share one note
- **THEN** all 37 rows belong to the same set

#### Scenario: Same format with different numbers
- **WHEN** two notes read "DET 2HRS @75" and "DET 3HRS @75"
- **THEN** they may be assigned to different sets, and each TEST note records whether its format appears in TRAIN

#### Scenario: Same seed
- **WHEN** the split runs twice on the same dataset with the same seed
- **THEN** both split manifests are identical

### Requirement: Already-labelled notes go to TRAIN
Notes the team has already labelled by hand, including those in the example output sheet, and notes quoted as D1 examples, MUST be assigned to TRAIN.

#### Scenario: Example sheet
- **WHEN** a note in the example sheet is drawn for TEST
- **THEN** it is assigned to TRAIN instead and another note is drawn

### Requirement: Notes read while drafting stay out of TEST
Every note placed in a draft prompt MUST be recorded and MUST NOT enter TEST or RESERVE in any later split, and it MAY go to TRAIN or VALIDATION.

#### Scenario: Split redone after a draft
- **WHEN** the split is redone after the draft prompt was written
- **THEN** no note in that prompt is in TEST or RESERVE

### Requirement: TEST drawn first with a reserve
The system SHALL draw TEST before assigning any other note, as 100 single-charge notes, `split.test_large_notes` large-dispute notes and multi-charge notes for the rest of the 200, plus `split.test_reserve_notes` reserve notes.

#### Scenario: TEST mix
- **WHEN** the split runs with `split.test_large_notes` set to 50
- **THEN** TEST holds 100 single-charge, 50 multi-charge and 50 large-dispute notes by provisional stratum

### Requirement: Unused reserve released after sealing
After TEST is sealed, the system SHALL assign unused reserve notes to TRAIN and VALIDATION using `split.validation_share`, and reserve notes MUST NOT be used for anything before then.

#### Scenario: Taxonomy draft before sealing
- **WHEN** the taxonomy draft samples TRAIN notes before TEST is sealed
- **THEN** no reserve note is included

### Requirement: Final strata from gold items
The system SHALL replace provisional strata with strata from the gold items after labelling, and SHALL list replacement notes from the reserve when single-charge and other notes differ from 100 each by more than `split.max_stratum_gap_notes`.

#### Scenario: Mix off after labelling
- **WHEN** gold items show 130 single-charge notes and 70 multi-charge or large notes, and the limit is 10
- **THEN** the tool lists 20 notes to replace and the replacements to label from the reserve

### Requirement: Split manifest
The system SHALL write a split manifest with the seed, the parameters and the set assigned to every note, and SHALL fail if any note fingerprint appears in two sets.

#### Scenario: Note in two sets
- **WHEN** a note fingerprint appears in both TRAIN and TEST
- **THEN** the split fails and names the fingerprint
