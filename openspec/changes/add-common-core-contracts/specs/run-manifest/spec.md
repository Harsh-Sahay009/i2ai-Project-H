## ADDED Requirements

### Requirement: Run manifest content
Before any stage executes, the system SHALL create a run manifest that records the input snapshot hash, dataset class, split manifest hash, taxonomy version, prompt template version, few-shot set version, lexicon version and carrier overrides, calibration map hash, effective config hash, route, model identities with digest or dated snapshot and decoding parameters, code Git SHA, lockfile hash, dirty flag, metric definitions version and price table version.

#### Scenario: Missing field
- **WHEN** a manifest is built without a model digest for the active route
- **THEN** the run fails before stage 1 with a `manifest_incomplete` error

### Requirement: Deterministic run id
The run id SHALL be derived from the SHA-256 of the canonical JSON of the manifest, excluding only the creation timestamp.

#### Scenario: Same inputs
- **WHEN** two manifests have identical content and different creation timestamps
- **THEN** they produce the same run id

#### Scenario: One parameter changed
- **WHEN** `confidence.review_threshold_row` changes from 0.80 to 0.81
- **THEN** the config hash and the run id both change

### Requirement: Dirty working tree blocks production runs
The system MUST refuse to start a run in the `prod` environment when the code working tree has uncommitted changes.

#### Scenario: Dirty tree in prod
- **WHEN** an operator runs in `prod` with an uncommitted change
- **THEN** the run stops with a message naming the modified files
