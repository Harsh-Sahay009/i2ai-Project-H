## 1. Taxonomy

- [ ] 1.1 Define `taxonomy/categories.yaml` schema and validator (12–20 categories, examples, catch-all)
- [ ] 1.2 Implement approval record and prod guard
- [ ] 1.3 Implement version mapping and change-request generator
- [ ] 1.4 Implement optional standard code mapping (X12 / carrier list)

## 2. Evaluation sets

- [ ] 2.1 Implement stratified sampler for TEST with seed and row-frequency capture
- [ ] 2.2 Implement gold item table schema and provenance tables (raw labels, agreement, resolution)
- [ ] 2.3 Implement sealing via version registry and role-restricted reader
- [ ] 2.4 Implement disjointness check and fingerprint export
- [ ] 2.5 Implement DEV and FRESH set builders with in-sample flag

## 3. Tests

- [ ] 3.1 Unit tests per scenario in `charge-taxonomy` and `evaluation-sets`
