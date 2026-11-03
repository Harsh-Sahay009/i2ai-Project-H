## ADDED Requirements

### Requirement: Content-addressed immutable storage
The registry SHALL store each data artifact under the SHA-256 of its canonical bytes and MUST reject any write that would change bytes under an existing hash.

#### Scenario: Same file twice
- **WHEN** the same export is registered twice
- **THEN** one object exists and both registrations return the same hash

#### Scenario: Overwrite attempt
- **WHEN** code attempts to write different bytes to an existing hash path
- **THEN** the write fails with `immutable_violation`

### Requirement: Lineage
Every registered artifact SHALL record its kind, parents and producing run id, and the registry SHALL answer the full ancestry of any artifact.

#### Scenario: Trace a KPI
- **WHEN** an operator runs `itemizer lineage <kpi_snapshot_id>`
- **THEN** the output lists the run manifest, input snapshot, raw export, taxonomy, prompt, lexicon, config hash, evaluation set and metric definitions versions

### Requirement: Git-tagged artifacts captured
The registry SHALL register taxonomy, prompt, few-shot, lexicon, metric definitions and price table versions by tag, commit and content hash, and SHALL store their bytes in the CAS.

#### Scenario: Tag moved
- **WHEN** a Git tag `lexicon@v4` is re-pointed to a different commit
- **THEN** registration fails because the content hash differs from the registered one

### Requirement: Sealed evaluation sets
Evaluation sets marked sealed SHALL be readable only by callers with the `kpi_calculator` role, and every read SHALL be logged with caller and purpose.

#### Scenario: Training pipeline reads TEST
- **WHEN** the Training & Calibration Pipeline requests the sealed TEST labels
- **THEN** the request is denied and an access-denied event is logged

### Requirement: Run restoration
The registry SHALL restore every artifact referenced by a run manifest into a working directory so that the run can be re-executed.

#### Scenario: Rerun after six weeks
- **WHEN** `itemizer rerun <run_id>` is executed on a clean checkout
- **THEN** all referenced artifacts are restored from the CAS and the run starts with the same manifest
