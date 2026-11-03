## ADDED Requirements

### Requirement: Eligible case mining
The pipeline SHALL mine only closed cases adjudicated AI wrong or context changed, grouped by reason code, with at least `adjudication.min_cases_for_change` cases per group, and MUST exclude rows flagged with a TEST or VALIDATION fingerprint.

#### Scenario: Test fingerprint in PROD case
- **WHEN** a closed PROD case's note matches a TEST fingerprint
- **THEN** it is excluded from mining and the exclusion is logged

### Requirement: No TEST label access
The pipeline MUST NOT read TEST labels and MUST NOT request TEST evaluations.

#### Scenario: Direct read attempt
- **WHEN** the calibrator requests the TEST evaluation set
- **THEN** the version registry denies the request

### Requirement: Candidates built from TRAIN
Lexicon additions, few-shot swaps and prompt edits SHALL be built from TRAIN notes and eligible PROD cases only.

#### Scenario: Few-shot swap from VALIDATION
- **WHEN** a `fewshot_swap` candidate uses a VALIDATION note
- **THEN** the candidate is rejected and the note's fingerprint is named

### Requirement: Versioned candidate changes
Each candidate SHALL be a versioned change set of one or more of lexicon addition, few-shot swap, prompt edit, threshold update or calibration refit, with links to the contributing case ids, and taxonomy changes SHALL be emitted as change requests requiring client approval.

#### Scenario: New abbreviation
- **WHEN** four AI-wrong cases share reason `wrong_amount` caused by "LMPR" not being recognised
- **THEN** a `lexicon_add` candidate maps "LMPR" to lumper and lists the four cases

### Requirement: Calibration on VALIDATION
The calibrator SHALL fit the confidence calibration map and Review thresholds on VALIDATION only, choosing the lowest row threshold that achieves the target Verified-row precision on VALIDATION, and SHALL record the VALIDATION version used.

#### Scenario: Refit after taxonomy change
- **WHEN** a new taxonomy version is approved
- **THEN** the calibration map is refit on VALIDATION relabelled under the new version and published as a new version

### Requirement: Replay before promotion
Every candidate SHALL be replayed against the current build on the contributing replay packs and TRAIN, producing a row-level diff, and on the full VALIDATION set, producing error-type deltas only.

#### Scenario: Fix breaks other rows
- **WHEN** a prompt edit fixes the target cases but adds three wrong counts on VALIDATION
- **THEN** the replay report shows the regression and the candidate is not sent to the gate unless the operator overrides with a reason
