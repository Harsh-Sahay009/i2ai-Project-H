# Harsh's TP2 responsibilities: evidence and review status

November 15, 2026. Covers issues #14, #20 and #22 on the latest SAP BOL branch.
No inference, prompt tuning or additional model spending was needed.

## Updated client evidence

Jake's November 10 written reply approves progression to Phase 3 and confirms
the shipment identifier/aggregation direction. Another client approval meeting
is not needed to establish that permission. It does not prove that every label
or every scope-change checklist item has been separately approved.

The November 13 clarification, forwarded to this team by Justin, changes several
data assumptions. Invoice Amount, Invoice Dups Removed and Delta were rough
calculations, not authoritative reviewer labels. The task is to improve those
calculations using source claims and the original Shipment Amount. Amounts may
be treated as USD; tax is a separate line item. Multiple orders can share one
SAP BOL, so join repetitions are not additional shipment charges. The source
messages and attached client-note workbook remain internal.

These instructions postdate the November 9 methodology report. Its historical
run statistics remain intact; statements about approval status, unknown currency
or a Delta mismatch requiring an invoice correction must be read with this
addendum. A Delta mismatch alone is not evidence that the AI amount is wrong.

## #14: balance-due interpretation settled for the label review

| Source wording or situation | Review policy |
|---|---|
| Named charges followed by a balance or total | Extract each stated charge once; retain the balance as context, not another expense. |
| A fee heading followed only by BALANCE DUE | Preserve the balance and category hint; do not invent a separately stated expense amount. |
| A balance explicitly identifies a specific claim, such as fuel or a rate correction | Preserve the named claim and its stated amount; the word balance alone does not erase a clearly identified claim. |
| An amount is already paid, approved as an invoice total, or described as overpayment | Preserve the context. Do not manufacture an additional payable charge or a signed credit. |
| Quantity and unit rate are given with no total | Record their product as the claimed amount, with both source numbers in the evidence. |
| A stated total is given as well | Preserve that stated claim and flag contradictions; do not force it to match Delta. |
| Charge type, rate unit or amount cannot be determined | Preserve known facts and an explicit unknown; do not substitute zero or guess a category. |

On November 15, Harsh explicitly confirmed that two dwell days at 300 should
be labeled as a 600 claim, with payment unverified. That supersedes the earlier
deferral based only on the source Delta of 300. The three affected reference
notes have proposed amount corrections in a separate overlay. The old frozen
prompt and predictions are not rewritten or re-run to conceal the discrepancy.

This resolves the technical labeling policy in #14. It does not silently edit
the deployed prompt: any subsequent prompt/model change needs a new version and
the existing review/tuning discipline. Missing source information remains unknown.

## #22: hazmat and lumper/GST cases verified

The actual shared Opus workbook, `Itemized_Output_SAP_BOL_2026-11-09.xlsx`, identifies
run `run_816a1969ea3d1581` and matches the source workbook hash. Readback confirms:

| Source rows | Existing Opus output | Decision |
|---|---|---|
| 29 and 30 | One 150 hazmat item per shipment; BOL weights stay in description text. | Correct for the reported cases. |
| 35 and 36 | One joined shipment/description line with 60 handling plus 3 GST; total 63. The gross 63 is not a third item. | Correct extraction and join handling. |

The lumper line retains a legacy Delta discrepancy because the old worksheet
value is 126. Jake's clarification means that flag is not proof that the 63
source extraction is wrong. It must not be repaired by adding another 63 fee.

The saved OpenAI output independently has the same categories/amounts for these
four source rows. Two invented-note regression tests now guard the output:
hazmat charge versus weight, and joined handling/GST versus the gross total.
The output test module passes 104 tests. No prompt change was necessary for the
reported samples. This completes the investigation requested by #22.

## #20: actual 200-note draft review completed as an assisted proposal

This pass uses the original received `test_provisional.json`: 200 notes and 279
draft items. It is not the separate 50-note supplemental pack. All 200 note
fingerprints match the source and the shared Opus output. The received label
bytes are preserved, and every proposed evidence span is checked against the
source note. Private artifacts bind the label file, source export and Opus
workbook with SHA-256 hashes.

| Review result | Count |
|---|---:|
| Notes reviewed | 200 |
| Complete source-based assisted proposals | 193 |
| Notes with an explicit remaining source ambiguity | 7 |
| Proposed expense-claim items | 256 |
| Context records | 17 |
| Uncertain claim records | 7 |
| Notes with a role, amount or uncertainty change | 24 |
| Dwell-amount corrections | 3 |

The seven ambiguities concern generic detention subtype, the meaning/type of a
reweigh or weight adjustment, and a bare FSC decimal that could be a rate rather
than a total amount. The packet keeps the supported parts and unknown fields;
it does not ask the user to invent unavailable facts. Source amounts are claims,
not proof of payment validity or incremental expense over a revised base.

The review is explicitly AI-assisted. Harsh's earlier overall reference-review
attestation and specific case answers remain separate provenance. No record
claims two independent human labelers, 200 new item-level human confirmations,
or Jake's completed 50-note review. The workbook has blank, editable fields for
real reviewer identity, acceptance/correction and comments.

### Same-run check and reporting correction

Reconstructing categories and amounts from the actual shared Opus workbook
reproduces 192 matches among 195 answered reference notes, with five abstentions.
That is **98.46% exact answered-note agreement** and **96.00% strict yield** over
200 notes. The historical **99.3% is weighted agreement**; it is not the direct
fraction 192/195. Table 2 in the progress report should label the weighted figure
and the exact count separately. The large-dispute weighted figure and its raw
fraction similarly require distinct denominators.

A diagnostic comparison against resolved, expense-only proposals is saved
privately, with policy-changed context cases and ambiguous cases excluded and
their exclusions explicit. It is not a replacement full-TEST score or a new
human-verified accuracy claim. The original category/amount outputs do not
establish every semantic field needed to re-score the complete acceptance gate;
the original experiment's matching private records still matter (#19).

### Private handoff and remaining responsibility

The review file is
`data/outputs/tp2-owned-review-2026-11-15/TP2_200_Note_Review.xlsx`.
It contains Review200, item decisions and the unchanged original draft, with a
summary and exact evidence. It must be shared internally, not committed here.
The machine-readable proposal, baseline comparison and hashes are under
`data/evaluation/tp2-owned-review-2026-11-15/`.

#20 remains in review because its human/client acceptance conditions have not
been established. The technical review packet is complete. Real reviewers must
confirm or correct the proposed decisions, or the client/course owner must
explicitly accept assisted review and retained unknowns. Justin coordinates
Jake's required 50-note review under #31. No human identity or approval event is
invented to close an issue.

## Suggested corrections to the team's three-page report

- Section 3 / Table 4: balance policy and hazmat/GST checks completed; all 200
  drafts now have an AI-assisted review proposal (193 complete, seven explicitly
  ambiguous). Human verification and Jake's 50-note review remain open; retain
  the November 20 / November 24 ownership unless the team changes it.
- Client meeting / scope: add Jake's November 10 written Phase 3 approval and
  November 13 amount-field/USD clarification. Do not describe a new approval
  meeting as a TP2 prerequisite.
- Table 2: label 99.3% as weighted; show 192/195 = 98.46% if giving the exact
  fraction. Do not call assisted reference agreement validated human accuracy.
- D5: a methodology draft and rerun guide already exist in the repository for
  Rachel to integrate; do not retain an unqualified statement that writing has
  not started. The November 9 report needs this newer-source addendum.
- Agentic component: describe the existing check/retry loop as implemented and
  the five-tool agent/guardrails as planned under #32 unless implementation is
  separately verified. Rachel's course-interpretation question #23 and the
  submission owner should be confirmed before the submission deadline.

This addendum is evidence for the team to incorporate. It does not overwrite
Alejandro's report, send email, publish confidential attachments or claim that
the assignment has been submitted.

## Verification

The latest branch passes **1,062 tests in 277.50 seconds**, including 104 output
tests and the two new invented-note regressions. Private workbook readback checks
all 200 note identities, 280 proposed item/context/uncertainty records and 279
unchanged original draft items. Evidence spans, original-file hash, blank human
fields and the three 600 dwell corrections were verified. No inference was run.
