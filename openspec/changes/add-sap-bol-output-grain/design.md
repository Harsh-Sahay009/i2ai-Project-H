## Context

Component: Output Formatter. Placement: **common core**, because the grain is part of the output contract and no setting changes it. Position: **owned**. Authority: **recommend**; the workbook shows what the tool found and decides nothing.

The client decided the grain on 5 November 2026 (ADR 0017). Row results stay at the export's grain, so the KPIs, the Level gates and the TEST budget do not move.

## Goals / Non-Goals

**Goals:** one line per unique charge per SAP BOL, with no allocation; every line traceable to its export rows; possible double counts visible.

**Non-Goals:** allocating a charge across shipments, deduplicating across SAP BOLs, changing the KPIs to the new grain.

## Decisions

### The key

A line's key is the SAP BOL and the note's fingerprint, the SHA-256 of the note with whitespace and case normalized, so notes that differ only in spacing are one description. A blank SAP BOL uses the shipment ID. An export without the column groups by shipment ID, and `Run Info` says so. Rows with the same key but a different disputed amount are not repeats of one charge, so each amount keeps its own line. Blank notes group by SAP BOL too. Lines keep the order of their first export row, so the same inputs give the same file.

### A line's outcome

Every row of a line shares one note result and one disputed amount, so they reconcile the same way. A row is marked `repeated_invoice` only because PPG's `Invoice Dups Removed` column zeroes every row after a shipment's first, including rows for other charges. Collapsing the rows is what removes the repeats, so a line takes the outcome its row would have without that flag. `review.repeated_invoice_policy` still applies to row results.

### Sheets

| Sheet | One line per | Columns |
|---|---|---|
| `Items` | Charge item on a line | `charge_id`, `sap_bol`, `shipment`, `item`, `category`, `amount`, `evidence`, `outcome`, `ai_reason`, `description` |
| `Charge Summary` | SAP BOL and description | `charge_id`, `sap_bol`, `shipment`, `bill_ids`, `carrier_invoice`, `carrier`, `status`, `reason_code`, `disputed`, `items_total`, `already_paid`, `difference`, `outcome`, `outcome_reason`, `rows`, `row_ids`, `same_amount_as`, `description` |
| `Largest` | SAP BOL, largest dispute first | `rank`, `sap_bol`, `shipment`, `charges`, `rows`, `largest_dispute`, `total_of_charges`, `share_of_total`, `cumulative_share`, `outcome`, `main_category` |

`charge_id` is `C` plus the line's position. `bill_ids` lists the distinct Invoice/Bill IDs of the line's rows. `Largest` still ranks by each SAP BOL's largest dispute, counted once, because two lines on one SAP BOL can be the same dispute described twice. `total_of_charges` sums its distinct lines.

### Possible double counts

`same_amount_as` lists the other lines on the same SAP BOL with the same billed and disputed amounts. Those are one invoice line described in two ways, or two charges that happen to match; only a person can tell. On the sample export, 42 lines carry it. Nothing is removed or allocated.

### Contracts

`DisputeRow` and `RowResult` gain `sap_bol` and `bill_id`, empty by default, and `RowResult` gains `billed`. Run folders written earlier still load. `evaluate` rebuilds row results from the export and compares them with the stored ones, so a run written before this change would read as tampered with. It gets a plain message instead: run again, at no model cost, and scoring the same answers stays free.

### Telemetry and versions

Nothing new is recorded. The code hash changes, so a run after this change gets a new run id. Its answers come from the cache, and the TEST budget follows what was scored, so scoring it costs no budget.
