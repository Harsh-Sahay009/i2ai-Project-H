## ADDED Requirements

### Requirement: Deterministic money and pattern extraction
The classifier SHALL extract every money token, rate × quantity pattern, tax mention and already-paid phrase from the raw note using the configured lexicon version, before any model call.

#### Scenario: Abbreviated detention
- **WHEN** a note reads "DET 2HRS @75 = 150.00 + LUMPER 85"
- **THEN** the extractor returns tokens 2, 75, 150.00 and 85 with offsets and a rate × quantity pattern linking 2 and 75

### Requirement: Bounded tool-calling agent
The classifier SHALL itemize each note with an agent loop in which the pretrained LLM, called through the Model Router, selects tools from `agent.tool_allowlist`, and the loop SHALL end only through `submit_itemization` or `escalate_to_review` within `agent.max_steps` steps.

#### Scenario: Step budget reached
- **WHEN** the agent reaches `agent.max_steps` without a terminal tool call
- **THEN** the row is set to Review with reason `step_budget_exhausted`

#### Scenario: Final text without terminal tool
- **WHEN** the model replies with free text listing charges instead of calling `submit_itemization`
- **THEN** no items are accepted and the row is Review with reason `no_terminal_call`

### Requirement: Amounts come from tools
Every accepted amount MUST be a stated amount returned by `extract_money_spans` or a product returned by `compute_rate_times_quantity`; an amount typed by the model SHALL be rejected by the output guard.

#### Scenario: Model does arithmetic
- **WHEN** the agent submits 160.00 for "2 hrs @ 75" without calling `compute_rate_times_quantity`
- **THEN** the submission is rejected with `amount_not_from_tool` and the agent may resubmit once

### Requirement: Structured itemization through the router
The classifier SHALL request itemization through the Model Router with a prompt built from the configured template, taxonomy version, few-shot set and extractor hints, and SHALL accept only responses that validate against the item schema.

#### Scenario: Malformed response
- **WHEN** the provider returns JSON missing the amount field
- **THEN** the response is treated as a provider failure and handled by fallback

### Requirement: Verbatim evidence enforced
Every accepted item MUST have evidence that is verbatim in the raw note under `evidence.match_mode`; any item failing the check SHALL be rejected and its row SHALL be set to Review with reason `evidence_failed`.

#### Scenario: Paraphrased quote
- **WHEN** the model quotes "lumper fee 85" but the note says "LUMPER 85"
- **THEN** the item is rejected and the row is Review

### Requirement: Amounts never edited
The classifier MUST NOT change any amount produced by the note's text or its declared derivation, including to make a row reconcile.

#### Scenario: Near miss
- **WHEN** items total 234.99 and the disputed amount is 235.00 with tolerance 0.00
- **THEN** items keep their amounts and the row is Discrepancy with delta 0.01

### Requirement: Category mapping to the active taxonomy
Each item category SHALL map to a code in the active taxonomy version; unknown categories SHALL become `other_unmapped`.

#### Scenario: Unknown label
- **WHEN** the model returns category "yard fee" not in the taxonomy
- **THEN** the item is stored as `other_unmapped` with the original label in decision telemetry

### Requirement: Reconciliation with configured tolerance
The classifier SHALL compute delta as disputed amount minus (sum of items minus sum of already-paid items) and SHALL treat the row as reconciling when the absolute delta is within `reconcile.abs_tolerance_usd` or `reconcile.rel_tolerance` times the disputed amount.

#### Scenario: Already paid
- **WHEN** a note says "TOTAL 300, 100 PAID ON INV 5521" and the disputed amount is 200
- **THEN** items are 300 (stated) and 100 (already_paid) and the row reconciles

### Requirement: Calibrated confidence
The classifier SHALL compute item and row confidence from the published calibration map version recorded in the manifest.

#### Scenario: Map missing
- **WHEN** the manifest references a calibration map hash that is not in the registry
- **THEN** the run fails before itemization

### Requirement: Outcome assignment order
The classifier SHALL assign outcomes in this order: no charge stated per policy; Review for evidence failure, provider unavailability or budget exhaustion; Review when row confidence is below `confidence.review_threshold_row`; Verified when the row reconciles; otherwise Discrepancy.

#### Scenario: Confident but not reconciling
- **WHEN** row confidence is 0.93 with threshold 0.80 and delta is 40.00
- **THEN** the outcome is Discrepancy

#### Scenario: Low confidence reconciling row
- **WHEN** row confidence is 0.62 with threshold 0.80 and the row reconciles
- **THEN** the outcome is Review

### Requirement: Shared-note fan-out
The classifier SHALL itemize each distinct note once and apply the items to every row sharing it, reconciling each row against its own disputed amount.

#### Scenario: Shared note, different amounts
- **WHEN** two rows share a note and have disputed amounts 150 and 235
- **THEN** both receive the same items and each gets its own outcome

### Requirement: Decision telemetry
For every row the classifier SHALL record extractor hints, raw response hash, parsed items, evidence results, reconciliation delta, confidence components, thresholds in force and the outcome rule applied, keyed by case id.

#### Scenario: Explain a Review
- **WHEN** an operator inspects a Review row
- **THEN** telemetry shows which rule sent it to Review and the values that triggered it
