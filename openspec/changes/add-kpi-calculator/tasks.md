## 1. Definitions

- [ ] 1.1 Write `metrics/definitions.yaml` v1 for errors a–g, success a–e, coverage and loop health
- [ ] 1.2 Write `metrics/prices.yaml` with effective dates
- [ ] 1.3 Implement definition loader and population validation

## 2. Resolution and matching

- [ ] 2.1 Implement Evaluation Set Resolver with role check and version-only reads
- [ ] 2.2 Implement Hungarian Item Matcher with tolerance and cost table
- [ ] 2.3 Implement Error Taxonomy Classifier

## 3. Metrics

- [ ] 3.1 Implement coverage (counting `no_charge_stated` as Verified under policy) and weighted accuracy with note-to-row fan-out
- [ ] 3.2 Implement error metrics a–g including ECE and invariant counts
- [ ] 3.3 Implement cost recomputation from per-call telemetry and price table
- [ ] 3.4 Implement item- and row-level AUC with undefined handling
- [ ] 3.5 Implement approval rate by outcome and audit disagreement
- [ ] 3.6 Implement reproducibility comparison between runs
- [ ] 3.7 Implement loop health metrics
- [ ] 3.8 Implement per-carrier coverage and accuracy
- [ ] 3.9 Implement the Level 3 cost-driver summary by carrier and category
- [ ] 3.10 Report dollar coverage with and without repeated-invoice rows, and accuracy for seen and unseen formats

## 4. Weighting and uncertainty

- [ ] 4.1 Implement Stratum Weighter and versioned weights artifact
- [ ] 4.2 Implement Wilson intervals and seeded stratified bootstrap

## 5. Gates and snapshots

- [ ] 5.1 Implement Level Gate Evaluator with invariant gate
- [ ] 5.2 Implement TEST peek budget, refusal of promotion requests for TEST, and aggregate VALIDATION responses
- [ ] 5.3 Implement immutable KPI Snapshot Writer with equality check

## 6. Tests

- [ ] 6.1 Hand-computed fixture tests for every metric
- [ ] 6.2 Tests per scenario in `kpi-metrics` and `level-gates`
