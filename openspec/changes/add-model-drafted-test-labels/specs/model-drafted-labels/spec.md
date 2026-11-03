## ADDED Requirements

### Requirement: A model drafts TEST labels only when asked to
`itemizer gt draft-test-labels --send` SHALL have the models named in `config/models.yaml` label the TEST packs, spending at most `budget.max_usd_per_run` across the whole job. Without `--send` it MUST send nothing. It MUST NOT label VALIDATION.

#### Scenario: Dry run
- **WHEN** an operator runs the command without `--send`
- **THEN** it reports the notes per pack and makes no model call

#### Scenario: Budget reached
- **WHEN** `budget.max_usd_per_run` is reached partway through
- **THEN** the remaining notes stay unlabelled, the freeze stops, and a repeat continues from the cache

### Requirement: A model's label passes a person's checks
A model's answer SHALL go through the same import and checks as a person's workbook, and the labeller MUST NOT receive tool output or worked examples. A note with no valid answer MUST stay unlabelled, and MUST NOT get an invented label.

#### Scenario: No tool output in the prompt
- **WHEN** a run on TRAIN exists and labels are drafted
- **THEN** the labeller's requests hold only the labelling rules, the category list, the note and its disputed amount

#### Scenario: A note the model will not label
- **WHEN** the model refuses a note
- **THEN** the note is reported as not labelled, and `gt seal --provisional` stops until it has a label

### Requirement: Drafts are marked wherever they count
Each drafted label MUST be stored with `source = model_draft`. The freeze record's counts, the KPI snapshot and the status page SHALL say how many TEST labels are drafts, and the page SHALL say that accuracy against them shows agreement and not correctness.

#### Scenario: Level result on drafts
- **WHEN** a run is scored on labels that are model drafts
- **THEN** the snapshot's `labels_sources` counts them, and the page flags them beside the Level result

#### Scenario: A first read of the status page
- **WHEN** TEST is frozen on drafts
- **THEN** D2 shows the number written by a model and the number checked by a person

### Requirement: A draft cannot be final
`gt seal` MUST refuse while any TEST label is an unchecked model draft. Accepting a draft in the client's review SHALL count as a person's check.

#### Scenario: Final seal with drafts left
- **WHEN** the client has reviewed the 50 notes and approved the categories, and 150 labels are still drafts
- **THEN** `gt seal` refuses and gives the count

#### Scenario: Everything checked
- **WHEN** every draft has been checked by a person
- **THEN** `gt seal` succeeds
