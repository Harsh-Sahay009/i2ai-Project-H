# Shipment-level review export

The November 5 client-demo transcript clarifies the requested analytical grain:
SAP BOL (column E) plus description. Repeated join rows do not represent multiple
expenses. Keep invoice/order IDs as evidence; finance performs allocation later.

Implementation sequence:

1. Read SAP BOL as text directly from the original workbook. Reject numeric BOLs
   rather than silently losing leading zeros. Preserve every source row.
2. Collapse repeated descriptions within a BOL. Isolate missing BOLs by row ID.
3. Reuse saved predictions offline. Apply explicit, row-scoped human decisions
   in a separate private overlay. Leave original scores and predictions intact.
4. Separate outstanding balances and already-paid amounts from expenses. Retain
   multiple item ordinals; do not collapse distinct fees with equal amounts.
5. Flag overlapping categories across descriptions for revision review. Do not
   calculate a financial grand total or allocate charges across invoices.
6. Export JSON/CSV and a private client review workbook with row-level evidence.
7. Test grouping, missing identifiers, overlays, source import and persistence;
   verify all 1,347 source rows and the client's 24-row example.

Acceptance distinguishes a reproducible extraction from approval to pay. Client
review, independent human reference labeling and a genuinely new export remain
external acceptance steps. Invoice-level reconciliation is an audit follow-up,
not a prerequisite to producing this shipment-grain review export.
