## 1. Reading and validation

- [ ] 1.1 Implement export reader with column alias config
- [ ] 1.2 Implement pandera input contract with fatal and warning checks
- [ ] 1.3 Implement data-quality report (counts, flags) and telemetry

## 2. Normalization and deduplication

- [ ] 2.1 Implement normalized columns preserving raw bytes
- [ ] 2.2 Implement fingerprinting, row-frequency map and fan-out index
- [ ] 2.3 Implement TEST fingerprint flagging

## 3. Masking

- [ ] 3.1 Implement regex + NER masker with stable placeholders and offset map
- [ ] 3.2 Store reversal map as confidential artifact
- [ ] 3.3 Measure masking recall on DEV fixture

## 4. Snapshots

- [ ] 4.1 Write Parquet snapshots and register with transform SHA
- [ ] 4.2 Tests per scenario in `data-ingestion`
