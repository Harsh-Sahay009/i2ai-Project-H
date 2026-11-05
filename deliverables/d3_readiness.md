# D3 readiness — 4 November 2026

> **5 November update:** this document preserves the November 4 checkpoint below. Latest `main` (`5720718`) now includes the local upload UI, Kimi comparison, and updated KPI reporting. It has been integrated with the local readiness fixes on `codex/integrate-latest`. Alejandro also supplied `test_provisional.json` with 200 model-drafted labels and 279 items. Only 77 notes overlap the reconstructed TEST set, so the file is preserved separately under ignored `data/incoming/alejandro/`. A portable workbook supports review of those original labels without fabricating freeze records or changing the local reconstruction. Original split/freeze/run artifacts are still missing; human review remains pending. See `deliverables/integration_2026-11-05.md` for current verification.

The team selected prototype and D3 readiness first. This record accompanies the local `codex/d3-readiness` branch, based on implementation commit `63f440d`. It does not record a client approval or declare D3 complete.

## What is locally verified

- The supplied workbook loads: 1,347 rows, 729 distinct notes, 18 carriers, $186,345.02 disputed. Its SHA-256 is `e08da6c7fd6e03036d537a13ed0a52748ef81fc5cedea0df7f3ec037bc43c0e5`.
- The existing taxonomy passes validation: 19 categories plus `other_unmapped`.
- A fresh split previously omitted prompt examples from the notes pinned to TRAIN. It placed two examples in TEST and one in VALIDATION, and prompt loading correctly refused the result. The correction pins every referenced prompt example before partitioning; locked splits remain locked.
- All 12 prompt examples validate against the corrected local split.
- The corrected reconstruction has TRAIN 305, VALIDATION 204, TEST 200 and RESERVE 20 notes. It is **not** the November 3 frozen experiment. No historical accuracy transfers to it.
- The original 867-test suite passes. After the corrections, the full suite passes **884 tests in 226.33 seconds**, including seven new split regressions and ten new readiness tests. `git diff --check` passes; independent code review found no remaining actionable issues.
- No model calls have been made in this readiness work. The configured Anthropic key is absent in this local environment. Provider access and current prices have not been validated.

The reconstructed split before the correction is retained locally at `data/bootstrap/split_manifest.before-readiness-fix.json`. Generated D1, labeling and status materials are private local artifacts under ignored `data/`.

## Work order and completion conditions

| Priority | Work | Completion evidence |
|---|---|---|
| 1 | Recover the original experiment if available | Original bootstrap split, packs, labels, runs, KPI ledger and reports, with matching dataset and code identity |
| 2 | Agree labeling rules, especially balance due | Written interpretation from Jake; matching instructions and prompt for the selected experiment |
| 3 | Independent labeling | Two real readers label the same 50 TEST notes without seeing each other's answers or tool results; other TEST labels and disagreements completed |
| 4 | Client category and label review | Actual category approval and review of 50 double-labeled notes; written evidence saved privately |
| 5 | Run and score | Actual full-data output, manifest, zero invariant violations, frozen/sealed TEST evaluation and explicit provisional/final status |
| 6 | D3 review with Jake | Prototype demonstrated; review evidence belongs to that run; acceptance status reflects all remaining conditions |
| 7 | D4/D5 preparation | New-export check, independently verified Level 2 results, reproducible methodology report by December 3 |

The November 5 prototype milestone is next. Additional UI and agent features should follow a credible D3 evaluation rather than delay it.

## Human labeling options

The user currently has only the source workbook. **Preferred:** recover Alejandro's original artifacts to review his existing 200 model drafts and preserve the experiment. The original run report says the drafts had not been human checked as of November 3; later private progress may exist.

**Prepared fallback:** new blind packs from the corrected reconstruction. Use these only if the team chooses a new experiment instead of recovering the original. They contain no tool predictions or suggested labels. Do not mix their labels or split with Alejandro's original run. Do not regenerate these packs once reviewers start.

Suggested allocation, for the team to agree (no assignments have been made):

- Two independent readers take `label_A.xlsx` and `label_B.xlsx` (50 common notes).
- Divide the remaining 150 notes in `label_single.xlsx` by disjoint note IDs; reconcile into one workbook before import. Another reader uses the spot-check pack.
- A separate development task labels at least 100 notes in `validation.xlsx`. None of its labels become TEST labels.
- Jake or a PPG accountant reviews the required 50; the team resolves disagreements and records actual evidence.

Blank packs are not completed ground truth. Existing model-draft review follows `deliverables/reviewing_test_labels.md` after the original artifacts are recovered.

## Original-artifact handoff checklist

Ask Alejandro for these privately through the team's normal channel; this document does not send a message:

1. `data/bootstrap/` including split, packs, label JSON files, provisional/sealed records, scan decision and command log.
2. `data/runs/` including manifests, note/row results, itemized workbooks and telemetry.
3. `data/kpi/` including snapshots and TEST-budget ledger, plus `data/reports/`.
4. The exact code commit/dirty state behind the reported full-data run and the dataset hash.
5. Existing real approval evidence and `taxonomy/approval.yaml`, if any. API keys are not part of the handoff.

Back up the local reconstruction before restoring anything. Compare hashes and label provenance; do not merge files from different splits. `doctor` checks local setup, not original-run identity or approval authenticity.

## Questions for Jake / team decisions

- Does a balance due beside listed charges represent a total or an additional charge? Current code treats it as a total; the historical report identifies conflicting examples. Do not change labels simply to match tool output.
- Is this specific dataset authorized for an external AI service? The source URL/client confirmation remains unresolved, and the local scan flags 44 notes with possible personal information. No acceptance decision has been recorded here.
- Should coverage count repeated invoice rows? They account for about 48% of disputed dollars in this export.
- How should negative dispute amounts be represented in dollar coverage? The historical net-sum metric excluding repeats exceeds 100%; do not silently cap it or alter the acceptance formula.
- What currency applies to Canadian-tax notes?
- Are the combined D1/D2/D3 presentation and UI/output scope changes agreed in writing? The supplied scope excludes a UI.
- What are current minutes per dispute and monthly dispute volume? These are needed to quantify time savings.

## Five-minute D3 walkthrough

1. State the task: itemize dispute-note charges with evidence; accountants decide payment.
2. Show `itemizer doctor` and explain that setup readiness differs from completed validation.
3. Show the D1 category draft privately and identify the approval still needed.
4. Explain the labeling workflow and independence of the two readers; do not show private notes in a public presentation.
5. If the original full-run workbook is recovered, demonstrate its Items and RowSummary sheets in an authorized private meeting and identify its run ID. Otherwise state that local run outputs are missing; do not substitute fabricated predictions.
6. Attribute historical numbers to `openspec/changes/add-d3-thin-path/live-check.md`: 99.3% agreement with unreviewed Opus-drafted labels, 99.0% row coverage and 99.1% dollar coverage. These were not independently reproduced here. Clear discrepancies count as coverage.
7. Show the actual local acceptance page. D3 remains open until the selected experiment has valid evidence, human/client review and the required result.

## Final-delivery work after D3

Prioritize reviewed-label error analysis (especially large disputes), a settled balance-due policy, safe data handling, VALIDATION-based model selection, a genuinely new export or clearly labeled synthetic compatibility test, and an outside-reader rerun guide. Full UI, agent and dashboard work needs a separate prioritized plan and scope confirmation. Preserve TEST for milestone evaluation; do not tune against repeated TEST scores.
