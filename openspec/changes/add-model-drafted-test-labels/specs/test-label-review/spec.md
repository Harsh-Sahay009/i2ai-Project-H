## ADDED Requirements

### Requirement: A review workbook for every TEST label
`itemizer gt label-review-pack` SHALL write the current label of every TEST note to a workbook, with the notes most in need of a person first, and MUST NOT include tool output.

#### Scenario: What comes first
- **WHEN** the labellers disagreed on a note, or the model marked it as doubtful
- **THEN** it comes before notes with neither, and its `priority` says why

#### Scenario: No tool output
- **WHEN** a run on all rows exists
- **THEN** the workbook still shows only the note and its label

### Requirement: Checks and corrections through one command
`itemizer gt import-label-review` SHALL accept a reviewed workbook. A note marked `checked` or whose label changed SHALL become `person_checked` or `person_corrected`, with the reviewer recorded. A partial review SHALL be allowed, and a later import SHALL add to it.

#### Scenario: Changed without the flag
- **WHEN** a reviewer changes an amount and forgets to mark the note `checked`
- **THEN** the change is taken, and the note is `person_corrected`

#### Scenario: Invalid correction
- **WHEN** a corrected amount is not in the evidence
- **THEN** the whole file is rejected, each failure is listed by row, and no label changes

#### Scenario: Note the client decided
- **WHEN** a reviewer changes a note the client's review already decided
- **THEN** the file is rejected, because the client's decision stands

#### Scenario: Team correction on a note the client will review
- **WHEN** the team corrects one of the 50 double-labelled notes and the client's workbook is written
- **THEN** it shows the correction, and `accept_correction` keeps it

#### Scenario: After the final seal
- **WHEN** TEST is sealed
- **THEN** the command refuses

### Requirement: Correcting a frozen test set
A correction after a provisional freeze SHALL update the frozen labels and their record, count the corrections made after the freeze, and leave results labelled provisional. It MUST NOT take a client review into the frozen labels before the final seal.

#### Scenario: Correction after the freeze
- **WHEN** a reviewer corrects a label after `gt seal --provisional`
- **THEN** `load_test_gold` returns the corrected label, and the record's `corrected_after_freeze` goes up

### Requirement: Running the test again
After labels change, scoring the same run SHALL use no model calls and no TEST budget, and SHALL report the new labels' hash. The instruction file `deliverables/reviewing_test_labels.md` SHALL explain the review, the rule on not opening run folders, and when a new run is needed.

#### Scenario: Labels corrected, then re-scored
- **WHEN** a label is corrected and `itemizer evaluate` is run on the same run
- **THEN** no model is called, the budget event is `rescored`, and the accuracy reflects the correction
