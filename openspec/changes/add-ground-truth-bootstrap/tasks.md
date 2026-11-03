## 1. Setup

- [x] 1.1 Create `pyproject.toml` if missing and the `itemizer.bootstrap` package with the standalone `itemizer gt` CLI and JSONL command log
- [ ] 1.2 (People) Add the file's public link and Jake's confirmation to `data.source_ref`
- [ ] 1.3 (People) Name the two labellers and the client reviewer

## 2. Profile and split

- [x] 2.1 Implement `gt profile`: rows, distinct notes, formats, carriers, date range, disputed dollars, repeated-invoice rows, catch-all reason share, compared with the scope's figures
- [x] 2.2 Implement the anonymization scan for phone numbers, emails and person names, with the operator's recorded decision
- [x] 2.3 Implement note fingerprints, format keys, repeat bands and provisional strata
- [x] 2.4 Implement `gt split`: example-sheet notes to TRAIN, TEST (100 / 50 / 50) and reserve first, then TRAIN and VALIDATION, with seed, disjointness check and split manifest
- [x] 2.5 Record for each TEST note whether its format appears in TRAIN

## 3. D1 charge category list

- [x] 3.1 Implement `gt draft-taxonomy` over TRAIN notes only, with the dataset class check, verbatim example check, 12–20 category check and `other_unmapped`
- [x] 3.2 Write `taxonomy/categories.yaml` with fingerprints and offsets only, plus a validator that rejects note text
- [x] 3.3 Implement `gt approval-doc`: about two pages with definitions and real examples, kept out of Git
- [x] 3.4 Implement `gt record-approval` with approver role, date and evidence file hash
- [ ] 3.5 (People) Edit the draft; merge or split categories until each has a clear definition
- [ ] 3.6 (People) Send the document to Jake and obtain written approval
- [ ] 3.7 (People) If a model-written draft is wanted, set an API key and run `gt draft-taxonomy --send` once, which also confirms the live call

## 4. D2 tooling

- [ ] 4.1 Implement `gt label-packs`: separate workbooks for labeller A and B (50 notes), the single-labelled 150 and the 15-note spot check
- [ ] 4.2 Implement `gt import-labels`: category in taxonomy, two-decimal amount, verbatim evidence, stated amount in evidence, rate × quantity product, with a per-row error report
- [ ] 4.3 Implement `gt agreement`: Cohen's kappa on category, exact match on amounts, item count match, list of disagreements
- [ ] 4.4 Implement `gt client-pack` and `gt import-client`: all 50 notes with both labels, disagreements flagged, the reviewer's decision becomes gold
- [ ] 4.5 Implement final strata from gold items and replacement from the reserve
- [ ] 4.6 Implement `gt seal`: every seal condition checked, hash recorded, fingerprint list exported without labels, unused reserve released to TRAIN and VALIDATION

## 5. Labelling (people)

- [ ] 5.1 Two labellers label the same 50 TEST notes separately, without seeing tool output
- [ ] 5.2 Label the other 150 TEST notes, and spot-check 15
- [ ] 5.3 Jake or a PPG accountant reviews all 50 double-labelled notes and resolves disagreements
- [ ] 5.4 Seal TEST
- [ ] 5.5 Label VALIDATION without tool output, at least `split.min_validation_notes` notes
- [ ] 5.6 Label TRAIN, with LLM suggestions allowed and recorded

## 6. Tests

- [ ] 6.1 Test that no TEST or VALIDATION pack contains tool output, by inspecting every generated file
- [ ] 6.2 Tests per scenario in `dataset-profile-split`, `taxonomy-drafting` and `test-set-preparation` on synthetic notes
