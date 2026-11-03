## Context

C4 container **Data Transformation & Check** (Export Reader, Input Contract Validator, Field Normalizer, Note Fingerprinter, Snapshot Writer). Placement: **common core** for the input contract; carrier-specific quirks stay **local exception** until they recur. Position: **owned**.

## Goals / Non-Goals

**Goals:** fail fast on contract errors; never alter raw text; one itemization per distinct note.

**Non-Goals:** connecting to TMS; fixing carrier text.

## Decisions

- **Input contract** (pandera): required columns, with aliases per export version. Current export: shipment `SHIPMENT_GID`, invoice `Carrier Invoice`, carrier `Carrier`, date `Event Date`, estimated charge `Shipment Amount`, billed charge `Invoice Amount`, disputed amount `Delta` (billed minus estimated on every row), reason code `Reason Code`, note `Descritipion` (spelled this way in the file), repeat marker `Invoice Dups Removed` (0 on repeated rows).
- **Row id.** `row_id` comes from the row's position in the export. No combination of ID columns identifies a row: `PK` is blank on 467 rows, and a shipment can have up to 24 rows.
- **Fatal vs warning:** missing columns or unparsable amounts are fatal (exit 3); repeated invoices, empty notes and non-positive deltas are warnings, rows kept and flagged (`repeated_invoice`, `empty_note`, `non_positive_delta`). The current file has 192, 9 and 23 such rows.
- **Fingerprint** = SHA-256 of whitespace-collapsed, case-folded note; raw bytes are kept for evidence.
- **No masking** (ADR 0013): the project uses one anonymized dataset. The Dataset Profiler scans it before any text is sent out, and the Privacy Guard screens model-bound payloads.
- **Snapshots** in Parquet, registered in CAS with transform code SHA.
- **Telemetry:** data-quality findings (action layer), row and note counts, dedup ratio.

## Risks / Trade-offs

- [The dataset is not fully anonymized] → scan findings and Privacy Guard blocks are visible in telemetry.

## Open Questions

- Will future exports keep the 2022 column layout?
