## Why

This is the core of the product: turn a free-text dispute note, full of abbreviations and misspellings, into charge items an accountant can check without reading the note. It must hit ≥95% accuracy on covered rows while never inventing or editing an amount, and it must know when it is not confident so that row goes to a person.

## What Changes

- Deterministic Amount & Pattern Extractor (money tokens, rate × quantity, taxes, "already paid") using a versioned lexicon.
- Prompt Builder from versioned template, taxonomy definitions, few-shot set and extractor hints, with note text wrapped as untrusted data.
- Itemization Agent Controller: a bounded tool-calling loop on the pretrained LLM (ADR 0008) that uses the custom tools from add-agent-tools, passes every step through add-guardrails, and ends only through `submit_itemization` or `escalate_to_review`.
- Structured Response Parser, Evidence Verifier, Category Mapper.
- Amount Reconciler (net of amounts already paid, configured tolerance), Confidence Scorer (calibrated), Outcome Assigner.
- Fan-out of note results to every row sharing the note; decision telemetry for every item and row.

## Capabilities

### New Capabilities
- `itemization`: note-to-items extraction, evidence verification, reconciliation, confidence scoring and outcome assignment.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.classify`.
- Depends on core contracts, configuration registry (thresholds, prompting, vocabulary, agent), router, agent tools, guardrails, ground truth (taxonomy), telemetry store.
- Level 1 (D3): single-charge + largest disputes; Level 2 (D4): multi-charge, rate × quantity, taxes, already paid.
