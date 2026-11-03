## 1. Taxonomy

- [ ] 1.1 Adopt the `taxonomy/categories.yaml` schema and validator from add-ground-truth-bootstrap (12–20 categories, examples by fingerprint, catch-all)
- [ ] 1.2 Implement approval record and prod guard
- [ ] 1.3 Implement version mapping and change-request generator
- [ ] 1.4 Implement optional standard code mapping (X12 / carrier list)

## 2. Evaluation sets

- [ ] 2.1 Register the split manifest and TEST sample from add-ground-truth-bootstrap, with seed and row frequency
- [ ] 2.2 Implement gold item table schema and provenance tables (raw labels, agreement, resolution)
- [ ] 2.3 Implement sealing via version registry and role-restricted reader
- [ ] 2.4 Implement disjointness check across all sets and fingerprint export
- [ ] 2.5 Implement TRAIN, VALIDATION and FRESH set registration with in-sample flag
- [ ] 2.6 Enforce allowed use per set (few-shot and lexicon from TRAIN only; TEST for Level gates only)

## 3. Tests

- [ ] 3.1 Unit tests per scenario in `charge-taxonomy` and `evaluation-sets`
