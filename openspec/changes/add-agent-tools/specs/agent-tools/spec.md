## ADDED Requirements

### Requirement: Pipeline tool set
The library SHALL provide `extract_money_spans`, `lookup_abbreviation`, `get_charge_categories`, `compute_rate_times_quantity`, `verify_evidence_span`, `reconcile_row`, `submit_itemization` and `escalate_to_review`, each with a JSON schema for its arguments and result.

#### Scenario: Tool list for the agent
- **WHEN** the agent controller requests tool definitions
- **THEN** it receives the allowlisted tools with schemas and docstrings

### Requirement: LLM-oriented docstrings
Every registered tool SHALL have a docstring with purpose, "Use when", "Do not use when", Args, Returns, Errors with next action, Determinism and Example sections, and the registry MUST refuse to register a tool whose docstring fails the lint.

#### Scenario: Missing section
- **WHEN** a tool docstring lacks "Do not use when"
- **THEN** `itemizer tools lint` fails naming the tool and section

### Requirement: Deterministic results
Every pipeline tool SHALL be a pure function of the note bytes, its arguments and the versions in the run manifest.

#### Scenario: Repeated call
- **WHEN** `reconcile_row` is called twice with the same arguments in the same run
- **THEN** both results are identical

### Requirement: Span-based numbers
`compute_rate_times_quantity` and `verify_evidence_span` SHALL accept numbers only as character spans of the note and SHALL return `SPAN_NOT_NUMERIC` or `SPAN_OUT_OF_RANGE` errors otherwise.

#### Scenario: Typed number
- **WHEN** the agent passes a span covering the word "lumper" as the rate
- **THEN** the tool returns `SPAN_NOT_NUMERIC` with a hint to call `extract_money_spans`

### Requirement: Unknown instead of guessing
`lookup_abbreviation` SHALL return `unknown` for tokens not in the active lexicon and SHALL NOT return a best guess.

#### Scenario: New abbreviation
- **WHEN** the agent looks up "YRD"
- **THEN** the tool returns `unknown` and the agent must either escalate or map it via the taxonomy definitions

### Requirement: Terminal tools
`submit_itemization` SHALL accept only items valid against the ChargeItem schema whose evidence passes verification, returning a structured rejection otherwise; `escalate_to_review` SHALL require a reason code from the error taxonomy.

#### Scenario: Escalation without reason
- **WHEN** the agent calls `escalate_to_review` with an empty reason code
- **THEN** the call is rejected with `REASON_REQUIRED`
