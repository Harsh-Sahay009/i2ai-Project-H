## Context

C4 container **Output Formatter**. Placement: **common core** (output contract). Position: **owned**.

## Goals / Non-Goals

**Goals:** one workbook accountants can filter; every line traceable; deterministic bytes for reproducibility.

**Non-Goals:** payment columns; editing in this workbook (review uses a separate workbook).

## Decisions

- **Sheets:**
  - `Items`: row id, invoice, carrier, item #, category code + name, amount, derivation, evidence text, confidence band (High/Medium/Low), outcome of the row.
  - `Row Summary`: row id, invoice, carrier, disputed amount, items total, already paid, delta, outcome, outcome reason, item count, note (raw).
  - `Run Info`: run id, created, taxonomy, prompt, lexicon, model, config hash, code SHA, row counts per outcome, coverage $ and rows.
  - `Categories`: taxonomy version definitions.
- **Deterministic writing:** fixed workbook properties (creation timestamp from manifest), sorted rows, no volatile formulas, so the same predictions give the same bytes.
- **Evidence and notes** come from the raw note text in the snapshot.
- **Confidence bands** instead of raw floats to discourage over-reading; raw value in a hidden column for audits.

## Risks / Trade-offs

- [Excel row limits] → far below limits at 1,500 rows.

## Open Questions

- Does PPG want a currency column per item or per row only?
- Final table layout. The team's example sheet is not final, and a simpler layout with a largest-disputes view is proposed in `scope_alignment.md`. This change's spec is updated once the team chooses.
