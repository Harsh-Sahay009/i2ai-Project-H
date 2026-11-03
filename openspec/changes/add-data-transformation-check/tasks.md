## 1. Reading and validation

- [ ] 1.1 Implement export reader with column alias config
- [ ] 1.2 Implement pandera input contract with fatal and warning checks
- [ ] 1.3 Implement data-quality report (counts, flags) and telemetry

## 2. Normalization and deduplication

- [ ] 2.1 Implement normalized columns preserving raw bytes
- [ ] 2.2 Implement fingerprinting, row-frequency map and fan-out index
- [ ] 2.3 Implement TEST and VALIDATION fingerprint flagging
- [ ] 2.4 Assign `row_id` from export position; flag `repeated_invoice`, `empty_note` and `non_positive_delta`

## 3. Snapshots

- [ ] 3.1 Write Parquet snapshots, recording `data.dataset_class`, and register with transform SHA
- [ ] 3.2 Tests per scenario in `data-ingestion`
