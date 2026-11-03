## ADDED Requirements

### Requirement: Locked test set composition
The TEST set SHALL contain 200 distinct note fingerprints, half single-charge and half multi-charge or large disputes within `split.max_stratum_gap_notes`, sampled with a recorded seed, each with gold items (category, amount, evidence span) and stratum.

#### Scenario: Duplicate note
- **WHEN** two sampled rows share a fingerprint
- **THEN** only one note enters the TEST set and its row frequency is recorded

### Requirement: Blind double labelling provenance
For the 50 double-labelled notes, the store SHALL keep both labellers' raw labels, the agreement statistics and the client reviewer's review of all 50 notes, including the resolution of every disagreement.

#### Scenario: Unresolved disagreement
- **WHEN** a disagreement has no resolution
- **THEN** the TEST set cannot be sealed

#### Scenario: Client review incomplete
- **WHEN** the client reviewer has reviewed 40 of the 50 notes
- **THEN** the TEST set cannot be sealed

### Requirement: Sealing
A sealed evaluation set SHALL be immutable, registered with its hash, and readable only by the KPI Calculator role.

#### Scenario: Edit after sealing
- **WHEN** someone corrects a gold label in a sealed TEST version
- **THEN** a new version must be created, and KPI snapshots record which version they used

### Requirement: Train, validation and test split
The system SHALL keep TRAIN, VALIDATION and TEST as separate sets drawn from one dataset file, assigned by distinct note using `split.seed` and `split.validation_share`, and SHALL record the assignment of every note in a versioned split manifest.

#### Scenario: Repeated note
- **WHEN** many rows share one note
- **THEN** all of those rows belong to the same set

### Requirement: Allowed use per set
Lexicon entries, few-shot examples and prompt examples SHALL come from TRAIN only; calibration, thresholds and candidate comparison SHALL use VALIDATION; TEST SHALL be used only for Level gates; and a run on all rows SHALL happen only at a Level gate, after TEST is sealed.

#### Scenario: Few-shot example from VALIDATION
- **WHEN** a few-shot set contains a fingerprint assigned to VALIDATION
- **THEN** publication fails naming the fingerprint

### Requirement: People write VALIDATION and TEST labels
VALIDATION, TEST and FRESH labels MUST be written by people without seeing tool output; TRAIN labels MAY start from model suggestions, and each such label SHALL record that it did.

#### Scenario: TRAIN label from a suggestion
- **WHEN** a labeller accepts a model suggestion for a TRAIN note
- **THEN** the label is stored with `source = model_suggestion_confirmed`

### Requirement: Disjointness
TRAIN, VALIDATION, TEST and FRESH SHALL share no note fingerprint, and the check SHALL run whenever any set or few-shot version is published.

#### Scenario: Leaked few-shot example
- **WHEN** a few-shot set contains a fingerprint present in TEST
- **THEN** publication fails naming the fingerprint

### Requirement: In-sample labelling
Every evaluation set SHALL record whether its notes come from data used to build the tool, and KPI outputs on such sets SHALL be labelled in-sample.

#### Scenario: No FRESH data
- **WHEN** only the anonymized dataset is available
- **THEN** accuracy is reported with the label "in-sample"
