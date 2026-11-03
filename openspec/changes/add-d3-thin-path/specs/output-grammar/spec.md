## ADDED Requirements

### Requirement: One controlled answer format
Every model answer MUST be one JSON object holding only `items`, `no_charge_stated`, `unsure` and `reason_code`, and each item MUST hold only `category`, `amount`, `evidence_text`, `line_type`, `derivation` and `basis`, with no free prose anywhere.

#### Scenario: Extra field
- **WHEN** a model adds a field `explanation` to its answer
- **THEN** the answer is rejected with `wrong_shape`

#### Scenario: Text around the JSON
- **WHEN** a model writes a sentence before the JSON object
- **THEN** the answer is rejected with `not_json`

### Requirement: Closed value lists
`category` MUST be a code in the approved taxonomy, and `line_type`, `derivation`, `basis` and `reason_code` MUST come from their closed lists.

#### Scenario: Invented category
- **WHEN** a model answers with category `yard_fee`, which is not in the taxonomy
- **THEN** the answer is rejected with `unknown_category`

### Requirement: Amount format
`amount` MUST be a string of digits, a point and exactly two digits.

#### Scenario: Number without cents
- **WHEN** a model answers with amount `85`
- **THEN** the answer is rejected with `bad_amount`

### Requirement: Evidence and amounts checked against the note
The parser SHALL apply the same evidence and amount checks used for labels, whichever provider wrote the answer.

#### Scenario: Paraphrased evidence
- **WHEN** a model quotes "lumper fee 85" and the note says "LUMPER 85"
- **THEN** the answer is rejected with `evidence_not_verbatim`

#### Scenario: Edited amount
- **WHEN** a note says "LUMPER $85.00" and a model answers 90.00
- **THEN** the answer is rejected with `amount_not_in_evidence`

### Requirement: Enforced at the provider and in the parser
The system SHALL send the grammar as a JSON Schema in each provider's own form, and SHALL parse every answer with one parser that does not depend on the provider.

#### Scenario: Provider without schema support
- **WHEN** a provider ignores the schema and returns free text
- **THEN** the parser rejects the answer and no item reaches a result

### Requirement: Rejected answers are not repaired
A rejected answer SHALL be retried once with its violation codes, and SHALL then send the note to Review. The system MUST NOT edit an answer to make it fit.

#### Scenario: Two rejected answers
- **WHEN** both answers for a note fail the grammar
- **THEN** the note is Review with reason `grammar_failed` and its rows carry no items

### Requirement: Explanations come from fixed sentences
The `ai_reason` column SHALL be rendered from `basis` and `line_type` using fixed sentences, and MUST NOT contain text written by a model.

#### Scenario: Category inferred
- **WHEN** an item has basis `inferred_from_context`
- **THEN** `ai_reason` reads "Category taken from the rest of the note."

#### Scenario: Amount already paid
- **WHEN** an item has line type `already_paid`
- **THEN** `ai_reason` reads "Already paid: subtracted from the items total."
