## Why

The weekly export is the only interface to Oracle TMS. Bad columns, duplicate invoices or encoding problems would silently corrupt coverage and accuracy, and names in notes must not leave team storage without approval. Many rows share the same note, so itemizing per row wastes money and makes repeated notes disagree.

## What Changes

- Read the .xlsx export without altering raw values; validate against the input contract; produce a data-quality report.
- Normalize into derived columns while preserving raw note bytes for evidence checks.
- Fingerprint notes, deduplicate, record row frequency, and exclude TEST fingerprints from tuning data.
- Mask names, phones and emails with stable placeholders; keep the map on team storage.
- Write raw and normalized snapshots to the version registry.
- Expose the input contract check as a pre-check call used by the Web UI upload page before any run.

## Capabilities

### New Capabilities
- `data-ingestion`: export reading, contract validation, normalization, fingerprinting, masking, snapshotting.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.ingest` (pandas, pandera, openpyxl, spaCy small model for names).
- Depends on core contracts, version registry, ground truth (fingerprints).
