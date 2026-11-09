# Live check

Aggregates only, with no note text. Run on 2026-11-09 from commit `537763c`, on all rows of the dataset file.

| Check | Result |
|---|---|
| Model calls | None: all 729 answers came from the cache, at $0.00 |
| Rows in, lines out | 1,347 rows became 1,281 lines, and the lines list all 1,347 rows |
| Disputed dollars | $186,345.02 on the rows, $126,699.80 on the lines |
| Largest repeat | 8 rows with 8 bill IDs collapse into one line, on a SAP BOL whose 24 rows hold 3 charges |
| Possible double counts | 42 lines share a SAP BOL, billed amount and disputed amount with a differently worded line |
| Blank SAP BOL | 3 lines group by shipment ID |
| Line outcomes | 1,174 verified, 87 discrepancy, 11 review, 9 no charge stated |
| Row outcomes | Unchanged: 1,097 verified, 227 discrepancy (136 repeated invoices), 14 review, 9 no charge stated |
| Largest dispute | One SAP BOL ranks first with 2 charges on 6 rows: largest 8,400.00, total of charges 16,400.00 |
| Scoring the new run | `evaluate` reports `rescored`: the answers match a run already scored, so no TEST budget is spent. Levels 1 and 2 read as before |
| Status page | `acceptance d3` shows the Largest table by SAP BOL |
