## Why

At the 5 November meeting the client corrected the output: the export repeats rows because PPG's query inner-joins shipments, invoices and charges, and the repeats mean nothing. On the sample export, 1,347 rows hold 1,281 distinct charges, and disputed dollars fall from $186,345 to $126,700 once the repeats go. The client asked for SAP BOL (column E) as the primary key, one line per unique charge per SAP BOL and description, and no allocation, which stays with finance analysts. Invoice/Bill ID (column D) is secondary.

## What Changes

- **Read two more columns:** `SAP BOL` and `Invoice/Bill ID`, when the export has them.
- **New output grain:** the workbook shows one line per SAP BOL and description. Rows that repeat a line collapse into it, and the line lists the export rows it came from.
- **Sheets:** `Items` and a new `Charge Summary` replace the per-row `Items` and `Row Summary`. `Largest` ranks SAP BOLs, and its total counts each charge once.
- **Possible double counts:** a line that shares its SAP BOL, billed amount and disputed amount with a differently worded line says so.
- **Unchanged:** row results, KPIs, Level gates and the TEST budget. They measure the itemizer, not the layout.

## Capabilities

### New Capabilities
- `sap-bol-output-grain`: the output's grain, its key, and how repeats and possible double counts are shown.

### Modified Capabilities
<!-- none in openspec/specs: the workbook requirements in add-d3-thin-path's d3-output are edited in place, as earlier changes did. -->

## Impact

- `bootstrap/data.py` and `contracts.py`: `DisputeRow` and `RowResult` carry `sap_bol` and `bill_id`; `RowResult` also carries `billed`. The JSON Schemas are regenerated.
- `output.py`: grouping, the new sheets and `Largest` by SAP BOL. `acceptance.py` shows the new `Largest` columns.
- `pipeline.py`: `Run Info` records the grain and the number of charge lines. A run written before this change gets a plain message from `evaluate`.
- ADR 0017 records the decision.
