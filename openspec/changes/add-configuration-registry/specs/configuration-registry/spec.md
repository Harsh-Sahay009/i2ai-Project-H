## ADDED Requirements

### Requirement: Declared parameters only
The registry SHALL reject any configuration key that is not declared in the Parameter Schema, and every declared parameter SHALL carry type, default, limits or enum, owner role, family, gate, validity horizon and affected metrics.

#### Scenario: Unknown key
- **WHEN** an environment file sets `confidence.review_treshold_row`
- **THEN** resolution fails naming the unknown key and the closest declared key

### Requirement: Layered resolution
The resolver SHALL merge core defaults, environment file, carrier overrides and CLI flags in that order, accepting carrier overrides only for keys marked carrier-overridable and CLI flags only for keys marked CLI-overridable.

#### Scenario: Carrier lexicon override
- **WHEN** `carriers/CARRIER_07.yaml` sets `lexicon.version: lexicon-carrier07@v2`
- **THEN** rows from CARRIER_07 resolve that lexicon and all other rows resolve the environment lexicon

#### Scenario: Forbidden CLI override
- **WHEN** an operator passes `--set routing.external_ai_approved=true`
- **THEN** resolution fails because the key is not CLI-overridable

### Requirement: Limits enforced without clamping
The resolver MUST fail when any value is outside its declared limits and MUST NOT adjust the value.

#### Scenario: Audit rate below floor
- **WHEN** `review.audit_sample_rate_verified` is set to 0.02 with a floor of 0.05
- **THEN** resolution fails and the run does not start

### Requirement: Frozen and hashed effective config
The resolver SHALL produce an immutable effective config and its SHA-256 over canonical JSON, which the run manifest records.

#### Scenario: Reordered YAML
- **WHEN** two environment files contain the same values in different key order
- **THEN** both produce the same config hash

### Requirement: Gated parameters
Parameters with gate `promotion` SHALL change only with a reference to a published change id; parameters with gate `written_approval` SHALL require a non-empty approval reference; parameters with gate `locked` SHALL NOT be changeable.

#### Scenario: External AI without approval
- **WHEN** `routing.external_ai_approved` is true and `routing.approval_ref` is empty
- **THEN** resolution fails

#### Scenario: Threshold edited by hand
- **WHEN** `confidence.review_threshold_row` changes in Git without a `published_change` reference
- **THEN** the config validation check fails in CI and in `itemizer run`

### Requirement: Change log
Every change to a configuration value SHALL be recorded with author, timestamp, key, previous value, new value, reason and evidence link.

#### Scenario: Query history
- **WHEN** an operator runs `itemizer config history confidence.review_threshold_row`
- **THEN** all changes are listed newest first with their evidence links

### Requirement: Validity horizon reporting
The registry SHALL compute, for each gated parameter, the date its value expires from the publication date plus its validity horizon, and SHALL list expired values.

#### Scenario: Expired threshold
- **WHEN** a threshold was published 31 days ago with a 30-day horizon
- **THEN** `itemizer config expired` lists it and the run prints a warning
