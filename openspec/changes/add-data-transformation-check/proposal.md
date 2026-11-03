## Why

The weekly export is the only interface to Oracle TMS. Bad columns, duplicate invoices or encoding problems would silently corrupt coverage and accuracy. Many rows share the same note, so itemizing per row wastes money and makes repeated notes disagree.

## What Changes

- Read the .xlsx export without altering raw values; validate against the input contract; produce a data-quality report.
- Normalize into derived columns while preserving raw note bytes for evidence checks.
- Fingerprint notes, deduplicate, record row frequency, and flag TEST and VALIDATION fingerprints so they stay out of tuning data.
- Write raw and normalized snapshots to the version registry, recording `data.dataset_class`.
- Expose the input contract check as a pre-check call used by the Web UI upload page before any run.

## Capabilities

### New Capabilities
- `data-ingestion`: export reading, contract validation, normalization, fingerprinting, snapshotting.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.ingest` (pandas, pandera, openpyxl).
- Depends on core contracts, version registry, ground truth (fingerprints).
