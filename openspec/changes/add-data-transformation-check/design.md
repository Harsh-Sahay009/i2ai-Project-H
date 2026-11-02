## Context

C4 container **Data Transformation & Check** (Export Reader, Input Contract Validator, Field Normalizer, Note Fingerprinter, Confidentiality Masker, Snapshot Writer). Placement: **common core** for the input contract; carrier-specific quirks stay **local exception** until they recur. Position: **owned**.

## Goals / Non-Goals

**Goals:** fail fast on contract errors; never alter raw text; one itemization per distinct note; masked text for any external route.

**Non-Goals:** connecting to TMS; fixing carrier text.

## Decisions

- **Input contract** (pandera): required columns (invoice id, carrier, ship date, estimated charge, billed charge, disputed amount, reason code, note); disputed amount > 0; currency known. Column-name aliases are configured per export version.
- **Fatal vs warning:** missing columns or unparsable amounts are fatal (exit 3); duplicate invoice keys and empty notes are warnings, rows kept and flagged (`repeated_invoice`, `empty_note`).
- **Fingerprint** = SHA-256 of whitespace-collapsed, case-folded note; raw bytes are kept for evidence.
- **Masking**: regex for phones/emails + spaCy PERSON entities + carrier-supplied driver-name list if available; placeholder `⟨PERSON_3⟩` stable within a snapshot; map written as a separate confidential artifact. Offsets are re-mapped so evidence spans refer to the raw note.
- **Snapshots** in Parquet, registered in CAS with transform code SHA.
- **Telemetry:** data-quality findings (action layer), row and note counts, dedup ratio.

## Risks / Trade-offs

- [Masking misses a name] → masking recall measured on DEV; external route blocked if recall < configured floor.
- [Masking changes offsets] → offset map tested on fixtures.

## Open Questions

- Will future exports keep the 2022 column layout?
