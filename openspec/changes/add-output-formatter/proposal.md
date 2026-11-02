## Why

D4 defines the deliverable as an Excel file with an items sheet and a row summary sheet. Accountants must see each charge with its exact words, see which rows add up, and be able to trace any file back to the run that produced it.

## What Changes

- Write the itemized workbook: `Items`, `Row Summary`, `Run Info`, `Categories` sheets.
- Include evidence text and outcome reasons; highlight Discrepancy and Review rows.
- Stamp run id and manifest summary; register the output hash.

## Capabilities

### New Capabilities
- `itemized-output`: Excel deliverable layout, content, traceability.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.output` (openpyxl).
- Depends on core contracts, version registry, ground truth (category definitions).
