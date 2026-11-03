## 1. Contracts and grammar

- [x] 1.1 Implement `contracts.py` and `export_schemas`, and generate `contracts/schemas/`
- [x] 1.2 Implement `grammar.py`: answer schema with closed lists and the provider-independent parser
- [ ] 1.3 Write `architecture/docs/11-data-contracts.md`: input, note, label, item, row, output and KPI contracts

## 2. Models

- [x] 2.1 Write `config/models.yaml` and implement the registry and `load_secret`
- [x] 2.2 Implement the Anthropic, Ollama and OpenAI-compatible adapters and the shared contract test
- [x] 2.3 Implement `itemizer models` and `itemizer compare-models`

## 3. Itemizer

- [x] 3.1 Write `prompts/itemize_v1.md` and `prompts/fewshot_v1.yaml`
- [x] 3.2 Implement note itemization with retry, cache, budget, concurrency and telemetry
- [x] 3.3 Implement row outcomes

## 4. Workbook

- [x] 4.1 Implement the five sheets, highlighting and fixed sentences for `ai_reason`
- [x] 4.2 Implement the largest-disputes view
- [x] 4.3 Make the file byte-identical for identical inputs

## 5. Evaluation

- [x] 5.1 Implement coverage, item matching and weighted accuracy with bootstrap and Wilson intervals
- [x] 5.2 Implement the Level gate under Option A, invariants and the TEST budget ledger
- [x] 5.3 Implement provisional freeze and `load_test_gold`

## 6. Run and present

- [x] 6.1 Implement `itemizer run` with the manifest and run folder
- [x] 6.2 Implement `itemizer evaluate`
- [ ] 6.3 Implement `itemizer acceptance d3` and `record-review`, and create `deliverables/requests.yaml`

## 7. Live check and people

- [ ] 7.1 Run on a small TRAIN sample with the real API and record cost and timing
- [ ] 7.2 Run on all of TRAIN and fix what the real notes expose
- [ ] 7.3 (People) Confirm the worked examples in `prompts/fewshot_v1.yaml`
- [ ] 7.4 (People) Label TEST and at least 100 VALIDATION notes, then freeze TEST
- [ ] 7.5 Run on all rows, evaluate Level 1, and produce the summary
- [ ] 7.6 (People) Present D1, D2 and D3 to Jake, and record the review

## 8. Tests

- [ ] 8.1 Tests per scenario in all six capability specs, on invented notes with no network
