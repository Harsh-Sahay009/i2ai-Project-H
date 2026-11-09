# Team 22 — Freight Analytics progress update

Prepared November 8, 2026. Working report for the team; not submitted or sent.

## Progress against scope

The project converts freight-dispute descriptions into itemized charge
categories, amounts and supporting source words. Accountants retain payment
decisions. The working pipeline loads the supplied export, validates structured
model answers, retains evidence and produces item/row results.

An independent OpenAI comparison and complete source-data run have finished:
729 distinct descriptions across 1,347 rows. Against the existing 200-note
reference, 189 of 197 covered notes match category and amount (95.94%); the strict
result including three abstentions is 189/200 (94.5%). These are reference
agreement figures, not a claim that every source row has independent human
ground truth. Existing reference corrections are retained separately.

Eighteen priority notes have been reviewed through explicit user decisions or
delegated recommendations. The remaining exception rows have been triaged with
source links and follow-up evidence needs. A deferral is not silently converted
into an accepted charge. The original predictions and benchmark remain intact.

## Working prototype and client feedback

The November 5 demo and subsequent transcript are available privately. The
client explained that repeated rows arise from joins across underlying orders.
The requested analytical grain is SAP BOL (column E) plus description, keeping
one instance of each charge per shipment. Finance will handle invoice allocation
later. Generic balances belong in context rather than expense spend.

The new offline exporter implements that grouping. It retains all 1,347 source
rows in traceability while producing 1,284 shipment/description groups and
removing 63 repeated join-row occurrences from counting. Six missing-BOL rows
remain separate. The review output has 1,447 expense candidate items, 13 balance
context items, and 189 flagged groups. Candidate items can include unresolved
amounts/categories; these counts do not imply acceptance or additive totals.

A private Excel workbook includes expense candidates, balances, shipment groups,
source-row evidence and blank reviewer fields. The client's 24-row example
collapses to three description groups with all source links retained.

## Blockers and decisions

Required independent two-reader labeling, client reference review and written
acceptance evidence must be completed or documented by the actual reviewers.
The demo record does not certify those gates. Ambiguous rate/day counts,
detention types, revisions and missing identifiers require source evidence.
Invoice-level allocations are outside the corrected export's immediate scope.

A genuinely new export is still needed for final unseen-data validation. The
existing benchmark has been inspected, so corrections must not be presented as
new blind test performance. The final methodology report must distinguish
reference agreement, human corrections and independently validated results.

API spend is $1.05022950 of the authorized $5 total. The shipment review work
uses saved results and makes no model requests. Sensitive input, output and
review evidence remain outside the public repository.

## Scope and next work

The client feedback refines output grouping and treatment of balances; it does
not request payment approval or order-level allocation. Next: client review of
the corrected shipment workbook, independently reviewed labels, a new export,
then final acceptance and the methodology/rerun handoff. Existing model scores
must remain attributed to their original frozen experiment.

## Repository and project board

- Repository: <https://github.com/Harsh-Sahay009/i2ai-Project-H>
- Merged evaluation work: <https://github.com/Harsh-Sahay009/i2ai-Project-H/pull/7>
- Shipment exporter branch: `codex/shipment-review` (local working branch).
- Board: <https://github.com/users/Harsh-Sahay009/projects/4/views/1>

The actual board snapshot read November 8 contains 25 items: **1 Done,
3 In progress, 5 Ready, 16 Backlog**. Several cards still label implemented or
demonstrated work as Backlog; the board is stale and these are its observed
statuses, not a fabricated completion snapshot. Suggested reconciliation:
prototype, exact evidence and demo cards should link their actual evidence;
evaluation cards must retain the human-label/acceptance caveat. D2 independent
labeling, fresh-export validation and final reporting remain open. No board
statuses or assignments have been changed by this report.
