## 1. Queue and workbook

- [ ] 1.1 Implement queue builder with audit sampling, priority, capacity cap, backlog record
- [ ] 1.2 Implement Review Decision Intake service (prediction-hash check, reason-code rule, outcome records with surface)
- [ ] 1.3 Implement fallback review workbook exporter/importer feeding the same intake

## 2. Labelling

- [ ] 2.1 Wrap the Labelling Pack Builder and Label Validator from add-ground-truth-bootstrap as the service behind the Blind Labelling Page
- [ ] 2.2 Wrap agreement statistics and client review from add-ground-truth-bootstrap for use from the UI
- [ ] 2.3 Hook sealing into ground truth store

## 3. Adjudication

- [ ] 3.1 Implement adjudication workbook and recorder with four buckets
- [ ] 3.2 Implement eligibility filter for improvement inputs
- [ ] 3.3 Implement Case Closer with replay pack creation

## 4. Tests

- [ ] 4.1 Tests per scenario in `review-workflow` and `adjudication`
