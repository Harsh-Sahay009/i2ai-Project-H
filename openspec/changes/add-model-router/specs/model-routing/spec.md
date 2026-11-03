## ADDED Requirements

### Requirement: Provider interface and contract tests
All model providers SHALL implement one interface that accepts a prompt, an output JSON schema and decoding parameters and returns a structured response, usage and model fingerprint, and every provider SHALL pass the shared contract tests before it can be routed to.

#### Scenario: New provider added
- **WHEN** a new adapter fails the timeout contract test
- **THEN** the router refuses to register it

### Requirement: Fail-closed confidentiality gate
The router MUST NOT send any text to an external provider unless the payload passes the PII check and either `data.dataset_class` is `open_anonymized` with `data.source_ref` set, or `routing.external_ai_approved` is true with `routing.approval_ref` set; otherwise the call SHALL be blocked and logged.

#### Scenario: Confidential data without approval
- **WHEN** the route is `external`, `data.dataset_class` is `client_confidential` and approval is false
- **THEN** no external request is made and the run fails at config resolution

#### Scenario: Anonymized dataset with a source
- **WHEN** the route is `external`, `data.dataset_class` is `open_anonymized` and `data.source_ref` is set
- **THEN** the external call is allowed

#### Scenario: Name left in the anonymized data
- **WHEN** an external call's payload contains a phone number pattern
- **THEN** the call is blocked, the note is routed per fallback order, and a `gate_block` event is logged

### Requirement: Configured routing
The router SHALL choose the provider from `routing.route` with any carrier or size overrides and SHALL record the chosen route per note.

#### Scenario: Rules-only route
- **WHEN** `routing.route` is `rules_only`
- **THEN** no model is called and the classifier uses only deterministic extraction

### Requirement: Fallback without guessing
On provider error, timeout or schema-invalid output, the router SHALL retry up to `routing.max_retries`, then try the next provider in `routing.fallback_order`, and when all fail SHALL return a `provider_unavailable` result that the classifier turns into Review.

#### Scenario: Local runtime down
- **WHEN** Ollama is not reachable and fallback order is `[local, rules_only]`
- **THEN** notes are processed with rules only and the dashboard shows the fallback share

### Requirement: Pinned models
The router MUST reject model identifiers that are aliases without a digest or dated snapshot.

#### Scenario: Alias
- **WHEN** `model.external.id` is set to a `-latest` alias
- **THEN** config resolution fails

### Requirement: Reproducible response cache
The router SHALL cache responses keyed by the hash of prompt, model identity with digest, decoding parameters and schema version, and SHALL never serve a cached response for a different model identity.

#### Scenario: Rerun with cache
- **WHEN** a run is repeated with cache enabled
- **THEN** zero model calls are made and responses are identical

### Requirement: Cost metering
The router SHALL record tokens in, tokens out, latency and cost per call using the configured price table version, and local compute cost using the configured rate.

#### Scenario: Run cost
- **WHEN** a run finishes
- **THEN** the telemetry store holds a cost total that the KPI Calculator can reproduce from per-call records

### Requirement: Silent upstream change detection
The router SHALL replay a fixed canary set on demand and on each run start, compare response fingerprints with the stored ones for the same model identity, and emit a `silent_change` event on mismatch.

#### Scenario: Provider changes behind same id
- **WHEN** canary fingerprints differ for an unchanged model id
- **THEN** a `silent_change` event is logged and affected published changes are flagged for recertification
