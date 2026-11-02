## 1. Extraction

- [ ] 1.1 Implement money/rate×qty/tax/already-paid extractor with lexicon loader
- [ ] 1.2 Write lexicon v1 from sample abbreviations and misspellings (DEV only)

## 2. Model itemization

- [ ] 2.0 Implement Itemization Agent Controller (loop, budgets, terminal tools, transcript cache key, trace telemetry)

- [ ] 2.1 Implement Prompt Builder with versioned template, taxonomy definitions, few-shot set, hints
- [ ] 2.2 Implement Structured Response Parser
- [ ] 2.3 Implement rules-only itemizer as baseline route

## 3. Checks

- [ ] 3.1 Implement Evidence Verifier using raw-note offsets and mask offset map
- [ ] 3.2 Implement Category Mapper with `other_unmapped`
- [ ] 3.3 Implement Decimal Amount Reconciler with tolerances and already-paid netting

## 4. Scoring and outcomes

- [ ] 4.1 Implement confidence features and calibration map application
- [ ] 4.2 Implement ordered Outcome Assigner and no-charge policy
- [ ] 4.3 Implement fingerprint fan-out with per-row reconciliation
- [ ] 4.4 Emit decision telemetry

## 5. Tests

- [ ] 5.1 Run core contract tests for rules-only, local and external implementations
- [ ] 5.2 Tests per scenario in `itemization`
