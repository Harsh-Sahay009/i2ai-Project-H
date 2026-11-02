## ADDED Requirements

### Requirement: Locked test set composition
The TEST set SHALL contain 200 distinct note fingerprints, half single-charge and half multi-charge or large disputes, sampled with a recorded seed, each with gold items (category, amount, evidence span) and stratum.

#### Scenario: Duplicate note
- **WHEN** two sampled rows share a fingerprint
- **THEN** only one note enters the TEST set and its row frequency is recorded

### Requirement: Blind double labelling provenance
For the 50 double-labelled notes, the store SHALL keep both labellers' raw labels, the agreement statistics and the client owner's resolution for every disagreement.

#### Scenario: Unresolved disagreement
- **WHEN** a disagreement has no resolution
- **THEN** the TEST set cannot be sealed

### Requirement: Sealing
A sealed evaluation set SHALL be immutable, registered with its hash, and readable only by the KPI Calculator role.

#### Scenario: Edit after sealing
- **WHEN** someone corrects a gold label in a sealed TEST version
- **THEN** a new version must be created, and KPI snapshots record which version they used

### Requirement: Disjointness
DEV, FRESH and every few-shot set SHALL share no note fingerprint with TEST, and the check SHALL run whenever any of them is published.

#### Scenario: Leaked few-shot example
- **WHEN** a few-shot set contains a fingerprint present in TEST
- **THEN** publication fails naming the fingerprint

### Requirement: In-sample labelling
Every evaluation set SHALL record whether its notes come from data used to build the tool, and KPI outputs on such sets SHALL be labelled in-sample.

#### Scenario: No FRESH data
- **WHEN** only the 2021–2022 sample is available
- **THEN** accuracy is reported with the label "in-sample"
