## 1. Mining and candidates

- [ ] 1.1 Implement Closed Case Miner with eligibility and TEST and VALIDATION fingerprint exclusion
- [ ] 1.2 Implement Candidate Change Generator for each candidate type
- [ ] 1.3 Route taxonomy change requests to ground truth

## 2. Calibration and replay

- [ ] 2.1 Implement isotonic calibration and threshold selection on VALIDATION
- [ ] 2.2 Implement Replay Runner with row-level diff on TRAIN and replay packs, and error-type deltas on VALIDATION

## 3. Promotion

- [ ] 3.1 Implement evidence collection for the four channels from VALIDATION, and count comparisons per VALIDATION version
- [ ] 3.2 Implement operator approval step in `itemizer promote`
- [ ] 3.3 Implement Change Publisher with full record and change log entry
- [ ] 3.4 Implement one-command rollback

## 4. Recertification

- [ ] 4.1 Implement Recertification Scheduler (horizon, digest change, silent change)
- [ ] 4.2 Implement `itemizer recertify`

## 5. Tests

- [ ] 5.1 Tests per scenario in `calibration-loop` and `promotion-gate`
