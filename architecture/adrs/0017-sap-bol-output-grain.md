# 17. One output line per charge per SAP BOL

Date: 2026-11-09

## Status

Accepted. Decided by the client at the D3 review on 5 November 2026. Amends the workbook layout in [14. D3 as a thin path](0014-d3-thin-path-controlled-grammar-model-registry.md). Row results and the KPIs do not change.

## Context

The export repeats rows because PPG's query inner-joins a shipment with each of its invoices and each of their charges. The repeats mean nothing. On the sample export, 1,347 rows hold 1,281 distinct charges, and disputed dollars fall from $186,345 to $126,700 once the repeats go. The workbook showed one line per export row, so a finance analyst summing it would count the same charge many times.

## Decision

The workbook shows one line per SAP BOL (column E) and description, with no allocation across shipments; finance analysts allocate, for example by weight. Invoice/Bill ID (column D) is listed on each line but is not part of the key. A blank SAP BOL uses the shipment ID. A line takes the outcome its note and disputed amount give, without the repeat flag, and lists the export rows it came from. Lines on one SAP BOL with the same billed and disputed amounts but different notes are flagged as possible double counts, and left in.

Alternatives considered:

- Keep one line per row with a `repeated` flag: no change, but every sum over the sheet overstates spend.
- Key on SAP BOL and disputed amount: it would merge two different charges that happen to cost the same.
- Allocate each charge across a shipment's invoices: the client said allocation stays with finance, and the method varies.

## Consequences

- `Items`, `Charge Summary` and `Largest` change; the per-row `Row Summary` goes. Each line lists its export rows, so nothing is lost.
- KPIs, Level gates and the TEST budget still use row results, so this change spends no TEST budget.
- The repeated-invoice question (Q-5) mostly goes away for the workbook, because the repeats it flagged collapse into one line.
