## ADDED Requirements

### Requirement: People write TEST and VALIDATION labels
The system MUST NOT write, suggest or pre-fill a category, amount or evidence span in a TEST or VALIDATION labelling pack, and SHALL allow model suggestions only in TRAIN packs, where each suggested label SHALL be recorded as such.

#### Scenario: Request to pre-fill a TEST pack
- **WHEN** an operator asks for model suggestions in a TEST pack
- **THEN** the command refuses and explains that TEST labels are written by people

#### Scenario: Suggestion in a TRAIN pack
- **WHEN** a labeller confirms a model suggestion in a TRAIN pack
- **THEN** the label is stored with `source = model_suggestion_confirmed`

### Requirement: Labelling packs contain no tool output
TEST and VALIDATION packs SHALL contain only the note, carrier, disputed amount and taxonomy, and MUST NOT contain predictions, confidence, extractor hints or another labeller's work.

#### Scenario: File inspection
- **WHEN** the test suite reads every cell of a generated TEST pack
- **THEN** no predicted category, amount or confidence is found

### Requirement: Double labelling of 50 notes
The system SHALL give two labellers the same 50 TEST notes in separate files, drawn to include both strata, and SHALL give the other 150 notes to one labeller, with a seeded spot check of 15 for a second person.

#### Scenario: Second labeller's file
- **WHEN** labeller B opens their pack
- **THEN** it contains none of labeller A's labels

### Requirement: Label validation
The importer SHALL check that each item's category is in the taxonomy, its amount has two decimals, its evidence is verbatim in the note, a stated amount appears in its evidence, and a rate × quantity amount equals the product, and SHALL report every failure per row.

#### Scenario: Thousands written with a space
- **WHEN** a labeller enters 1277.68 with evidence "UNPAID $1 277.68"
- **THEN** the row is accepted

#### Scenario: Paraphrased evidence
- **WHEN** a labeller writes evidence "lumper fee 85" and the note says "LUMPER 85"
- **THEN** the row is rejected with `evidence_not_verbatim` and returned to the labeller

### Requirement: Agreement report
The system SHALL compute Cohen's kappa on category, exact match on amounts and item count match for the 50 double-labelled notes, and SHALL list every disagreement.

#### Scenario: Different item counts
- **WHEN** labeller A finds two items in a note and labeller B finds one
- **THEN** the note is listed as a disagreement with both sets of labels

### Requirement: Client review of all 50 notes
The system SHALL generate a review workbook with all 50 double-labelled notes and both labels, with disagreements flagged, for Jake or a PPG accountant, and the reviewer's decision SHALL become the gold label.

#### Scenario: Reviewer corrects an agreed label
- **WHEN** both labellers agree on a category and the reviewer changes it
- **THEN** the reviewer's category becomes gold and the change is recorded

### Requirement: Sealing conditions
TEST SHALL be sealed only when it has 200 distinct notes, the mix is within `split.max_stratum_gap_notes`, every label passes validation, the client review is complete, every disagreement is resolved and the taxonomy is approved or mapped to the approved version. Sealing SHALL record the hash.

#### Scenario: Review incomplete
- **WHEN** the client has reviewed 40 of the 50 notes
- **THEN** sealing fails and reports the 10 missing notes

### Requirement: Fingerprint export without labels
Sealing SHALL export the list of TEST fingerprints without labels, so that later stages can keep those notes out of tuning data.

#### Scenario: Export contents
- **WHEN** the export file is read
- **THEN** it contains fingerprints only
