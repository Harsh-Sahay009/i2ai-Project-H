# Shipment review handoff — November 8, 2026

## Current result

The saved OpenAI evaluation covers all 729 distinct notes / 1,347 source rows.
Against the existing 200-note reference, category-and-amount matches were
189/197 covered notes (95.94%); counting abstentions as failures gives 189/200
(94.5%). These are comparisons to the existing reference, not independently
verified accuracy across every row. Reference decisions have since been reviewed;
the original benchmark and saved predictions remain unchanged.

The November 5 demo occurred. Its meeting transcript requests shipment-level
output keyed by SAP BOL plus description, counting repeated join rows once.
Invoice/order IDs remain traceable; allocation is handled by finance. Generic
balances are context, not additional expense spend. This changes the next output
priority from invoice reconciliation to shipment-level review.

## Reproduce the corrected output

Use the `codex/shipment-review` checkout. Inputs and outputs are private and
Git-ignored. The command makes no model/API calls:

```bash
PYTHONPATH=src python -m itemizer.shipment_review \
  --source 'AutoPay Dispute Data 20220815_withExamples.xlsx' \
  --predictions data/evaluation/openai-mini-v1/all/note_results.json \
  --overlay data/evaluation/human_adjudication/shipment_overlay_v1.json \
  --output data/evaluation/shipment-review-v1
```

Omit `--overlay` to reproduce raw model candidates. The optional overlay is keyed
by source row ID, bound to the source workbook SHA-256 and expected BOL/description
fingerprint, records decision-file provenance, and must cover all joined
rows consistently. Deferred amounts/categories remain unresolved. No human
substitution is counted as an improvement to model accuracy.

JSON preserves identifiers and all source rows exactly as loaded. CSV files are
interchange files: import identifier columns explicitly as text to preserve
leading zeros. Use the typed Excel review workbook for ordinary client review.

## Review workflow

1. Open the expense candidates and filter flagged groups. Check SAP BOL,
   description, category, amount, evidence and the linked source rows.
2. Resolve possible revisions/overlaps between different descriptions. Repeated
   identical BOL/description rows are collapsed; distinct descriptions are not
   automatically treated as additive charges.
3. Confirm the six missing BOL records separately; never merge all blanks.
4. Review balances separately. A stated outstanding balance is not a second
   expense; already-paid amounts are not new spend. No payment approval is implied.
5. Record reviewer identity, decision and supporting evidence. Keep the original
   predictions and benchmark immutable. Save reviewed corrections separately.

## What remains

- Client review of the corrected shipment output and written acceptance of the
  applicable D3 gate. A demo record does not itself certify that gate.
- Complete/document the required independent two-reader blind labels and client
  reference review. The exposed benchmark cannot serve as fresh blind validation.
- Resolve ambiguous categories, rates, revisions and missing identifiers where
  supporting documents are needed. Do not block the entire shipment deliverable
  on allocating every invoice balance.
- Obtain a genuinely new export and run final held-out acceptance for D4/D5.
- Finish the methodology/final handoff around those verified results.

API spend remains $1.05022950 of the authorized $5 cap. This shipment export is
offline; it adds no model charges. Private workbook data and review evidence must
remain outside the public repository.
