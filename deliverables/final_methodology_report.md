# Freight Analytics: methodology and current-data closeout

Team 22 / Project H | November 9, 2026

## 1. Executive result and delivery boundary

The Freight Invoice Itemizer turns carrier dispute descriptions into categorized
charge claims, stated or calculated amounts, and the exact supporting words.
The current-data implementation, evaluation, exception review and assisted
labeling are complete for the supplied export. This is a bounded delivery of a
reviewable extraction system, not a certification of payable freight expenses.
Accountants retain payment and allocation decisions.

The independent OpenAI experiment processed all 729 distinct nonblank notes and
all 1,347 source rows. On the existing 200-note reference, 189 of 197 answered
notes matched categories and amounts: 95.94%. Counting abstentions as failures
gives 189/200, or 94.5%. The original references were model-drafted; the user
attested review of all 200 separately. Neither figure establishes independently
double-labeled accuracy across the complete export. The strict result also does
not meet a 95% strict-yield requirement.

The client demo took place on November 5. Its transcript clarified that repeated
source rows come from database joins, and that the requested output is unique
charge evidence at shipment level, keyed by SAP BOL plus description. The
offline export preserves every source row while reducing repeated join records
to 1,284 shipment/description groups. Finance performs downstream invoice
allocation. Generic balances and already-paid amounts are context rather than
new expense spend.

The final review version covers 245 groups: every originally flagged group,
related descriptions and one subsequent user-confirmed interpretation. There
are 209 completed extraction reviews and 36 groups requiring unavailable
evidence. The analytical proposal holds 68 claim items, consolidates 49 repeated
fee entries, and moves 81 entries to balance context. It contains 1,249 expense
candidates and 94 context items; some candidates outside the focused review
retain their original model status. These are record counts, not approved-spend
totals or a new accuracy result.

The delivery preserves raw predictions, historical scores and human decisions.
No unresolved amount, rate, date, charge type or SAP BOL was invented to close an
exception. The work is ready for current-data handoff with disclosed limitations.
Original requirements for independent human review, client acceptance and
fresh-export validation remain unsatisfied unless their owners explicitly accept
a revised scope. This report does not record such a revision or sign-off.

## 2. Problem, source data and analytical grain

The source export describes differences between estimated and carrier-billed
freight. Its free-text notes may name accessorial charges, rate corrections,
taxes, payments, balances, weights or dates. A number occurring in a note is not
automatically a charge. The extraction task must identify what the carrier
actually states while retaining evidence and uncertainty. Whether the claim is
valid under a contract or should be paid is a separate task.

The supplied workbook contains 1,347 nonempty source rows, 729 distinct
normalized nonblank descriptions, and 18 carriers. The dataset identity is
SHA-256 e08da6c7fd6e03036d537a13ed0a52748ef81fc5cedea0df7f3ec037bc43c0e5.
Source notes and identifiers remain private. No raw workbook, source text,
predictions, credentials or review ledger is included in the public repository.

There are three useful grains. The model operates on distinct descriptions so
identical normalized notes can reuse an answer. The source-row layer preserves
the original records and row outcomes. The shipment-review layer groups SAP BOL
and description, retaining the source-row, order/invoice and shipment references
needed to audit each extracted item. These grains have different item counts;
a distinct-note item count must not be confused with its shipment occurrences.

SAP BOL comes directly from column E. It is not replaced by SHIPMENT_GID or the
carrier invoice number. The source has 1,341 text BOL cells, six missing BOLs and
1,154 distinct nonmissing BOL values. Long identifiers and leading zeros are
preserved as text. Missing BOL records remain separate review records rather
than being grouped under one blank key.

Grouping produces 1,284 description groups and removes 63 repeated join-row
occurrences from counting. A client-demo example with 24 source rows reduces to
three charge-description groups while retaining all original references.
Different descriptions can still represent repeated or revised charges. The
review layer therefore flags overlapping categories and does not simply add
every description into a financial total. Source dispute values remain available
for reconciliation, but an extraction is never edited merely to equal them.

## 3. Extraction and evidence method

The implementation separates data loading, note grouping, model providers,
structured-answer validation, source-row assignment and reporting. The taxonomy
has 19 named categories plus other_unmapped. It covers purchased transportation,
base-rate corrections, fuel, handling, detention, storage, port/drayage services,
taxes and other common freight concepts. Definitions distinguish close concepts
such as driver waiting versus equipment held for days.

Each extracted item records its category, amount, evidence quotation and
character offsets, line type and derivation. A stated amount is distinct from
a product such as days times daily rate. Date strings, BOL weights, mileage
rates and invoice totals are not treated as extra charge items merely because
they contain numbers. A missing quantity is not filled with zero, and arithmetic
does not establish that the stated days were actually chargeable.

Validation checks enforce the answer schema, permitted categories, positive
amounts, evidence spans and supported derivations. An exact quotation is an
audit aid, not proof of correct interpretation. Likewise, zero invariant
violations do not mean every charge was categorized correctly. A note that
cannot be resolved can abstain or enter a review queue rather than acquire an
invented answer. Text telling a carrier or accountant to add a fee is treated as
source evidence of a claim, not as an instruction to the AI or approval to pay.

The offline shipment exporter consumes saved note results and the source
workbook. It makes no model requests. An optional row-scoped overlay records
specific reviewed decisions without mutating the original predictions. The
overlay is bound to the source workbook hash and expected BOL/description
fingerprint. Conflicting or partially scoped corrections on joined rows fail
closed. The exporter also distinguishes real BOL values from missing-key markers.

Already-paid amounts and generic short-paid balances are exported as context.
Overlapping categories across descriptions are flagged instead of automatically
summed. The subsequent AI review supplies an explicit analytical proposal for
known repetition and ambiguity patterns. That private downstream proposal is
separate from the raw candidate CLI output. Review decisions are attributed to
the actual source: user, delegated AI recommendation or unresolved evidence.

## 4. Experiment protocol, metrics and spending control

Alejandro's original prototype, shared provisional references and the reconstructed
local split were preserved as distinct experiment records. Their membership and
freeze history cannot be combined merely because they contain similar notes.
The local readiness correction pins prompt examples to TRAIN before creating
a new split; already locked splits are not silently changed. Historical results
remain attached to the code, data, prompt, taxonomy and reference identities
under which they were produced.

The separate OpenAI candidate used the pinned gpt-5.4-mini-2026-03-17 snapshot,
medium reasoning, a 16,000-token completion limit, standard service tier and
store=false. The original source checkout remains separate so completed Gemini
and OpenAI protocols can retain their frozen source identities. New exporter
work lives on a separate development branch; a changed package hash is not
passed off as the original completed inference experiment.

The main benchmark comparison matches categories and amounts within one cent.
Answered-note agreement excludes abstentions from its denominator; strict yield
includes every reference note. Row coverage includes covered discrepancies,
which means a row can count as covered while still requiring manual attention.
Dollar coverage is not dollar correctness or the percentage of dollars approved
for payment. Weighted figures depend on the population and weighting rule and
must be identified separately from unweighted note agreement.

The user authorized a maximum of $5 total for OpenAI evaluation. A persistent
shared ledger reserves a conservative maximum before each paid request and
settles it against metered usage. Unknown costs retain their reservations.
The completed experiment used $1.05022950, including development checks and
validation retries; no unsettled reservations remained. The cap does not cover
unrelated activity in the same account. Review, labeling and shipment exports
after that run used saved results and made no additional model/API requests.

The 50-note assisted-label pass was finalized and hashed before reading its
corresponding saved predictions in that pass. However, inference on the old
export had already occurred and the assistant had project context. This is not
a new independent blind evaluation. Human substitutions and policy corrections
are not credited as an improvement to the original model benchmark.

## 5. Completed evaluation and practical limits

The benchmark returned 197 answers and three abstentions. It matched 189 notes
exactly on category and amount. Answered-note agreement was 95.94%, with a 95%
Wilson interval of 92.19%-97.93%. Strict yield was 94.5%. Reference-stratum
row-weighted agreement was 96.41%, with a weighted bootstrap interval of
93.15%-98.80%. These estimates describe agreement with the existing reference,
not a statistically guaranteed floor for future production accuracy.

The benchmark's eight answered disagreements included category and amount
errors, a missing item and an extra item. Performance was weaker on difficult
subsets: large-dispute row-weighted agreement was 85.29%, and unseen-format
agreement was 48/54, or 88.89%. The overall benchmark exceeds the user's 90%
target, but those subgroups do not establish a 90% floor. A 95% strict-yield
acceptance target is not met by the 94.5% strict result.

The full sweep completed 729 distinct notes and 1,347 source rows. Row outcomes
were 1,084 verified, 12 no-charge, 240 discrepancy and 11 review. Coverage was
1,336/1,347 rows, or 99.18%, and reported disputed-dollar coverage was 99.19%.
Only 1,096 rows, or 81.37%, were accepted without reading under that run's row
rules. Their disputed dollars represented 49.57%, illustrating that high overall
coverage can coexist with substantial high-value exception exposure.

There were 879 verifiable distinct-note items in the full sweep and no invariant
violations. All benchmark predictions were identical when reused in the sweep.
The complete run establishes processing coverage, not independently verified
accuracy on the 529 notes outside the existing 200-note reference. An all-scope
weighted approximation is therefore not used as the headline accuracy result.

The later shipment and assisted-label reviews change the analytical treatment of
some claims and balances without rewriting these historical measurements. In
the 50-note assisted pack, 44 named-fee notes agree with saved expense outputs;
six balance-context treatments differ under the reviewed policy. That comparison
is neither an independent 88% accuracy estimate nor a new passing benchmark.
It identifies policy differences that belong in the reviewed output and report.

## 6. Review, assisted labels and exception decisions

The first priority pass recorded 18 note-level cases using explicit user answers
or delegated recommendations. It distinguished already-paid amounts from
outstanding balances, preserved duplicate source rows, confirmed stated tax,
hazmat and other fees, and deferred unsupported rates, categories and revisions.
Subsequent source auditing retained invoice dossiers rather than fabricating
payment histories or assuming row order established chronology.

At shipment grain, the original export flagged 189 groups. Review included those
groups, related descriptions, 80 purchase-fee headings with only balance-due
amounts, and a later user-confirmed balance interpretation. The final scope is
245 groups: 209 extraction reviews completed and 36 requiring external evidence.
The unresolved groups are consolidated into 21 shipment/invoice evidence
requests. No request was sent automatically and no reply is assumed.

The separate analytical proposal consolidates 49 repeated fee entries with the
same reviewed BOL/invoice/category/amount across alternate descriptions. It
preserves all original claims and canonical references in the audit. This is a
review proposal, not a universal rule that every equal amount is the same fee.
Two item ordinals in one note are not collapsed. Taxes tied to different named
fees remain separate. Explicitly conflicting fee versions are held, not added
together or assigned an unsupported latest version.

The 50-note labeling pack contains 45 expense-claim items across 44 notes and six
balance-context notes. Exact evidence quotations were checked. The user made
one explicit interpretation decision, recorded separately and propagated to the
updated proposal. The other labels were authored by the AI assistant. The pack
is complete as AI-assisted labeling; it is not evidence of two independent human
readers, nor is one user answer approval of every label or client sign-off.

Because missing information is unavailable, the proposal excludes 68 held claim
items rather than repeatedly asking the user to guess. Missing BOLs, ambiguous
rate/day evidence, detention type and revised fee amounts remain disclosed.
There are 1,249 proposed expense candidates and 94 context records. Candidate
records outside the focused review retain a model-candidate status. No mixed
currency financial grand total, validated invoice liability or automatic payment
decision is produced.

## 7. Reproduction, verification and handoff

The repository contains the source, configuration, synthetic-data tests, report
and rerun guide. Private inputs and outputs live under ignored data/. The
existing-data shipment export can be reproduced offline from the source workbook,
saved all-scope note results and optional source-bound overlay using
python -m itemizer.shipment_review. The detailed command, input layout and
expected counts are in deliverables/final_rerun_guide.md.

Saved inference should be audited in its matching frozen checkout. Resuming an
old experiment from changed source can correctly fail protocol checks; it is
not a reason to weaken those checks or copy a new hash over the old protocol.
A new experiment needs its own identity and an explicit budget/authorization
decision. Cached, paid and reviewed phases must remain distinguishable.

The private handoff has two layers. The raw shipment candidate export supplies
1,284 description groups and all source links. The later reviewed workbook adds
the completed assisted labels, review decisions, proposed candidates, context,
claim audit and source rows. The original raw export is not overwritten. The
AI review and assisted-label analysis scripts and their input hashes are saved
privately because their concrete decisions refer to confidential source cases.
Repository collaborators need those artifacts through an approved private
channel to reproduce the exact reviewed snapshot; Git alone is insufficient.

Verification covers join-row collapse, distinct shipment identities, missing BOL
isolation, source import, stale/partial overlays, repeated item ordinals and
balance treatment. Review fixes were tested with invented notes, including a
balance item whose evidence quotes only its amount. Export checks read back all
source BOL values as text, preserve leading-zero invoices, account for every
claim item, check canonical references and confirm that user decisions reach
the downstream output. Workbook tabs were rendered for visual inspection.

The final closeout runs the complete automated test suite and records its result
in the repository handoff. Credentials, private notes and generated workbooks
are excluded from the public push. No inference run or additional API spending
is necessary for this verification. A successful technical test run establishes
software behavior; it does not manufacture contractual acceptance evidence.

## 8. Limitations, acceptance and closure

The delivered version is bounded to the supplied export and recorded review
decisions. Carrier descriptions express claims, not necessarily contractually
valid charges. A convincing quotation, correct arithmetic or a reconciled source
delta does not prove a service occurred or a fee was payable. The held items are
excluded from the proposed expense candidates, but the evidence and unknown
values remain available for a future reviewer. This is preferable to silently
filling missing information or declaring every source row settled.

Three original acceptance conditions remain external. The scope calls for
independent human labeling/review, client acceptance and validation on a genuinely
new export. The existing assisted pack cannot be renamed to satisfy the first;
the November 5 demo cannot automatically satisfy the second; repeated testing
on the inspected old export cannot satisfy the third. An authorized client/course
owner may agree a revised scope accepting these limitations, but no such
agreement is invented or recorded by this closeout.

There is no pending freight-interpretation question for the user in the completed
50-note pack. The requested source judgments have been resolved or the missing
facts explicitly marked unavailable. The remaining decision is whether the
owners accept the current-data deliverable with its documented exclusions and
AI-assisted provenance, or require the original validation milestones before
formal acceptance. The final code/report handoff can proceed without claiming
that those milestones occurred.

Historical evidence is summarized in deliverables/openai_evaluation_results.md,
deliverables/shipment_review_handoff.md and deliverables/ai_review_2026-11-09.md.
The private dataset, experiment protocols, case decisions, review ledgers and
label-lock hashes support the aggregates reported here. The November 5 meeting
record supports the shipment-level output requirement. The public rerun guide
explains which private inputs a collaborator must obtain separately.

The result is a reproducible prototype with completed current-data processing,
explicit evidence, a reviewed analytical proposal and a transparent exception
boundary. The delivery does not promise that all future formats exceed 90%,
claim a 95% strict pass, or authorize automated settlement. Future work should
begin with real new data and independent labels, using a new experiment version
rather than optimizing against the repeatedly inspected benchmark.
