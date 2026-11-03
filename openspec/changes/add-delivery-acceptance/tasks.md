## 1. Acceptance checks

- [ ] 1.1 Implement `itemizer acceptance d3`: end-to-end run on the sample export, Level 1 gate on TEST, evidence summary
- [ ] 1.2 Implement the client review record with date and evidence hash
- [ ] 1.3 Implement `itemizer acceptance d4`: one command on a new or synthetic export, 1,500-row timing, workbook sheets, Level 2 gate on TEST
- [ ] 1.4 (People) Show Jake the prototype and record it (D3)
- [ ] 1.5 (People) Confirm with Jake that a level is met when the measured value reaches the target, with the interval shown beside it

## 2. Client requests

- [ ] 2.1 Create `deliverables/requests.yaml` with item, owner, date asked and status
- [ ] 2.2 (People) Ask PPG for current minutes per dispute and monthly dispute volume
- [ ] 2.3 (People) Obtain Jake's written agreement to the Web UI and confirmation of the dataset

## 3. D5 report

- [ ] 3.1 Implement measure tables from KPI snapshots, with n, interval and snapshot ids
- [ ] 3.2 Implement the labels: in-sample, synthetic, TEST evaluation count, VALIDATION comparison count, known biases
- [ ] 3.3 Implement error examples: from TRAIN by default, from TEST only after release
- [ ] 3.4 Implement rerun instructions from the run manifest: code tag, lockfile, config, dataset source and hash, model id, both rerun paths
- [ ] 3.5 (People) Write the method and discussion sections, within 8 to 12 pages
- [ ] 3.6 (People) Dry run: someone outside the team follows the report on a clean machine, and the team fixes what fails

## 4. Tests

- [ ] 4.1 Tests per scenario in `deliverable-acceptance` and `methodology-report`, using synthetic data
