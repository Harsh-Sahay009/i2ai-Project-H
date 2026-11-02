# Scope alignment check: architecture and OpenSpec vs. the scope statement

* **Date:** 2026-11-02
* **Baseline:** `Freight_Analytics_Scope_Statement 2.pdf` (v1.0, 1 Oct 2026), plus one stated change: the Web UI is now in scope.
* **Compared against:** `architecture/` (C4 model, docs 01-10, ADRs 0001-0010), `Architecture Diagram - i2ai project.pptx`, and all 20 changes in `openspec/changes/`.
* **Status:** first pass by one reviewer. No Goldfish review has run yet.

## Verdict

**They do not match, and the UI is not the only difference.** The product rules line up with the scope. The amount of work, the schedule, the use of PPG time and some of the deliverables do not.

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

## 9. Fix now vs. decide

**Fixes that need no decision from anyone:**

1. Remove real quotes from taxonomy files in Git; keep fingerprints and load the text from the encrypted store.
2. Make `no_charge_stated` a reason on a Verified row, not a fourth outcome.
3. Add the missing Agent Trace Viewer, KPI View and D5 report work to OpenSpec.
4. Have the client review all 50 double-labelled notes.

**Decisions the team and client need to make:**

1. Which of the 94 tasks are cut, reduced or moved after 3 Dec.
2. Whether Jake is told about the course-driven additions, and which of them count as scope changes.
3. What "meets Level N" means when the interval contains 95%.
4. Whether TEST may ever be used to choose between candidates.
5. Whether UI work starts before or after D3.
