# Scope alignment check: architecture and OpenSpec vs. the scope statement

* **Date:** 2026-11-02
* **Baseline:** `Freight_Analytics_Scope_Statement 2.pdf` (v1.0, 1 Oct 2026), plus one stated change: the Web UI is now in scope.
* **Compared against:** `architecture/` (C4 model, docs 01-10, ADRs 0001-0010), `Architecture Diagram - i2ai project.pptx`, and all 20 changes in `openspec/changes/`.
* **Status:** first pass by one reviewer. No Goldfish review has run yet.

## Verdict

**They do not match, and the UI is not the only difference.** The product rules line up with the scope. The amount of work, the schedule, the use of PPG time and some of the deliverables do not.

## Update after seeing the data file (same day)

The team added `AutoPay Dispute Data 20220815_withExamples.xlsx`. Every partition comes from this file, and its `Sheet1` shows the desired output, which is not final. This repo is public, so this section uses aggregates and invented examples only. The file is now in `.gitignore`.

Decisions since the update below: all three UI actions must work in the browser, so the UI is plain HTML from a thin server (ADR 0011), not static pages. The fix plan in §9 is done.

### What the file shows

| Finding | Evidence |
|---|---|
| It matches the scope's client export | 1,347 rows, 18 carriers, $186,345 in deltas, May 2021 to Aug 2022, same file name and date |
| The team confirms it is free, open and public, though not fully anonymized | 15 emails in 3 rows; at least 42 phrases that look like names; 1,264 of 1,341 destination addresses start with a street number |
| Nearly half the dollars are on repeated-invoice rows | 192 rows hold $89,372 (48%); without them the total is $96,973 |
| A few shipments dominate | One shipment holds $49,600 (26.6%) on 6 rows, with a largest dispute of $8,400; four shipments hold 46.3% |
| No ID identifies a row | `PK` and `Invoice/Bill ID` are blank on 467 rows; shipment + PK still repeats on 149 keys |
| Notes repeat in format | 729 distinct notes form 173 formats, and the top 10 formats cover 883 rows |

**Runtime with real numbers:** at 729 notes and 4 turns per note, 4 parallel slots allow 2.47 seconds per turn within 30 minutes.

### Problems in `Sheet1`

| Row | Problem |
|---|---|
| 5 | `expense` is 27.5, but the evidence says 27.05. This is the error the "never edit an amount" rule exists to prevent |
| 5 | The note totals 28.40 and the row's delta is 56.80, so this row is a Discrepancy. The table has no column to show that |
| 5 | `type_expense` is "BALANCE DUE", which is a position in the note, not a kind of charge. The note says it is a fuel surcharge |
| 6 | The shipment ID is not in the file, and `itemid` is empty. It looks like an Excel drag-fill of row 5's IDs |
| All | `id2` always equals "PPGTM." + `id3`, so one of them is redundant |
| All | No outcome column, although the scope requires Verified, Discrepancy or Review |
| 3 | `AI reason` is filled once and cannot be checked against the note |

### Proposed output

`Items`, one line per charge (7 columns instead of 11):

| row_id | item | category | amount | evidence | outcome | ai_reason |
|---|---|---|---|---|---|---|
| R0007 | 1 | Lumper | 60.00 | LUMPER $60.00 | Verified | |
| R0007 | 2 | Stop fee | 12.00 | STOP FEE $12.00 | Verified | |
| R0007 | 3 | Tax | 3.60 | GST $3.60 | Verified | |

`Row Summary`, one line per dispute: `row_id`, `shipment`, `carrier_invoice`, `carrier`, `status`, `reason_code`, `disputed`, `items_total`, `difference`, `outcome`, `outcome_reason`, `repeated`, `note`.

`Largest`, one line per shipment, sorted by dollars: `rank`, `shipment`, `rows`, `largest_dispute`, `total_on_rows`, `repeated_rows`, `share_of_total`, `cumulative_share`, `outcome`, `main_category`.

Why this layout:

- `row_id` replaces the three IDs. `shipment` drops the constant "PPGTM." prefix, and `carrier_invoice` maps one-to-one to it.
- `type`, `type2` and `original` move to `Row Summary`, so they do not repeat on every item.
- `category` comes from the approved D1 list, and the note's own words stay in `evidence`.
- `ai_reason` is filled only when a category is uncertain, so it does not read as a check on correct rows.
- `Largest` counts by shipment. Ranked by row, one $8,400 dispute would appear six times and look like $49,600.

## Update after team input (same day)

The HTML recommendation below assumed some actions could leave the browser. The team needs all of them in the browser, so ADR 0011 uses a thin server instead.

The team reports:

* The architecture folder has been reviewed and is the source of truth.
* The UI should be HTML, not Streamlit.
* Course and atlas work are internal check-ins that Jake does not need to approve.
* PPG data is open this time, so there are no privacy concerns.
* A clear train / validation / test split is needed.

Three of these contradict the architecture folder, so this check treats it as the source of truth **except for these three changes**:

| Change | What it overrides |
|---|---|
| HTML instead of Streamlit | ADR 0007, `workspace.dsl`, `docs/01`, `openspec/config.yaml`, `add-web-ui`, `add-kpi-dashboard/design.md` |
| Train / validation / test split | ADR 0003, ADR 0004, `workspace.dsl`, docs 02-09, and the changes that read DEV |
| Open data | The scope's confidentiality clause, ADR 0003, ADR 0007, ADR 0009, `workspace.dsl`, `openspec/config.yaml`, and the docs that assume confidential data, chiefly `docs/05` and `docs/09` |

### Status of the original findings

| Finding | Status |
|---|---|
| §1 Jake's approval of course and atlas work | Closed, except the skill folder and MCP tools that `docs/08` §8.6 hands to PPG. Those are not internal if they are delivered. |
| §1 and §2 Size and schedule | **Open.** Internal work still has to be built. D3 is 3 days away. |
| §3.1 Real quotes in Git | Closed if open data is confirmed. |
| §3.2 Test set used to choose candidates | Closed by the split below. |
| §3.3 PPG review hours | **Open.** The reviewed architecture keeps 60 rows a week. |
| §3.4 `no_charge_stated` and coverage | Fixable in the spec. `docs/01` already says Verified includes these rows. |
| §3.5 Client review of all 50 notes | Fixable in the spec, unless D2 is already finished. |
| §3.6 External AI rules | Closed if open data is confirmed. |
| §4 Meaning of "meets Level N" | **Open.** `docs/04` rule 4 has the same problem as the spec, so the reviewed architecture does not settle it. |
| §5 Missing tasks | Depends on D1 and D2 status, and on open data for the D5 rerun path. |
| §6 UI gaps | Handled in the HTML rewrite. |
| §7 30-minute limit | Eases if open data allows the external model route. |

### The split gap

The architecture has TEST and FRESH but no separation between training and validation. **DEV does three jobs:**

1. **Teaching:** lexicon v1 and few-shot examples come from it. Few-shot sets only have to be disjoint from TEST.
2. **Fitting:** the calibration map and Review thresholds are fitted on it.
3. **Judging:** candidates are replayed and compared on it.

A change can therefore be judged on the same notes it was built from. `add-training-calibration-pipeline/design.md` handles "overfitting DEV" by evaluating on TEST for each candidate, which is the conflict in §3.2.

**Proposed split:**

| Set | Used for | Row-level reading by the team |
|---|---|---|
| TRAIN | Lexicon, few-shot examples, prompts, rules | Yes |
| VALIDATION | Calibration, thresholds, comparing candidates, promotion gate | Aggregates only |
| TEST (D2) | Level gates at D3 and D4 only; never used to choose between candidates | Aggregates only until the final freeze |
| FRESH | Final out-of-sample result | Aggregates only until the final freeze |

**Rules:**

* Split by distinct note fingerprint, not by row, so a repeated note cannot land in two sets.
* Stratify with the same strata as TEST and record the seed.
* Check that all four sets are disjoint whenever any set or few-shot version is published.
* Draw few-shot examples and lexicon sources from TRAIN only.
* Keep SYNTH and ADV outside the split.

**Starting size:** 60% TRAIN and 40% VALIDATION of the non-TEST notes. Revisit this once the distinct note count is known. Validation needs enough wrong answers to calibrate on, and every note in both sets needs a label. No task covers that labelling yet.

### HTML: what the choice means

"Easier to deploy" holds only if the pages are static. Static pages cannot accept an upload, start a run or save a decision on their own. Keeping those actions in the browser needs a server, and then deployment is no simpler than Streamlit, with login and table editing still to build. ADR 0007 rejected FastAPI + React as about twice the code.

**Recommended: `itemizer run` generates static HTML pages.**

* **Reading:** results with highlighted evidence, Agent Trace Viewer, error review and KPIs. This reuses the Jinja2 and inline Vega-Lite approach already in `add-kpi-dashboard`, so the KPI View and the static dashboard become one thing.
* **Review and labelling:** the page downloads a decisions file with its timestamps, and `itemizer review import` loads it through the existing Review Decision Intake. The single intake path stays.
* **Removed:** about 8 of the 26 UI tasks (login, permission checks, upload, pre-check, job launcher, run monitor, proxy, permission tests).

**What this gives up:**

* Uploading from the browser, which was the first reason ADR 0007 gave for having a UI.
* The start of the `docs/10` website demo (upload, then watch the run). The demo would start from the CLI instead.
* Server-side role checks. Anything in a page can be read, so blind labelling and TEST pages must be generated without predictions or row data in the file.
* Logging of who viewed what.

### Open data: what to confirm

Sending notes to an external model and publishing them in a public repo or on a poster are separate permissions. The scope says data "is not published" and that changes are agreed in writing, and `docs/08` §8.4 expects notes to contain driver names and phone numbers.

If open data is confirmed:

* The external model route becomes available, which eases the 30-minute risk.
* Up to 11 tasks could go: masking (3), Privacy Guard, confidentiality gate, synthetic privacy check, real-data repo guard, encrypted volume, tombstones, OIDC and proxy.
* Check before cutting any of them. Course requirement 6 still asks for client data protection or simulated data, and the guardrail comparison measures PII egress.

## 1. The UI is not the only addition

Every open task, grouped by what justifies it:

| What justifies the work | Changes | Tasks | Share |
|---|---|---:|---:|
| The scope itself | data-transformation-check, itemization-classifier, output-formatter, run-console, kpi-calculator, ground-truth-store, model-router, common-core-contracts | 98 | 43% |
| The UI change | web-ui, human-review-system | 36 | 16% |
| Course requirements (`docs/10`) | agent-tools, guardrails, synthetic-data-generator, guardrail-evaluation, skill-folder | 48 | 21% |
| Strategy atlas, not asked for by the scope or the UI | configuration-registry, version-artifact-registry, telemetry-episode-store, training-calibration-pipeline, kpi-dashboard | 46 | 20% |
| **Total** | 20 changes | **228** | |

Grouping is by each change's main purpose. Some changes span two groups: run manifests and versioning support D5, and the run monitor reads telemetry.

**94 of 228 tasks (41%) trace to neither the scope nor the UI.** `docs/01-overview.md` flags only the UI as a scope change. Two additions matter most:

* **New items handed to PPG.** `docs/08` §8.6 gives PPG a skill folder and MCP analyst tools. Neither is in D1-D5, so the approval rule ("changes after approval are agreed in writing") may apply to them as well.
* **Course work the client has not seen.** The course requirements may be legitimate, but they are absent from the document Jake is asked to sign. The team and Jake could be working from different ideas of the project.

## 2. Size and schedule

| Check | Scope + UI | Current plan |
|---|---|---|
| Python size | About 2,000 lines (D4) + 800-1,200 (ADR 0007) = at most 3,200 | 228 tasks, 167 requirements, 181 scenarios, 18 containers, 86 components, about 85 parameters |
| Implied size per unit | | About 14 lines per task, about 19 per requirement |
| Work before D3 (5 Nov, 3 days away) | Runs end to end on the sample export and meets Level 1 | `docs/07` build order puts about 181 of 228 tasks before D3 |
| Tasks done | | 0 of 228. This folder has no `src/`, `taxonomy/`, `metrics/` or `config/` |

Tasks such as "OIDC login, domain allowlist, role map and session timeout" or "Hungarian item matcher" will not fit in 14 lines. Either the size estimate or the task list is wrong.

## 3. Direct conflicts with the scope

| # | Scope says | Plan says | Why it matters |
|---|---|---|---|
| 1 | PPG data "is not published" | Taxonomy YAML in Git stores `examples (fingerprint + quote)` from real notes (`add-ground-truth-store/design.md`). `docs/05` §5.5 says Git holds no note text, and `docs/09` says the public repo is synthetic only. | Real note text reaches a public repo, or the CI guard blocks the D1 file. |
| 2 | Test set "is never used to tune the tool" | The promotion gate rejects candidates on TEST results, returning point estimates per metric and stratum, up to 5 evaluations per milestone (`level-gates`, `promotion-gate`). | Choosing between candidates using TEST results is tuning, even with aggregates only. |
| 3 | About 3 hours of PPG time in total | `review.weekly_capacity_rows` = 60. At the spec's own 90 seconds per row that is 1.5 hours per week, or about 6 hours by 3 Dec. | Approval rate, audit disagreement and minutes per dispute all depend on time nobody has budgeted. |
| 4 | Three outcomes; "no charge stated" counts as Verified | The contract has a fourth value, `no_charge_stated`, while the coverage formula counts only Verified + Discrepancy (`docs/04` §4.5). | Coverage can come out too low, depending on how the code reads this. |
| 5 | Jake or a PPG accountant reviews the 50 double-labelled notes | The spec sends only disagreements to the client owner. | D2's done-when condition is not met as specified. |
| 6 | Without Jake's approval: local model or mask names | External use needs approval **and** masking. | Stricter than the scope and safe, but it removes an option the scope allows. |

## 4. "Meets Level 1 / Level 2" is not defined the same way

The scope sets accuracy at 95% or higher and accepts about ±3 points of precision. `level-gates` reports **inconclusive** whenever the interval contains the target, and its own example gives 0.96 (interval 0.93-0.98) as inconclusive for accuracy.

With a Wilson interval, a clean pass needs **197 of 200 (98.5%)**. At 100 covered notes it needs 100 of 100. Accuracy is measured on covered rows only, and weighting widens the interval further, so the real requirement is stricter than these figures.

The plan does not say whether "inconclusive" counts as meeting the level. As written, D3 and D4 may have no reachable pass on accuracy. Agree the rule with Jake before results exist.

## 5. Scope items with no task

| Scope item | Finding |
|---|---|
| D5 report (8-12 pages) | No task or change writes it. |
| D5 "reader outside the team can rerun the tool" | The rerun restores artifacts from an encrypted volume an outsider cannot reach. `docs/10` plans a README quickstart on synthetic data, but nothing ties it to D5 or says what an outside reader can reproduce. |
| D1 content and Jake's sign-off | Tasks build the schema and validator only. Nothing writes the categories or obtains approval. |
| D2 labelling (200 notes) | Tasks build the tooling only. Nothing covers the labelling itself. |
| D3 "Jake has seen it" | No task. |
| Requests to PPG: current minutes per dispute, monthly volume, a fresh month | Listed as open questions only, with no task or owner. |
| Level 3 cost-driver summary by carrier and category | Not found in any doc or spec. It is a stretch goal, but the omission is silent. |
| Per-carrier coverage and accuracy (claimed in `docs/08` §8.4) | No KPI or dashboard spec or task mentions carriers. |

## 6. Gaps inside the UI plan

| Gap | Evidence |
|---|---|
| **Agent Trace Viewer has no spec or task** | `docs/10` calls it "the creative centrepiece" of the website demo, and the DSL has it as a Web UI component. `add-web-ui` lists 10 components, leaves it out, and has no task for it. |
| KPI View has a task but no requirement | Task 4.4 exists; none of the 5 UI specs mention it. |
| Demo mode has no task | `add-synthetic-data-generator` lists "add-web-ui demo mode" as a consumer, and the website demo uploads a synthetic export, but `add-web-ui` never mentions synthetic data or a demo. No spec says how demo data is kept apart from PPG data on the server. |
| Three blockers are still open | Jake's written agreement, PPG sign-in (OIDC or guest accounts), and CMU VM availability and data rules (`add-web-ui/design.md`). All three depend on people outside the team. |
| Review pages depend on reviewers who may not exist | See conflict 3. If PPG cannot reach the server, the UI measures nothing from accountants. |
| Fallback work is duplicated | Excel review, adjudication and labelling workbooks sit alongside the UI pages, and the static dashboard alongside the KPI View. Both are specified in full. |
| "Approve" wording | The review button and "approval rate" sit close to the payment decision the scope excludes. The Action Guard blocks the same language from the agent. Consider "accept". |

## 7. Risks that are not yet conflicts

**The 30-minute limit has not been tested against the agent design.** ADR 0008 adds several model calls per note and only says latency will be measured.

* With 4 parallel slots, 30 minutes gives 7,200 model-seconds.
* At an assumed 1,000 distinct notes and 4 turns per note, that leaves **1.8 seconds per turn**. At 600 notes it leaves 3 seconds.
* Those note and turn counts are illustrative. Neither they nor the latency have been measured, and the deployment view names no GPU.
* The planned fallback (`add-run-console/design.md`) sends the remaining rows to Review, so a slow model lowers coverage directly.

**The closed loop has no weekly data to run on.** The scope asks PPG for one fresh month, not weekly exports. Without weekly data, PROD metrics, adjudication and recertification have little or nothing to run on before 3 Dec. Thresholds also carry a 30-day expiry in a project with about 31 days left.

**The baseline may not be approved.** The PDF is marked "for client approval" and its signature lines are blank.

## 8. What does match

| Scope item | Where it is covered |
|---|---|
| Level 1/2/3 targets (80/25/95, 90/85/95, 95/95/95) | `gates.level1-3` |
| Three invariants: exact words, no invented or edited amounts, flag rows that do not add up | ADR 0006, contract validators, Output Guard |
| One command, under 30 minutes for 1,500 rows | `itemizer run`, timing benchmark task. The CLI stays alongside the UI. |
| Excel with items and row summary sheets | `itemized-output` (adds Run Info and Categories) |
| Coverage and accuracy definitions, weighting to the real mix | `docs/04`, `kpi-metrics` |
| 200 notes, half and half, 50 labelled blind by two people, sealed | `evaluation-sets`, `review-workflow` |
| In-sample label when no fresh data arrives | `evaluation-sets` |
| Local model by default, external gated | ADR 0003, `model-routing` |
| X12 with XPO fallback for Level 3 | `charge-taxonomy` |
| Payment decision excluded; no TMS or accounting connection | ADR 0007, `docs/02` authority ladder |
| Slide 2 blocks all map to containers | `docs/01` mapping table |

## 9. Fix plan

The fix pass below is done; the changes are uncommitted. A Goldfish review of the result comes next if the team wants it.

**Fix pass (done):**

1. **UI:** add ADR 0011 superseding ADR 0007. Update the Web UI container in `workspace.dsl`, `docs/01`, the `ui.*` parameters and `openspec/config.yaml`. Rewrite `add-web-ui` for the chosen form, including the Agent Trace Viewer, KPI View and demo data handling.
2. **Split:** add ADR 0012. Update the populations in `docs/04`, the artifacts in `docs/05`, the closed loop in `docs/06`, the affected parameters in `docs/03`, and the changes that read DEV. Add a task for labelling TRAIN and VALIDATION.
3. **Open data:** record the permission and where it is written. Update the affected ADRs and docs. Cut only what course requirement 6 does not need.
4. **Spec fixes:** count `no_charge_stated` as Verified in the coverage requirement. Have the client review all 50 notes if D2 is still open.
5. **Missing work:** add a change covering the D5 report and the outside-reader rerun, plus D1, D2, D3 and PPG data requests as far as they are still open. Add per-carrier metrics and the Level 3 cost-driver summary. Update the change count and traceability in `docs/07`, `docs/10` and `architecture/README.md`.
6. **Regenerate** `architecture/export/` from the DSL and run `openspec validate --all --strict`.

**Not fixable by editing documents; the team and client must decide:**

1. Which tasks are cut, reduced or moved after 3 Dec, given that D3 is 3 days away.
2. What "meets Level N" means when the interval contains 95%.
3. Where the PPG reviewer hours come from, or how far the review queue shrinks.
4. Whether the skill folder and MCP tools are really handed to PPG.
5. Which output table to use, and whether Level dollars keep counting repeated-invoice rows.
