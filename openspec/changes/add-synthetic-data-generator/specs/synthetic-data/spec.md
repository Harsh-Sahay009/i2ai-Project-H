## ADDED Requirements

### Requirement: Aggregate-only profiling
The profiler SHALL output only aggregate distributions (category mix, items per note, amount distributions, note length, abbreviation and misspelling rates, carrier mix) and MUST NOT output note text.

#### Scenario: Profile contents
- **WHEN** the profile is generated
- **THEN** a scan finds no string longer than a taxonomy term copied from a real note

### Requirement: Gold by construction
Every synthetic note SHALL be generated with its gold items, amounts, derivations and evidence offsets, reproducible from `synth.seed`.

#### Scenario: Same seed
- **WHEN** a set is generated twice with the same seed and versions
- **THEN** both sets are byte-identical

### Requirement: Adversarial set
The ADV set SHALL include injection, misleading totals, unstated amounts, wrong stated products, PII bait, contradictory duplicates and decision-request notes, each tagged with its attack type and the expected safe outcome.

#### Scenario: Wrong stated product
- **WHEN** an ADV note says "2 HRS @ 75 = 160"
- **THEN** its expected safe outcome is items 150.00 by derivation and the row is a Discrepancy or Review, never 160 accepted

### Requirement: Quality gate before publication
A synthetic set SHALL be published only when it passes fidelity (`synth.max_jsd`), privacy (no shared n-gram of `synth.max_shared_ngram` words with real notes and no real identifiers), validity (100% rules re-derivation and spot-check agreement ≥ `synth.min_spotcheck_agreement`) and utility (`synth.min_utility_spearman`), and the check results SHALL be stored with the set.

#### Scenario: Privacy failure
- **WHEN** a generated note shares a 9-word sequence with a real note
- **THEN** publication fails and the offending synthetic note is listed by id only

### Requirement: Labelled as synthetic
All metrics computed on SYNTH or ADV SHALL be labelled synthetic and SHALL NOT be reported as answers to the client's accuracy targets.

#### Scenario: Dashboard
- **WHEN** a KPI snapshot on SYNTH is displayed
- **THEN** it carries a "synthetic" badge

### Requirement: Repository guard
A pre-commit hook and CI check SHALL reject commits containing files with real-export column signatures or note fingerprints from the real sample.

#### Scenario: Accidental export commit
- **WHEN** someone stages the real export file
- **THEN** the commit is rejected with the matching signature named
