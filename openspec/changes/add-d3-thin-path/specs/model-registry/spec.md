## ADDED Requirements

### Requirement: Models listed in one file
Models SHALL be listed in `config/models.yaml` with their provider, model id, prices and settings, and a model on a known API MUST be usable by adding one entry, with no code change.

#### Scenario: New model on a known API
- **WHEN** an entry for another Claude model is added and `itemizer run --model <name>` is run
- **THEN** the run uses that model, and its manifest records the full entry

#### Scenario: Unknown name
- **WHEN** `--model` names no entry
- **THEN** the command stops and lists the available names

### Requirement: One provider interface
Every provider SHALL implement one interface taking a system prompt, a user prompt and a schema, and returning text and usage. Every registered adapter MUST pass one shared contract test.

#### Scenario: New API family
- **WHEN** an adapter class is added to `ADAPTERS`
- **THEN** the shared contract test runs against it with no new test code

### Requirement: Secrets stay out of output
API keys SHALL be read from the environment or `.env`, and MUST NOT appear in logs, manifests, telemetry, error messages or printed output.

#### Scenario: Key missing
- **WHEN** the variable named by `api_key_env` is not set
- **THEN** the error names the variable and no value

### Requirement: Compare models on the same notes
`itemizer compare-models` SHALL run each named model on the same TRAIN or VALIDATION notes with the same prompt, and SHALL report valid-first-try rate, retry rate, Review share, Verified and Discrepancy shares, agreement with the first model, cost, latency, and projected cost and minutes for all notes.

#### Scenario: Two models
- **WHEN** an operator compares two models on 30 TRAIN notes
- **THEN** a table shows both models on the same measures, and the report contains no note text

#### Scenario: TEST refused
- **WHEN** an operator asks to compare models on TEST
- **THEN** the command refuses, because TEST never chooses between candidates

#### Scenario: Labels available
- **WHEN** the compared notes have labels
- **THEN** the report adds accuracy on those notes as an aggregate

### Requirement: Cost from usage and listed prices
The system SHALL compute each call's cost from its token usage and the prices in the model's entry.

#### Scenario: Cached tokens
- **WHEN** a call reads 1,000 tokens from the prompt cache
- **THEN** those tokens are priced at `cache_read_usd_per_mtok`
