## ADDED Requirements

### Requirement: Versioned taxonomy with definitions and examples
The system SHALL store each taxonomy version with 12 to 20 categories, each having a code, name, definition, inclusion and exclusion notes and at least one real example, plus the catch-all category `other_unmapped`. Examples in Git SHALL be stored as note fingerprints and offsets, and quotes SHALL be resolved from the dataset only when rendered.

#### Scenario: Category without example
- **WHEN** a taxonomy version contains a category with no example
- **THEN** taxonomy validation fails

#### Scenario: Note text in Git
- **WHEN** `taxonomy/categories.yaml` contains a quoted note instead of a fingerprint and offsets
- **THEN** taxonomy validation fails

### Requirement: Client approval before production use
A taxonomy version SHALL be usable in `prod` runs only when it has an approval record with approver role, date and evidence file hash.

#### Scenario: Unapproved taxonomy in prod
- **WHEN** a `prod` run references `taxonomy@v2-draft`
- **THEN** the run fails before stage 1

### Requirement: Taxonomy change requests from evidence
The system SHALL generate a taxonomy change request when the share of disputed dollars in `other_unmapped`, or the reviewer "no fitting category" rate, exceeds the configured trigger, listing the affected notes.

#### Scenario: Catch-all grows
- **WHEN** 7% of disputed dollars in a PROD run fall in `other_unmapped` and the trigger is 5%
- **THEN** a change request is created with the top recurring evidence phrases

### Requirement: Version mapping
A new taxonomy version SHALL include a mapping from every code of the previous version, so that KPI snapshots under different versions can be compared.

#### Scenario: Split category
- **WHEN** `fuel_surcharge` is split into two codes in v2
- **THEN** the mapping lists both targets and the dashboard marks cross-version comparisons

### Requirement: Standard code mapping (Level 3)
When `codes.standard_list` is not `none`, each category SHALL map to one or more codes of the configured list; unmapped categories SHALL be listed.

#### Scenario: Carrier list fallback
- **WHEN** the X12 license is unavailable and `codes.standard_list` is `carrier_xpo`
- **THEN** categories map to XPO accessorial codes and the output records the list used
